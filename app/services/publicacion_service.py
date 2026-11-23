"""Reglas de negocio de publicaciones (convocatorias)."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.fundacion import Fundacion
from app.models.gamificacion import PublicacionImagen
from app.models.habilidades import MAX_HABILIDADES, MIN_HABILIDADES
from app.models.organizacion import VD_VERIFICADA
from app.models.postulacion import ESTADO_EN_REVISION as ESTADO_POST_EN_REVISION
from app.models.postulacion import ESTADO_PENDIENTE as ESTADO_POST_PENDIENTE
from app.models.postulacion import Postulacion
from app.models.publicacion import (
    ESTADO_BORRADOR,
    ESTADO_CANCELADA,
    ESTADO_PENDIENTE_APROBACION,
    ESTADO_PUBLICADA,
    Publicacion,
)
from app.repositories.publicacion_repo import PublicacionRepository
from app.schemas.publicacion import (
    FundacionResumen,
    PaginatedResponse,
    PublicacionCreate,
    PublicacionImagenOut,
    PublicacionOut,
    PublicacionUpdate,
)
from app.services.coincidencia import calcular_coincidencia
from app.services.habilidad_service import HabilidadService
from app.services.storage_service import StorageService

MAX_IMAGENES = 8


def _now() -> datetime:
    return datetime.now(UTC)


def _to_out(pub: Publicacion) -> PublicacionOut:
    """Serializa dentro del contexto async (habilidades ya cargadas)."""
    return PublicacionOut.model_validate(pub)


class PublicacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PublicacionRepository(db)

    async def _enriquecer(
        self, pubs: list[Publicacion], voluntario_id: uuid.UUID | None
    ) -> list[PublicacionOut]:
        """Añade la organización y, si hay voluntario, la coincidencia de habilidades."""
        vol_hab: set[int] | None = None
        if voluntario_id is not None:
            vol_hab = set(await HabilidadService(self.db).ids_de_voluntario(voluntario_id))

        galerias: dict[uuid.UUID, list[PublicacionImagen]] = {}
        if pubs:
            for img in (
                await self.db.execute(
                    select(PublicacionImagen)
                    .where(PublicacionImagen.publicacion_id.in_([p.id for p in pubs]))
                    .order_by(PublicacionImagen.orden, PublicacionImagen.fecha_creacion)
                )
            ).scalars().all():
                galerias.setdefault(img.publicacion_id, []).append(img)

        ids = {p.fundacion_id for p in pubs}
        fundaciones: dict[uuid.UUID, Fundacion] = {}
        if ids:
            filas = (
                await self.db.execute(select(Fundacion).where(Fundacion.id.in_(ids)))
            ).scalars().all()
            fundaciones = {f.id: f for f in filas}

        salida: list[PublicacionOut] = []
        for pub in pubs:
            out = _to_out(pub)
            out.imagenes = [
                PublicacionImagenOut.model_validate(i) for i in galerias.get(pub.id, [])
            ]
            requeridas = [h.id for h in pub.habilidades]
            if vol_hab is not None:
                out.coincidencia = calcular_coincidencia(requeridas, vol_hab)
                out.habilidades_coinciden = [i for i in requeridas if i in vol_hab]
            f = fundaciones.get(pub.fundacion_id)
            if f is not None:
                out.fundacion = FundacionResumen(
                    id=f.id,
                    nombre=f.nombre,
                    logo=f.logo,
                    verificada=f.verificacion_documental == VD_VERIFICADA,
                    tipo_organizacion=f.tipo_organizacion,
                )
            salida.append(out)
        return salida

    async def listar_publicas(
        self,
        *,
        categoria_id: int | None,
        modalidad: str | None,
        municipio_id: int | None,
        buscar: str | None,
        page: int,
        per_page: int,
        voluntario_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[PublicacionOut]:
        filas, total = await self.repo.listar_publicas(
            categoria_id=categoria_id,
            modalidad=modalidad,
            municipio_id=municipio_id,
            buscar=buscar,
            voluntario_id=voluntario_id,
            page=page,
            per_page=per_page,
        )
        return PaginatedResponse(
            data=await self._enriquecer(filas, voluntario_id),
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    async def obtener_publica(
        self, publicacion_id: uuid.UUID, voluntario_id: uuid.UUID | None = None
    ) -> PublicacionOut:
        pub = await self.repo.por_id_con_habilidades(publicacion_id)
        if pub is None or pub.estado != ESTADO_PUBLICADA or pub.oculta_por_admin:
            raise NotFoundError("Convocatoria no encontrada.")
        return (await self._enriquecer([pub], voluntario_id))[0]

    async def crear(self, fundacion_id: uuid.UUID, data: PublicacionCreate) -> PublicacionOut:
        payload = data.model_dump(exclude={"habilidades"})
        payload["fundacion_id"] = fundacion_id
        payload["estado"] = ESTADO_BORRADOR
        if data.habilidades:
            await HabilidadService(self.db).validar_ids(
                data.habilidades, minimo=1, maximo=MAX_HABILIDADES, sujeto="La actividad"
            )
        pub = await self.repo.crear(payload, data.habilidades)
        salida = _to_out(pub)
        await self.db.commit()
        return salida

    async def _pub_de_fundacion(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> Publicacion:
        pub = await self.repo.por_id_y_fundacion(publicacion_id, fundacion_id)
        if pub is None:
            # No revela si existe pero es de otra fundación.
            raise NotFoundError("Convocatoria no encontrada.")
        return pub

    async def actualizar(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID, data: PublicacionUpdate
    ) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        if pub.estado in (ESTADO_CANCELADA,):
            raise ConflictError("No se puede editar una convocatoria cancelada.")
        campos = data.model_dump(exclude_unset=True, exclude={"habilidades"})
        if data.habilidades is not None:
            minimo = MIN_HABILIDADES if pub.estado == ESTADO_PUBLICADA else 0
            if data.habilidades or minimo:
                await HabilidadService(self.db).validar_ids(
                    data.habilidades,
                    minimo=minimo or 1,
                    maximo=MAX_HABILIDADES,
                    sujeto="La actividad",
                )
        pub = await self.repo.actualizar(pub, campos, data.habilidades)
        salida = (await self._enriquecer([pub], None))[0]
        await self.db.commit()
        return salida

    async def obtener_propia(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> PublicacionOut:
        """Detalle para la organización dueña, en cualquier estado (para editar)."""
        pub = await self.repo.por_id_con_habilidades(publicacion_id)
        if pub is None or pub.fundacion_id != fundacion_id:
            raise NotFoundError("Convocatoria no encontrada.")
        return (await self._con_conteos(await self._enriquecer([pub], None)))[0]

    async def _con_conteos(self, salida: list[PublicacionOut]) -> list[PublicacionOut]:
        """Agrega el total de postulaciones y las pendientes de revisar."""
        if not salida:
            return salida
        filas = (
            await self.db.execute(
                select(Postulacion.publicacion_id, Postulacion.estado, func.count())
                .where(Postulacion.publicacion_id.in_([s.id for s in salida]))
                .group_by(Postulacion.publicacion_id, Postulacion.estado)
            )
        ).all()
        totales: dict[uuid.UUID, int] = {}
        pendientes: dict[uuid.UUID, int] = {}
        for pid, estado, n in filas:
            totales[pid] = totales.get(pid, 0) + n
            if estado in (ESTADO_POST_PENDIENTE, ESTADO_POST_EN_REVISION):
                pendientes[pid] = pendientes.get(pid, 0) + n
        for s in salida:
            s.postulaciones_total = totales.get(s.id, 0)
            s.postulaciones_pendientes = pendientes.get(s.id, 0)
        return salida

    async def publicar(self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        if pub.estado not in (ESTADO_BORRADOR, ESTADO_PENDIENTE_APROBACION):
            raise ConflictError("Solo se puede publicar una convocatoria en borrador.")
        if not MIN_HABILIDADES <= len(pub.habilidades) <= MAX_HABILIDADES:
            raise ConflictError(
                f"Para publicar, la actividad debe exigir entre {MIN_HABILIDADES} y "
                f"{MAX_HABILIDADES} habilidades del catálogo."
            )
        pub.estado = ESTADO_PUBLICADA
        pub.fecha_publicacion = _now()
        await self.db.flush()
        await self.repo.cargar_habilidades(pub)
        salida = _to_out(pub)
        await self.db.commit()
        return salida

    async def cancelar(self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        if pub.estado in (ESTADO_CANCELADA,):
            raise ConflictError("La convocatoria ya está cancelada.")
        pub.estado = ESTADO_CANCELADA
        await self.db.flush()
        await self.repo.cargar_habilidades(pub)
        salida = _to_out(pub)
        await self.db.commit()
        return salida

    async def mis_publicaciones(
        self, fundacion_id: uuid.UUID, page: int, per_page: int
    ) -> PaginatedResponse[PublicacionOut]:
        filas, total = await self.repo.listar_de_fundacion(fundacion_id, page, per_page)
        return PaginatedResponse(
            data=await self._con_conteos(await self._enriquecer(filas, None)),
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    async def subir_imagen(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID, archivo: UploadFile
    ) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        existentes = list(
            (
                await self.db.execute(
                    select(PublicacionImagen).where(PublicacionImagen.publicacion_id == pub.id)
                )
            ).scalars().all()
        )
        if len(existentes) >= MAX_IMAGENES:
            raise ConflictError(f"Máximo {MAX_IMAGENES} fotografías por convocatoria.")
        url = await StorageService(get_settings()).guardar_imagen(archivo, "convocatorias")
        orden = max((i.orden for i in existentes), default=-1) + 1
        self.db.add(PublicacionImagen(publicacion_id=pub.id, ruta=url, orden=orden))
        if not existentes:
            pub.imagen = url  # portada para tarjetas y listados
        pub.fecha_actualizacion = _now()
        await self.db.flush()
        salida = (await self._enriquecer([pub], None))[0]
        await self.db.commit()
        return salida

    async def eliminar_imagen(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID, imagen_id: uuid.UUID
    ) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        img = await self.db.get(PublicacionImagen, imagen_id)
        if img is None or img.publicacion_id != pub.id:
            raise NotFoundError("Fotografía no encontrada.")
        await self.db.delete(img)
        await self.db.flush()
        primera = (
            await self.db.execute(
                select(PublicacionImagen.ruta)
                .where(PublicacionImagen.publicacion_id == pub.id)
                .order_by(PublicacionImagen.orden, PublicacionImagen.fecha_creacion)
                .limit(1)
            )
        ).scalar_one_or_none()
        pub.imagen = primera
        pub.fecha_actualizacion = _now()
        await self.db.flush()
        salida = (await self._enriquecer([pub], None))[0]
        await self.db.commit()
        return salida

    def _ensure_owner(self, pub: Publicacion, fundacion_id: uuid.UUID) -> None:
        if pub.fundacion_id != fundacion_id:
            raise ForbiddenError("No tienes permiso sobre esta convocatoria.")

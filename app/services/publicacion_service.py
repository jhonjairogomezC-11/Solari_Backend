"""Reglas de negocio de publicaciones (convocatorias)."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.publicacion import (
    ESTADO_BORRADOR,
    ESTADO_CANCELADA,
    ESTADO_PENDIENTE_APROBACION,
    ESTADO_PUBLICADA,
    Publicacion,
)
from app.repositories.publicacion_repo import PublicacionRepository
from app.schemas.publicacion import (
    PaginatedResponse,
    PublicacionCreate,
    PublicacionOut,
    PublicacionUpdate,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _to_out(pub: Publicacion) -> PublicacionOut:
    """Serializa dentro del contexto async (habilidades ya cargadas)."""
    return PublicacionOut.model_validate(pub)


class PublicacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PublicacionRepository(db)

    async def listar_publicas(
        self,
        *,
        categoria_id: int | None,
        modalidad: str | None,
        municipio_id: int | None,
        buscar: str | None,
        page: int,
        per_page: int,
    ) -> PaginatedResponse[PublicacionOut]:
        filas, total = await self.repo.listar_publicas(
            categoria_id=categoria_id,
            modalidad=modalidad,
            municipio_id=municipio_id,
            buscar=buscar,
            page=page,
            per_page=per_page,
        )
        return PaginatedResponse(
            data=[_to_out(f) for f in filas],
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    async def obtener_publica(self, publicacion_id: uuid.UUID) -> PublicacionOut:
        pub = await self.repo.por_id_con_habilidades(publicacion_id)
        if pub is None or pub.estado != ESTADO_PUBLICADA or pub.oculta_por_admin:
            raise NotFoundError("Convocatoria no encontrada.")
        return _to_out(pub)

    async def crear(self, fundacion_id: uuid.UUID, data: PublicacionCreate) -> PublicacionOut:
        payload = data.model_dump(exclude={"habilidades"})
        payload["fundacion_id"] = fundacion_id
        payload["estado"] = ESTADO_BORRADOR
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
        pub = await self.repo.actualizar(pub, campos, data.habilidades)
        salida = _to_out(pub)
        await self.db.commit()
        return salida

    async def publicar(self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID) -> PublicacionOut:
        pub = await self._pub_de_fundacion(publicacion_id, fundacion_id)
        if pub.estado not in (ESTADO_BORRADOR, ESTADO_PENDIENTE_APROBACION):
            raise ConflictError("Solo se puede publicar una convocatoria en borrador.")
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
            data=[_to_out(f) for f in filas],
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    def _ensure_owner(self, pub: Publicacion, fundacion_id: uuid.UUID) -> None:
        if pub.fundacion_id != fundacion_id:
            raise ForbiddenError("No tienes permiso sobre esta convocatoria.")

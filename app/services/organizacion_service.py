"""Perfil público de la organización, verificación documental y reseñas."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models.catalogo import AreaImpacto, Municipio
from app.models.favorito import TIPO_FUNDACION, VoluntarioFavorito
from app.models.fundacion import Fundacion
from app.models.notificacion import (
    TIPO_NUEVA_RESENA,
    TIPO_RESENA_RESPONDIDA,
    TIPO_VERIFICACION_ACTUALIZADA,
)
from app.models.organizacion import (
    RESENA_OCULTA,
    RESENA_PENDIENTE,
    RESENA_VISIBLE,
    TIPOS_DOCUMENTO_VERIF,
    VD_EN_REVISION,
    VD_INFO_REQUERIDA,
    VD_NO_SOLICITADA,
    VD_RECHAZADA,
    VD_REVOCADA,
    VD_VERIFICADA,
    FundacionDocumento,
    FundacionGaleria,
    ResenaOrganizacion,
    fundacion_areas,
)
from app.models.postulacion import ESTADO_ASISTIO, Postulacion
from app.models.publicacion import ESTADO_CANCELADA, ESTADO_BORRADOR, Publicacion
from app.models.usuario import ESTADO_ACTIVO, Usuario
from app.models.voluntario import Voluntario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.catalogo import AreaImpactoOut
from app.schemas.organizacion import (
    AVISO_VERIFICACION,
    ContactoPublico,
    DocumentoVerifOut,
    EstadisticasOrganizacion,
    GaleriaItem,
    OrganizacionPublicaOut,
    PerfilPublicoUpdate,
    ResenaCreate,
    ResenaOut,
    ResenasPage,
    ResumenResenas,
    VerificacionEstadoOut,
    VerificacionPublica,
)
from app.services.coincidencia import contiene_datos_personales, contiene_lenguaje_ofensivo
from app.services.notificacion_service import NotificacionService
from app.services.ofrecimiento_service import primer_nombre
from app.services.storage_service import StorageService

MAX_GALERIA = 12


def _now() -> datetime:
    return datetime.now(UTC)


def motivo_moderacion(texto: str) -> str | None:
    """Devuelve el motivo si el texto debe revisarse antes de publicarse."""
    if contiene_datos_personales(texto):
        return "Contiene datos personales (correo, teléfono o enlace)."
    if contiene_lenguaje_ofensivo(texto):
        return "Contiene lenguaje ofensivo."
    return None


class OrganizacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notif = NotificacionService(db)
        self.storage = StorageService(get_settings())

    # ─────────────── Estadísticas reales (R11) ───────────────

    async def estadisticas(self, fundacion: Fundacion) -> EstadisticasOrganizacion:
        fid = fundacion.id

        async def contar(*condiciones) -> int:
            return (
                await self.db.execute(
                    select(func.count()).select_from(Publicacion).where(
                        Publicacion.fundacion_id == fid, *condiciones
                    )
                )
            ).scalar_one()

        async def realizadas(recurrente: bool) -> int:
            filtro = (
                Publicacion.programacion_id.is_not(None)
                if recurrente
                else Publicacion.programacion_id.is_(None)
            )
            return (
                await self.db.execute(
                    select(func.count(func.distinct(Publicacion.id)))
                    .select_from(Publicacion)
                    .join(Postulacion, Postulacion.publicacion_id == Publicacion.id)
                    .where(
                        Publicacion.fundacion_id == fid,
                        Postulacion.estado == ESTADO_ASISTIO,
                        filtro,
                    )
                )
            ).scalar_one()

        participantes, confirmadas = (
            await self.db.execute(
                select(
                    func.count(func.distinct(Postulacion.voluntario_id)),
                    func.count(Postulacion.id),
                )
                .select_from(Postulacion)
                .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
                .where(Publicacion.fundacion_id == fid, Postulacion.estado == ESTADO_ASISTIO)
            )
        ).one()
        fecha = fundacion.fecha_creacion
        antig = (datetime.now(fecha.tzinfo) - fecha).days if fecha else 0
        return EstadisticasOrganizacion(
            antiguedad_dias=max(antig, 0),
            convocatorias_creadas=await contar(Publicacion.estado != ESTADO_BORRADOR),
            individuales_realizadas=await realizadas(False),
            individuales_canceladas=await contar(
                Publicacion.estado == ESTADO_CANCELADA, Publicacion.programacion_id.is_(None)
            ),
            recurrentes_realizadas=await realizadas(True),
            recurrentes_canceladas=await contar(
                Publicacion.estado == ESTADO_CANCELADA, Publicacion.programacion_id.is_not(None)
            ),
            voluntarios_participantes=participantes,
            participaciones_confirmadas=confirmadas,
        )

    # ─────────────── Perfil público ───────────────

    async def _resumen_resenas(self, fundacion_id: uuid.UUID) -> ResumenResenas:
        promedio, total = (
            await self.db.execute(
                select(func.avg(ResenaOrganizacion.calificacion), func.count()).where(
                    ResenaOrganizacion.fundacion_id == fundacion_id,
                    ResenaOrganizacion.estado == RESENA_VISIBLE,
                )
            )
        ).one()
        return ResumenResenas(
            promedio=round(float(promedio), 2) if promedio is not None else None, total=total
        )

    async def _resena_a_out(self, r: ResenaOrganizacion) -> ResenaOut:
        vol = await self.db.get(Voluntario, r.voluntario_id)
        usuario = await self.db.get(Usuario, vol.usuario_id) if vol else None
        return ResenaOut(
            id=r.id,
            voluntario_nombre=primer_nombre(usuario.nombre) if usuario else "Voluntario",
            calificacion=r.calificacion,
            comentario=r.comentario,
            respuesta=r.respuesta,
            fecha_respuesta=r.fecha_respuesta,
            fecha_creacion=r.fecha_creacion,
            estado=r.estado,
        )

    async def perfil_publico(
        self, fundacion_id: uuid.UUID, usuario: Usuario | None
    ) -> OrganizacionPublicaOut:
        f = await self.db.get(Fundacion, fundacion_id)
        if f is None:
            raise NotFoundError("Organización no encontrada.")
        dueno = await self.db.get(Usuario, f.usuario_id)
        es_mia = usuario is not None and usuario.id == f.usuario_id
        if not es_mia and (
            dueno is None
            or dueno.estado != ESTADO_ACTIVO
            or f.estado_verificacion in ("RECHAZADA", "SUSPENDIDA")
        ):
            raise NotFoundError("Organización no encontrada.")

        municipio = (
            await self.db.execute(select(Municipio.nombre).where(Municipio.id == f.municipio_id))
        ).scalar_one_or_none()
        areas = (
            await self.db.execute(
                select(AreaImpacto)
                .join(fundacion_areas, fundacion_areas.c.area_id == AreaImpacto.id)
                .where(fundacion_areas.c.fundacion_id == f.id)
                .order_by(AreaImpacto.nombre)
            )
        ).scalars().all()
        galeria = (
            await self.db.execute(
                select(FundacionGaleria)
                .where(FundacionGaleria.fundacion_id == f.id)
                .order_by(FundacionGaleria.orden, FundacionGaleria.fecha_creacion)
            )
        ).scalars().all()

        es_favorita = puede_resenar = False
        mi_resena = None
        if usuario is not None and usuario.rol == "VOLUNTARIO":
            vol = await UsuarioRepository(self.db).voluntario_por_usuario(usuario.id)
            if vol is not None:
                es_favorita = (
                    await self.db.execute(
                        select(VoluntarioFavorito.id).where(
                            VoluntarioFavorito.voluntario_id == vol.id,
                            VoluntarioFavorito.tipo == TIPO_FUNDACION,
                            VoluntarioFavorito.fundacion_id == f.id,
                        )
                    )
                ).first() is not None
                existente = (
                    await self.db.execute(
                        select(ResenaOrganizacion).where(
                            ResenaOrganizacion.fundacion_id == f.id,
                            ResenaOrganizacion.voluntario_id == vol.id,
                        )
                    )
                ).scalar_one_or_none()
                if existente:
                    mi_resena = await self._resena_a_out(existente)
                else:
                    puede_resenar = await self._participo(vol.id, f.id)

        return OrganizacionPublicaOut(
            id=f.id,
            nombre=f.nombre,
            tipo_organizacion=f.tipo_organizacion,
            constituida_legalmente=f.constituida_legalmente,
            logo=f.logo,
            descripcion=f.descripcion,
            historia=f.historia,
            mision=f.mision,
            municipio=municipio,
            areas=[AreaImpactoOut.model_validate(a) for a in areas],
            contacto=ContactoPublico(
                telefono=f.telefono if f.mostrar_telefono else None,
                correo=f.correo_institucional if f.mostrar_correo else None,
                direccion=f.direccion if f.mostrar_direccion else None,
                pagina_web=f.pagina_web,
            ),
            galeria=[GaleriaItem.model_validate(g) for g in galeria],
            estadisticas=await self.estadisticas(f),
            verificacion=VerificacionPublica(
                verificada=f.verificacion_documental == VD_VERIFICADA,
                fecha=f.verificacion_documental_fecha
                if f.verificacion_documental == VD_VERIFICADA
                else None,
            ),
            resenas=await self._resumen_resenas(f.id),
            es_mia=es_mia,
            es_favorita=es_favorita,
            puede_resenar=puede_resenar,
            mi_resena=mi_resena,
        )

    async def actualizar_perfil_publico(
        self, fundacion: Fundacion, data: PerfilPublicoUpdate
    ) -> OrganizacionPublicaOut:
        campos = data.model_dump(exclude_unset=True)
        areas = campos.pop("areas", None)
        for k, v in campos.items():
            setattr(fundacion, k, v)
        if "tipo_organizacion" in campos:
            fundacion.constituida_legalmente = fundacion.tipo_organizacion == "FUNDACION" or bool(
                fundacion.nit
            )
        if areas is not None:
            unicas = list(dict.fromkeys(areas))
            validas = set(
                (await self.db.execute(select(AreaImpacto.id).where(AreaImpacto.id.in_(unicas))))
                .scalars()
                .all()
            )
            if len(validas) != len(unicas):
                raise AppError("Hay áreas de impacto que no existen.", 422)
            await self.db.execute(
                delete(fundacion_areas).where(fundacion_areas.c.fundacion_id == fundacion.id)
            )
            for aid in unicas:
                await self.db.execute(
                    insert(fundacion_areas).values(fundacion_id=fundacion.id, area_id=aid)
                )
        fundacion.fecha_actualizacion = _now()
        await self.db.commit()
        usuario = await self.db.get(Usuario, fundacion.usuario_id)
        return await self.perfil_publico(fundacion.id, usuario)

    # ─────────────── Galería (control de imagen) ───────────────

    async def subir_galeria(
        self,
        fundacion: Fundacion,
        archivo: UploadFile,
        descripcion: str | None,
        contiene_menores: bool,
        autorizacion_imagen: bool,
    ) -> GaleriaItem:
        if not autorizacion_imagen:
            raise AppError(
                "Debes confirmar que cuentas con la autorización de las personas que aparecen "
                "en la imagen (y de sus representantes legales si son menores de edad).",
                422,
            )
        total = (
            await self.db.execute(
                select(func.count())
                .select_from(FundacionGaleria)
                .where(FundacionGaleria.fundacion_id == fundacion.id)
            )
        ).scalar_one()
        if total >= MAX_GALERIA:
            raise ConflictError(f"La galería admite hasta {MAX_GALERIA} imágenes.")
        ruta = await self.storage.guardar_imagen(archivo, "galeria")
        item = FundacionGaleria(
            fundacion_id=fundacion.id,
            ruta=ruta,
            descripcion=(descripcion or None) and descripcion[:200],
            contiene_menores=contiene_menores,
            autorizacion_imagen=True,
            orden=total,
        )
        self.db.add(item)
        await self.db.flush()
        salida = GaleriaItem.model_validate(item)
        await self.db.commit()
        return salida

    async def eliminar_galeria(self, fundacion: Fundacion, item_id: uuid.UUID) -> None:
        item = await self.db.get(FundacionGaleria, item_id)
        if item is None or item.fundacion_id != fundacion.id:
            raise NotFoundError("Imagen no encontrada.")
        await self.db.delete(item)
        await self.db.commit()

    # ─────────────── Documentos y verificación ───────────────

    async def _documentos(self, fundacion_id: uuid.UUID) -> list[FundacionDocumento]:
        return list(
            (
                await self.db.execute(
                    select(FundacionDocumento)
                    .where(FundacionDocumento.fundacion_id == fundacion_id)
                    .order_by(FundacionDocumento.fecha_subida.desc())
                )
            ).scalars().all()
        )

    async def estado_verificacion(self, fundacion: Fundacion) -> VerificacionEstadoOut:
        return VerificacionEstadoOut(
            estado=fundacion.verificacion_documental,
            nota=fundacion.verificacion_documental_nota,
            fecha=fundacion.verificacion_documental_fecha,
            documentos=[
                DocumentoVerifOut.model_validate(d) for d in await self._documentos(fundacion.id)
            ],
        )

    async def subir_documento(
        self, fundacion: Fundacion, tipo_documento: str, archivo: UploadFile
    ) -> VerificacionEstadoOut:
        if tipo_documento not in TIPOS_DOCUMENTO_VERIF:
            raise AppError(f"tipo_documento debe ser uno de {TIPOS_DOCUMENTO_VERIF}.", 422)
        if len(await self._documentos(fundacion.id)) >= 10:
            raise ConflictError("Máximo 10 documentos por organización.")
        ruta = await self.storage.guardar_documento(archivo, "verificacion")  # PRIVADO
        self.db.add(
            FundacionDocumento(
                fundacion_id=fundacion.id,
                tipo_documento=tipo_documento,
                nombre_original=(archivo.filename or "documento")[:200],
                ruta_archivo=ruta,
                validado=False,
            )
        )
        await self.db.commit()
        return await self.estado_verificacion(fundacion)

    async def eliminar_documento(
        self, fundacion: Fundacion, documento_id: uuid.UUID
    ) -> VerificacionEstadoOut:
        doc = await self.db.get(FundacionDocumento, documento_id)
        if doc is None or doc.fundacion_id != fundacion.id:
            raise NotFoundError("Documento no encontrado.")
        if fundacion.verificacion_documental == VD_EN_REVISION:
            raise ConflictError("No puedes eliminar documentos mientras están en revisión.")
        self.storage.eliminar_privado(doc.ruta_archivo)
        await self.db.delete(doc)
        await self.db.commit()
        return await self.estado_verificacion(fundacion)

    async def solicitar_verificacion(self, fundacion: Fundacion) -> VerificacionEstadoOut:
        if fundacion.verificacion_documental in (VD_EN_REVISION, VD_VERIFICADA):
            raise ConflictError("Tu solicitud ya está en revisión o fue aprobada.")
        if not await self._documentos(fundacion.id):
            raise ConflictError("Sube al menos un documento antes de solicitar la verificación.")
        fundacion.verificacion_documental = VD_EN_REVISION
        fundacion.verificacion_documental_nota = None
        fundacion.verificacion_documental_fecha = _now()
        await self.db.commit()
        return await self.estado_verificacion(fundacion)

    async def resolver_verificacion(
        self, admin: Usuario, fundacion_id: uuid.UUID, accion: str, nota: str | None
    ) -> Fundacion:
        """Aprueba, rechaza, pide más información o revoca (solo administradores)."""
        f = await self.db.get(Fundacion, fundacion_id)
        if f is None:
            raise NotFoundError("Organización no encontrada.")
        if accion not in ("APROBAR", "RECHAZAR", "PEDIR_INFO", "REVOCAR"):
            raise AppError("Acción no válida.", 422)
        if accion in ("RECHAZAR", "PEDIR_INFO", "REVOCAR") and not (nota and nota.strip()):
            raise AppError("Indica una nota para el solicitante.", 422)
        if accion == "REVOCAR" and f.verificacion_documental != VD_VERIFICADA:
            raise ConflictError("Solo se puede revocar una verificación aprobada.")
        if accion != "REVOCAR" and f.verificacion_documental != VD_EN_REVISION:
            raise ConflictError("La organización no tiene una solicitud en revisión.")

        nuevo = {
            "APROBAR": VD_VERIFICADA,
            "RECHAZAR": VD_RECHAZADA,
            "PEDIR_INFO": VD_INFO_REQUERIDA,
            "REVOCAR": VD_REVOCADA,
        }[accion]
        f.verificacion_documental = nuevo
        f.verificacion_documental_nota = nota
        f.verificacion_documental_fecha = _now()
        f.verificacion_documental_por = admin.id
        if accion == "APROBAR":
            for d in await self._documentos(f.id):
                d.validado = True
        mensajes = {
            "APROBAR": "¡Tu organización fue verificada! Ahora muestra la insignia de verificación.",
            "RECHAZAR": f"Tu solicitud de verificación fue rechazada. {nota}",
            "PEDIR_INFO": f"Necesitamos más información para verificar tu organización. {nota}",
            "REVOCAR": f"Tu verificación fue revocada. {nota}",
        }
        await self.notif.notificar(
            f.usuario_id, TIPO_VERIFICACION_ACTUALIZADA, mensajes[accion], "fundacion", f.id
        )
        return f

    # ─────────────── Reseñas (R12) ───────────────

    async def _participo(self, voluntario_id: uuid.UUID, fundacion_id: uuid.UUID) -> bool:
        return (
            await self.db.execute(
                select(Postulacion.id)
                .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
                .where(
                    Postulacion.voluntario_id == voluntario_id,
                    Postulacion.estado == ESTADO_ASISTIO,
                    Publicacion.fundacion_id == fundacion_id,
                )
                .limit(1)
            )
        ).first() is not None

    async def crear_resena(
        self, voluntario: Voluntario, fundacion_id: uuid.UUID, data: ResenaCreate
    ) -> ResenaOut:
        f = await self.db.get(Fundacion, fundacion_id)
        if f is None:
            raise NotFoundError("Organización no encontrada.")
        if not await self._participo(voluntario.id, fundacion_id):
            raise ForbiddenError(
                "Solo pueden reseñar las personas con participación confirmada en una "
                "actividad de esta organización."
            )
        ya = (
            await self.db.execute(
                select(ResenaOrganizacion.id).where(
                    ResenaOrganizacion.fundacion_id == fundacion_id,
                    ResenaOrganizacion.voluntario_id == voluntario.id,
                )
            )
        ).first()
        if ya:
            raise ConflictError("Ya reseñaste a esta organización.")
        motivo = motivo_moderacion(data.comentario)
        resena = ResenaOrganizacion(
            fundacion_id=fundacion_id,
            voluntario_id=voluntario.id,
            calificacion=data.calificacion,
            comentario=data.comentario,
            estado=RESENA_PENDIENTE if motivo else RESENA_VISIBLE,
            motivo_moderacion=motivo,
        )
        self.db.add(resena)
        await self.db.flush()
        if not motivo:
            await self.notif.notificar(
                f.usuario_id, TIPO_NUEVA_RESENA,
                f"Recibiste una reseña de {data.calificacion}/5.", "fundacion", f.id,
            )
        salida = await self._resena_a_out(resena)
        await self.db.commit()
        return salida

    async def listar_resenas(
        self, fundacion_id: uuid.UUID, page: int, per_page: int
    ) -> ResenasPage:
        condicion = (
            ResenaOrganizacion.fundacion_id == fundacion_id,
            ResenaOrganizacion.estado == RESENA_VISIBLE,
        )
        total = (
            await self.db.execute(
                select(func.count()).select_from(ResenaOrganizacion).where(*condicion)
            )
        ).scalar_one()
        filas = (
            await self.db.execute(
                select(ResenaOrganizacion)
                .where(*condicion)
                .order_by(ResenaOrganizacion.fecha_creacion.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).scalars().all()
        return ResenasPage(
            data=[await self._resena_a_out(r) for r in filas],
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
            resumen=await self._resumen_resenas(fundacion_id),
        )

    async def responder_resena(
        self, fundacion: Fundacion, resena_id: uuid.UUID, respuesta: str
    ) -> ResenaOut:
        r = await self.db.get(ResenaOrganizacion, resena_id)
        if r is None or r.fundacion_id != fundacion.id:
            raise NotFoundError("Reseña no encontrada.")
        if r.estado != RESENA_VISIBLE:
            raise ConflictError("Solo se pueden responder reseñas publicadas.")
        if motivo := motivo_moderacion(respuesta):
            raise AppError(f"La respuesta no se puede publicar: {motivo}", 422)
        r.respuesta = respuesta
        r.fecha_respuesta = _now()
        vol = await self.db.get(Voluntario, r.voluntario_id)
        if vol:
            await self.notif.notificar(
                vol.usuario_id, TIPO_RESENA_RESPONDIDA,
                f"«{fundacion.nombre}» respondió tu reseña.", "fundacion", fundacion.id,
            )
        salida = await self._resena_a_out(r)
        await self.db.commit()
        return salida

    async def moderar_resena(
        self, resena_id: uuid.UUID, accion: str, motivo: str | None
    ) -> ResenaOrganizacion:
        r = await self.db.get(ResenaOrganizacion, resena_id)
        if r is None:
            raise NotFoundError("Reseña no encontrada.")
        if accion == "APROBAR":
            r.estado = RESENA_VISIBLE
            r.motivo_moderacion = None
        elif accion == "OCULTAR":
            if not (motivo and motivo.strip()):
                raise AppError("Indica el motivo para ocultar la reseña.", 422)
            r.estado = RESENA_OCULTA
            r.motivo_moderacion = motivo
        else:
            raise AppError("Acción no válida.", 422)
        return r


# Constantes re-exportadas para quienes importan desde este módulo.
__all__ = ["AVISO_VERIFICACION", "VD_NO_SOLICITADA", "OrganizacionService"]

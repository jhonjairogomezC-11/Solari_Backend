"""Reglas de negocio de postulaciones."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.notificacion import (
    TIPO_NUEVA_POSTULACION,
    TIPO_POSTULACION_ACEPTADA,
    TIPO_POSTULACION_RECHAZADA,
    TIPO_POSTULACION_RETIRADA,
    TIPO_VOLUNTARIO_ASISTIO,
    TIPO_VOLUNTARIO_NO_ASISTIO,
)
from app.models.postulacion import (
    ESTADO_ACEPTADO,
    ESTADO_ASISTIO,
    ESTADO_NO_ASISTIO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    ESTADO_RETIRADO,
    Postulacion,
)
from app.models.publicacion import ESTADO_PUBLICADA
from app.repositories.postulacion_repo import PostulacionRepository
from app.repositories.publicacion_repo import PublicacionRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.postulacion import (
    ConfirmarAsistencia,
    PaginatedResponse,
    PostulacionCreate,
    PostulacionOut,
    PostulacionResponder,
)
from app.services.notificacion_service import NotificacionService


def _now() -> datetime:
    return datetime.now(UTC)


def _page(filas, total, page, per_page):
    return PaginatedResponse(
        data=[PostulacionOut.model_validate(f) for f in filas],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 1,
    )


class PostulacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PostulacionRepository(db)
        self.pub_repo = PublicacionRepository(db)
        self.usr_repo = UsuarioRepository(db)
        self.notif = NotificacionService(db)

    async def postular(
        self, voluntario_id: uuid.UUID, data: PostulacionCreate
    ) -> Postulacion:
        pub = await self.pub_repo.por_id(data.publicacion_id)
        if pub is None or pub.estado != ESTADO_PUBLICADA or pub.oculta_por_admin:
            raise NotFoundError("Convocatoria no disponible.")

        if await self.repo.existe(data.publicacion_id, voluntario_id):
            raise ConflictError("Ya te postulaste a esta convocatoria.")

        # Verifica cupo disponible.
        aceptadas = await self.repo.contar_aceptadas(data.publicacion_id)
        if aceptadas >= pub.cupo_maximo:
            raise ConflictError("Esta convocatoria ya alcanzó su cupo máximo.")

        post = await self.repo.crear(data.publicacion_id, voluntario_id, data.mensaje_voluntario)

        # Notifica a la fundación dueña.
        await self._notificar_fundacion(
            pub.fundacion_id,
            TIPO_NUEVA_POSTULACION,
            f"Tienes una nueva postulación en «{pub.titulo}».",
            pub.id,
        )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def _notificar_fundacion(
        self, fundacion_id: uuid.UUID, tipo: str, mensaje: str, objeto_id: uuid.UUID
    ) -> None:
        from app.models.fundacion import Fundacion

        fundacion = await self.db.get(Fundacion, fundacion_id)
        if fundacion is not None:
            await self.notif.notificar(
                fundacion.usuario_id, tipo, mensaje, "publicacion", objeto_id
            )

    async def _notificar_voluntario(
        self, voluntario_id: uuid.UUID, tipo: str, mensaje: str, objeto_id: uuid.UUID
    ) -> None:
        from app.models.voluntario import Voluntario

        vol = await self.db.get(Voluntario, voluntario_id)
        if vol is not None:
            await self.notif.notificar(
                vol.usuario_id, tipo, mensaje, "postulacion", objeto_id
            )

    async def retirar(
        self, postulacion_id: uuid.UUID, voluntario_id: uuid.UUID
    ) -> Postulacion:
        post = await self.repo.por_id(postulacion_id)
        if post is None or post.voluntario_id != voluntario_id:
            raise NotFoundError("Postulación no encontrada.")
        if post.estado in (ESTADO_RETIRADO, ESTADO_RECHAZADO):
            raise ConflictError("Esta postulación ya no puede retirarse.")
        post.estado = ESTADO_RETIRADO
        post.fecha_actualizacion = _now()

        pub = await self.pub_repo.por_id(post.publicacion_id)
        if pub is not None:
            await self._notificar_fundacion(
                pub.fundacion_id,
                TIPO_POSTULACION_RETIRADA,
                f"Un voluntario retiró su postulación de «{pub.titulo}».",
                pub.id,
            )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def _post_de_fundacion(
        self, postulacion_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> Postulacion:
        post = await self.repo.por_id(postulacion_id)
        if post is None:
            raise NotFoundError("Postulación no encontrada.")
        pub = await self.pub_repo.por_id(post.publicacion_id)
        if pub is None or pub.fundacion_id != fundacion_id:
            raise ForbiddenError("No tienes permiso sobre esta postulación.")
        return post

    async def responder(
        self, postulacion_id: uuid.UUID, fundacion_id: uuid.UUID, data: PostulacionResponder
    ) -> Postulacion:
        post = await self._post_de_fundacion(postulacion_id, fundacion_id)
        if post.estado != ESTADO_PENDIENTE:
            raise ConflictError("Esta postulación ya fue respondida.")
        if data.estado not in (ESTADO_ACEPTADO, ESTADO_RECHAZADO):
            raise ConflictError("Solo puedes aceptar o rechazar una postulación pendiente.")

        post.estado = data.estado
        post.motivo_rechazo = data.motivo_rechazo if data.estado == ESTADO_RECHAZADO else None
        post.comentario_fundacion = data.comentario_fundacion
        post.fecha_respuesta = _now()
        post.fecha_actualizacion = _now()

        pub = await self.pub_repo.por_id(post.publicacion_id)
        titulo = pub.titulo if pub else "una convocatoria"
        if data.estado == ESTADO_ACEPTADO:
            await self._notificar_voluntario(
                post.voluntario_id, TIPO_POSTULACION_ACEPTADA,
                f"¡Tu postulación a «{titulo}» fue aceptada!", post.id,
            )
        else:
            await self._notificar_voluntario(
                post.voluntario_id, TIPO_POSTULACION_RECHAZADA,
                f"Tu postulación a «{titulo}» fue rechazada.", post.id,
            )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def confirmar_asistencia(
        self,
        postulacion_id: uuid.UUID,
        fundacion_id: uuid.UUID,
        data: ConfirmarAsistencia,
    ) -> Postulacion:
        post = await self._post_de_fundacion(postulacion_id, fundacion_id)
        if post.estado != ESTADO_ACEPTADO:
            raise ConflictError("Solo puedes confirmar asistencia de postulaciones aceptadas.")

        if data.asistio:
            post.estado = ESTADO_ASISTIO
            post.calificacion = data.calificacion
            tipo = TIPO_VOLUNTARIO_ASISTIO
            msg = "Se confirmó tu asistencia. ¡Gracias por tu aporte!"
        else:
            post.estado = ESTADO_NO_ASISTIO
            tipo = TIPO_VOLUNTARIO_NO_ASISTIO
            msg = "Se registró que no asististe a la convocatoria."
        post.comentario_fundacion = data.comentario_fundacion
        post.fecha_confirmacion = _now()
        post.fecha_actualizacion = _now()

        await self._notificar_voluntario(post.voluntario_id, tipo, msg, post.id)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def mis_postulaciones(
        self, voluntario_id: uuid.UUID, page: int, per_page: int
    ) -> PaginatedResponse[PostulacionOut]:
        filas, total = await self.repo.mis_postulaciones(voluntario_id, page, per_page)
        return _page(filas, total, page, per_page)

    async def de_publicacion(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID, page: int, per_page: int
    ) -> PaginatedResponse[PostulacionOut]:
        pub = await self.pub_repo.por_id_y_fundacion(publicacion_id, fundacion_id)
        if pub is None:
            raise NotFoundError("Convocatoria no encontrada.")
        filas, total = await self.repo.de_publicacion(publicacion_id, page, per_page)
        return _page(filas, total, page, per_page)

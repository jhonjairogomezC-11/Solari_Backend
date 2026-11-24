"""Mensajería entre el voluntario y la organización dentro de una postulación.

Reglas:
- Solo las dos partes (el voluntario postulado y la organización dueña de la
  convocatoria) pueden leer o escribir. A cualquier otro usuario se le responde 404
  para no revelar que la postulación existe.
- Se puede escribir mientras la postulación está activa (ACEPTADO, EN_REVISION,
  LISTA_ESPERA). Desde ASISTIO, NO_ASISTIO, RETIRADO, RECHAZADO o
  CANCELADO_FUNDACION la conversación queda de solo lectura: el historial se ve,
  pero no se envían mensajes nuevos.
- No se exponen datos personales: el voluntario aparece con su primer nombre, la
  organización con su nombre, y se rechazan mensajes con correos, teléfonos o enlaces.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.fundacion import Fundacion
from app.models.notificacion import TIPO_NUEVO_MENSAJE, Notificacion
from app.models.postulacion import (
    ESTADO_ACEPTADO,
    ESTADO_ASISTIO,
    ESTADO_EN_REVISION,
    ESTADO_LISTA_ESPERA,
    Postulacion,
)
from app.models.publicacion import Publicacion
from app.models.usuario import ROL_FUNDACION, ROL_VOLUNTARIO, Usuario
from app.models.voluntario import Voluntario
from app.repositories.mensaje_postulacion_repo import MensajePostulacionRepository
from app.schemas.mensaje_postulacion import (
    ConversacionPostulacionOut,
    MensajePostulacionInput,
    MensajePostulacionOut,
)
from app.services.coincidencia import contiene_datos_personales
from app.services.notificacion_service import NotificacionService
from app.services.ofrecimiento_service import primer_nombre

OBJETO_TIPO = "postulacion"

# Estados en los que se muestra el chat (botón "Mensajes" en el frontend).
ESTADOS_CHAT_VISIBLE = frozenset(
    {ESTADO_ACEPTADO, ESTADO_EN_REVISION, ESTADO_LISTA_ESPERA, ESTADO_ASISTIO}
)
# Estados en los que se puede enviar. El resto es de solo lectura.
ESTADOS_CHAT_ESCRITURA = frozenset({ESTADO_ACEPTADO, ESTADO_EN_REVISION, ESTADO_LISTA_ESPERA})

MENSAJE_DATOS_PERSONALES = (
    "Por seguridad no compartas correos, teléfonos ni enlaces. "
    "Coordinen los detalles dentro de la plataforma."
)


def puede_escribir(estado: str) -> bool:
    return estado in ESTADOS_CHAT_ESCRITURA


class _Contexto:
    __slots__ = ("post", "pub", "vol", "fund", "rol")

    def __init__(
        self, post: Postulacion, pub: Publicacion, vol: Voluntario, fund: Fundacion, rol: str
    ):
        self.post = post
        self.pub = pub
        self.vol = vol
        self.fund = fund
        self.rol = rol

    def contraparte_usuario_id(self) -> uuid.UUID:
        return self.fund.usuario_id if self.rol == ROL_VOLUNTARIO else self.vol.usuario_id


class MensajePostulacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MensajePostulacionRepository(db)
        self.notif = NotificacionService(db)

    async def _contexto(self, usuario: Usuario, postulacion_id: uuid.UUID) -> _Contexto:
        datos = await self.repo.contexto(postulacion_id)
        if datos is None:
            raise NotFoundError("Postulación no encontrada.")
        post, pub, vol, fund = datos
        if usuario.id == vol.usuario_id:
            rol = ROL_VOLUNTARIO
        elif usuario.id == fund.usuario_id:
            rol = ROL_FUNDACION
        else:
            raise NotFoundError("Postulación no encontrada.")
        return _Contexto(post, pub, vol, fund, rol)

    async def _nombre_voluntario(self, vol: Voluntario) -> str:
        u = await self.db.get(Usuario, vol.usuario_id)
        return primer_nombre(u.nombre) if u else "Voluntario"

    async def _conversacion(self, usuario: Usuario, ctx: _Contexto) -> ConversacionPostulacionOut:
        nombre_vol = await self._nombre_voluntario(ctx.vol)
        nombre_fund = ctx.fund.nombre or "Organización"
        salida: list[MensajePostulacionOut] = []
        for m in await self.repo.listar(ctx.post.id):
            es_vol = m.autor_id == ctx.vol.usuario_id
            salida.append(
                MensajePostulacionOut(
                    id=m.id,
                    autor_rol=ROL_VOLUNTARIO if es_vol else ROL_FUNDACION,
                    autor_nombre=nombre_vol if es_vol else nombre_fund,
                    mensaje=m.mensaje,
                    leido=bool(m.leido),
                    fecha_creacion=m.fecha_creacion,
                    es_mio=m.autor_id == usuario.id,
                )
            )
        return ConversacionPostulacionOut(
            postulacion_id=ctx.post.id,
            estado=ctx.post.estado,
            puede_escribir=puede_escribir(ctx.post.estado),
            convocatoria_titulo=ctx.pub.titulo,
            contraparte_nombre=nombre_fund if ctx.rol == ROL_VOLUNTARIO else nombre_vol,
            mensajes=salida,
        )

    async def listar(
        self, usuario: Usuario, postulacion_id: uuid.UUID
    ) -> ConversacionPostulacionOut:
        ctx = await self._contexto(usuario, postulacion_id)
        marcados = await self.repo.marcar_leidos_de_otros(ctx.post.id, usuario.id)
        # Al abrir la conversación, el aviso de "nuevo mensaje" ya no está pendiente.
        avisos = await self.db.execute(
            update(Notificacion)
            .where(
                Notificacion.usuario_id == usuario.id,
                Notificacion.tipo == TIPO_NUEVO_MENSAJE,
                Notificacion.objeto_tipo == OBJETO_TIPO,
                Notificacion.objeto_id == ctx.post.id,
                Notificacion.leida.is_(False),
            )
            .values(leida=True, fecha_lectura=datetime.now(UTC))
        )
        if marcados or (avisos.rowcount or 0):
            await self.db.commit()
        return await self._conversacion(usuario, ctx)

    async def enviar(
        self, usuario: Usuario, postulacion_id: uuid.UUID, data: MensajePostulacionInput
    ) -> ConversacionPostulacionOut:
        ctx = await self._contexto(usuario, postulacion_id)
        if not puede_escribir(ctx.post.estado):
            raise ConflictError(
                "Esta conversación es de solo lectura por el estado de la postulación."
            )
        if contiene_datos_personales(data.mensaje):
            raise AppError(MENSAJE_DATOS_PERSONALES, 422)

        await self.repo.crear(ctx.post.id, usuario.id, data.mensaje)

        destino = ctx.contraparte_usuario_id()
        # Una sola notificación sin leer por conversación (evita inundar la bandeja).
        ya = (
            await self.db.execute(
                select(Notificacion.id).where(
                    Notificacion.usuario_id == destino,
                    Notificacion.tipo == TIPO_NUEVO_MENSAJE,
                    Notificacion.objeto_tipo == OBJETO_TIPO,
                    Notificacion.objeto_id == ctx.post.id,
                    Notificacion.leida.is_(False),
                )
            )
        ).first()
        if not ya:
            remitente = (
                await self._nombre_voluntario(ctx.vol)
                if ctx.rol == ROL_VOLUNTARIO
                else (ctx.fund.nombre or "La organización")
            )
            await self.notif.notificar(
                destino,
                TIPO_NUEVO_MENSAJE,
                f"{remitente} te escribió sobre «{ctx.pub.titulo}».",
                OBJETO_TIPO,
                ctx.post.id,
            )
        await self.db.commit()
        return await self._conversacion(usuario, ctx)

    async def no_leidos(self, usuario: Usuario) -> int:
        return await self.repo.no_leidos_count(usuario.id)

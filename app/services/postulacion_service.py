"""Reglas de negocio de postulaciones.

Reglas del documento de grado que se cumplen aquí:
- R5: los cupos distinguen postulados de aceptados y nunca se asignan más cupos
  de los disponibles (se valida al postular Y al aceptar, con bloqueo de fila).
- R6: la organización decide; el sistema notifica con mensajes respetuosos basados
  en plantillas.
- R7: el voluntario puede retirarse con confirmación previa si ya fue aceptado; el
  retiro libera el cupo y notifica a la organización.
- R8: cada cambio de estado queda registrado con quién lo hizo.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.catalogo import Habilidad, Municipio
from app.models.fundacion import Fundacion
from app.models.gamificacion import VoluntarioPuntos
from app.models.habilidades import VoluntarioHabilidad
from app.models.notificacion import (
    TIPO_NUEVA_POSTULACION,
    TIPO_POSTULACION_ACEPTADA,
    TIPO_POSTULACION_ACTUALIZADA,
    TIPO_POSTULACION_RECHAZADA,
    TIPO_POSTULACION_RETIRADA,
    TIPO_VOLUNTARIO_ASISTIO,
    TIPO_VOLUNTARIO_NO_ASISTIO,
)
from app.models.postulacion import (
    ESTADO_ACEPTADO,
    ESTADO_ASISTIO,
    ESTADO_EN_REVISION,
    ESTADO_LISTA_ESPERA,
    ESTADO_NO_ASISTIO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    ESTADO_RETIRADO,
    Postulacion,
    PostulacionHistorial,
)
from app.models.publicacion import ESTADO_PUBLICADA, publicacion_habilidades
from app.models.usuario import Usuario
from app.models.voluntario import Voluntario
from app.repositories.postulacion_repo import PostulacionRepository
from app.repositories.publicacion_repo import PublicacionRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.postulacion import (
    ConfirmarAsistencia,
    PaginatedResponse,
    PostulacionCreate,
    PostulacionOut,
    PostulacionResponder,
    PostulanteOut,
    PostulantesPage,
    ResumenCupos,
    VoluntarioPostulante,
)
from app.services.coincidencia import calcular_coincidencia
from app.services.menores_service import (
    calcular_edad,
    es_menor,
    estado_autorizacion,
    validar_aceptacion_menor,
)
from app.services.notificacion_service import NotificacionService

RETIRABLES = (ESTADO_PENDIENTE, ESTADO_EN_REVISION, ESTADO_LISTA_ESPERA, ESTADO_ACEPTADO)
RESPONDIBLES = (ESTADO_PENDIENTE, ESTADO_EN_REVISION, ESTADO_LISTA_ESPERA)


def _now() -> datetime:
    return datetime.now(UTC)


def _edad(nacimiento: date) -> int:
    # Edad con la fecha de Bogotá (misma regla que la autorización de menores).
    return calcular_edad(nacimiento)


def _page(filas, total, page, per_page):
    return PaginatedResponse(
        data=[PostulacionOut.model_validate(f) for f in filas],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 1,
    )


# ── Plantillas de mensajes (R6): respetuosas, sin redacción manual ──
def msg_postulacion_recibida(titulo: str) -> str:
    return f"Recibimos tu postulación a «{titulo}». La organización la revisará pronto."


def msg_lista_espera(titulo: str) -> str:
    return (
        f"Tu postulación a «{titulo}» quedó en lista de espera porque los cupos están "
        "completos. Te avisaremos si se libera uno."
    )


def msg_aceptada(titulo: str) -> str:
    return (
        f"¡Tu postulación a «{titulo}» fue aceptada! Revisa los detalles de la "
        "actividad y prepárate para participar."
    )


def msg_rechazada(titulo: str, motivo: str | None) -> str:
    base = (
        f"Gracias por tu interés en «{titulo}». En esta ocasión la organización no "
        "pudo incluirte en la actividad. Valoramos el tiempo que ofreciste y te "
        "invitamos a seguir explorando otras convocatorias."
    )
    return f"{base} Mensaje de la organización: {motivo}" if motivo else base


def msg_en_revision(titulo: str) -> str:
    return f"La organización está revisando tu postulación a «{titulo}»."


class PostulacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PostulacionRepository(db)
        self.pub_repo = PublicacionRepository(db)
        self.usr_repo = UsuarioRepository(db)
        self.notif = NotificacionService(db)

    # ─────────────── Utilidades internas ───────────────

    def _historial(
        self,
        post: Postulacion,
        anterior: str | None,
        nuevo: str,
        actor_usuario_id: uuid.UUID | None,
        rol: str | None,
        motivo: str | None = None,
    ) -> None:
        self.db.add(
            PostulacionHistorial(
                postulacion_id=post.id,
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                cambiado_por=actor_usuario_id,
                rol_actor=rol,
                motivo=motivo,
            )
        )

    async def _notificar_fundacion(
        self, fundacion_id: uuid.UUID, tipo: str, mensaje: str, objeto_id: uuid.UUID
    ) -> None:
        fundacion = await self.db.get(Fundacion, fundacion_id)
        if fundacion is not None:
            await self.notif.notificar(
                fundacion.usuario_id, tipo, mensaje, "publicacion", objeto_id
            )

    async def _notificar_voluntario(
        self, voluntario_id: uuid.UUID, tipo: str, mensaje: str, objeto_id: uuid.UUID
    ) -> None:
        vol = await self.db.get(Voluntario, voluntario_id)
        if vol is not None:
            await self.notif.notificar(vol.usuario_id, tipo, mensaje, "postulacion", objeto_id)

    # ─────────────── Voluntario ───────────────

    async def postular(self, voluntario: Voluntario, data: PostulacionCreate) -> Postulacion:
        # Bloqueo de fila: evita condición de carrera al ocupar el último cupo.
        pub = await self.pub_repo.por_id_bloqueada(data.publicacion_id)
        if pub is None or pub.estado != ESTADO_PUBLICADA or pub.oculta_por_admin:
            raise NotFoundError("Convocatoria no disponible.")

        if pub.fecha_limite_postulacion is not None and date.today() > pub.fecha_limite_postulacion:
            raise ConflictError("La fecha límite de postulación ya pasó.")

        if await self.repo.existe(data.publicacion_id, voluntario.id):
            raise ConflictError("Ya te postulaste a esta convocatoria.")

        # Requisitos de edad (si la convocatoria los define).
        edad = _edad(voluntario.fecha_nacimiento)
        if pub.edad_minima is not None and edad < pub.edad_minima:
            raise ConflictError(f"Esta convocatoria requiere una edad mínima de {pub.edad_minima} años.")
        if pub.edad_maxima is not None and edad > pub.edad_maxima:
            raise ConflictError(f"Esta convocatoria admite hasta {pub.edad_maxima} años.")

        # Cupos: los pendientes no ocupan cupo; solo los aceptados (R5).
        aceptadas = await self.repo.contar_aceptadas(data.publicacion_id)
        en_lista_espera = aceptadas >= pub.cupo_maximo

        post = await self.repo.crear(
            data.publicacion_id,
            voluntario.id,
            data.mensaje_voluntario,
            lista_espera=en_lista_espera,
        )
        self._historial(post, None, post.estado, voluntario.usuario_id, "VOLUNTARIO")

        await self._notificar_fundacion(
            pub.fundacion_id,
            TIPO_NUEVA_POSTULACION,
            f"Tienes una nueva postulación en «{pub.titulo}».",
            pub.id,
        )
        await self.notif.notificar(
            voluntario.usuario_id,
            TIPO_POSTULACION_ACTUALIZADA,
            msg_lista_espera(pub.titulo) if en_lista_espera else msg_postulacion_recibida(pub.titulo),
            "postulacion",
            post.id,
        )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def retirar(
        self,
        postulacion_id: uuid.UUID,
        voluntario: Voluntario,
        confirmar: bool = False,
        motivo: str | None = None,
    ) -> Postulacion:
        post = await self.repo.por_id(postulacion_id)
        if post is None or post.voluntario_id != voluntario.id:
            raise NotFoundError("Postulación no encontrada.")
        if post.estado not in RETIRABLES:
            raise ConflictError("Esta postulación ya no puede retirarse.")
        estaba_aceptado = post.estado == ESTADO_ACEPTADO
        if estaba_aceptado and not confirmar:
            raise ConflictError(
                "Ya fuiste aceptado en esta actividad. Retirarte puede afectar la "
                "planificación de la organización. Confirma para continuar."
            )

        # Bloquea la convocatoria para calcular los cupos libres de forma consistente.
        pub = await self.pub_repo.por_id_bloqueada(post.publicacion_id)
        anterior = post.estado
        post.estado = ESTADO_RETIRADO
        post.fecha_actualizacion = _now()
        self._historial(post, anterior, ESTADO_RETIRADO, voluntario.usuario_id, "VOLUNTARIO", motivo)
        await self.db.flush()

        if pub is not None:
            nombre = (await self.db.get(Usuario, voluntario.usuario_id)).nombre
            if estaba_aceptado:
                aceptadas = await self.repo.contar_aceptadas(pub.id)
                libres = max(pub.cupo_maximo - aceptadas, 0)
                espera = await self.repo.contar_por_estado(pub.id, ESTADO_LISTA_ESPERA)
                msg = (
                    f"{nombre} se retiró de «{pub.titulo}». Quedan {libres} cupo(s) "
                    f"disponible(s) y {espera} persona(s) en lista de espera."
                )
            else:
                msg = f"{nombre} retiró su postulación de «{pub.titulo}»."
            await self._notificar_fundacion(
                pub.fundacion_id, TIPO_POSTULACION_RETIRADA, msg, pub.id
            )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def mis_postulaciones(
        self, voluntario_id: uuid.UUID, page: int, per_page: int
    ) -> PaginatedResponse[PostulacionOut]:
        filas, total = await self.repo.mis_postulaciones(voluntario_id, page, per_page)
        return _page(filas, total, page, per_page)

    # ─────────────── Organización ───────────────

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
        self, postulacion_id: uuid.UUID, fundacion: Fundacion, data: PostulacionResponder
    ) -> Postulacion:
        post = await self._post_de_fundacion(postulacion_id, fundacion.id)
        if post.estado not in RESPONDIBLES:
            raise ConflictError("Esta postulación ya fue respondida.")
        if data.estado == post.estado:
            raise ConflictError("La postulación ya está en ese estado.")

        # Bloqueo de la convocatoria: la validación de cupo y el cambio son atómicos.
        pub = await self.pub_repo.por_id_bloqueada(post.publicacion_id)
        titulo = pub.titulo if pub else "una convocatoria"
        if data.estado == ESTADO_ACEPTADO:
            # Menores: solo con la autorización del acudiente aprobada.
            vol = await self.db.get(Voluntario, post.voluntario_id)
            if vol is not None:
                validar_aceptacion_menor(vol.fecha_nacimiento, vol.autorizacion_estado)
        if data.estado == ESTADO_ACEPTADO and pub is not None:
            ocupados = await self.repo.contar_aceptadas(pub.id)
            if ocupados >= pub.cupo_maximo:
                raise ConflictError(
                    "No quedan cupos disponibles. Para aceptar a otra persona, "
                    "libera un cupo o amplía los cupos de la convocatoria."
                )

        anterior = post.estado
        post.estado = data.estado
        post.motivo_rechazo = data.motivo_rechazo if data.estado == ESTADO_RECHAZADO else None
        post.comentario_fundacion = data.comentario_fundacion
        post.fecha_respuesta = _now()
        post.fecha_actualizacion = _now()
        self._historial(
            post, anterior, data.estado, fundacion.usuario_id, "FUNDACION", data.motivo_rechazo
        )

        if data.estado == ESTADO_ACEPTADO:
            await self._notificar_voluntario(
                post.voluntario_id, TIPO_POSTULACION_ACEPTADA, msg_aceptada(titulo), post.id
            )
        elif data.estado == ESTADO_RECHAZADO:
            await self._notificar_voluntario(
                post.voluntario_id,
                TIPO_POSTULACION_RECHAZADA,
                msg_rechazada(titulo, data.motivo_rechazo),
                post.id,
            )
        elif data.estado == ESTADO_LISTA_ESPERA:
            await self._notificar_voluntario(
                post.voluntario_id, TIPO_POSTULACION_ACTUALIZADA, msg_lista_espera(titulo), post.id
            )
        else:  # EN_REVISION
            await self._notificar_voluntario(
                post.voluntario_id, TIPO_POSTULACION_ACTUALIZADA, msg_en_revision(titulo), post.id
            )
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def confirmar_asistencia(
        self,
        postulacion_id: uuid.UUID,
        fundacion: Fundacion,
        data: ConfirmarAsistencia,
    ) -> Postulacion:
        post = await self._post_de_fundacion(postulacion_id, fundacion.id)
        if post.estado != ESTADO_ACEPTADO:
            raise ConflictError("Solo puedes confirmar asistencia de postulaciones aceptadas.")

        anterior = post.estado
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
        self._historial(post, anterior, post.estado, fundacion.usuario_id, "FUNDACION")

        await self._notificar_voluntario(post.voluntario_id, tipo, msg, post.id)

        # Al confirmar ASISTENCIA: otorgar XP, actualizar horas/estadísticas y logros.
        if data.asistio:
            from app.services.gamificacion_service import GamificacionService

            voluntario = await self.db.get(Voluntario, post.voluntario_id)
            pub = await self.pub_repo.por_id(post.publicacion_id)
            if voluntario is not None and pub is not None:
                await GamificacionService(self.db).otorgar_por_asistencia(voluntario, post, pub)

        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def de_publicacion(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID, page: int, per_page: int
    ) -> PostulantesPage:
        pub = await self.pub_repo.por_id_y_fundacion(publicacion_id, fundacion_id)
        if pub is None:
            raise NotFoundError("Convocatoria no encontrada.")
        filas, total = await self.repo.de_publicacion(publicacion_id, page, per_page)

        req_ids = set(
            (
                await self.db.execute(
                    select(publicacion_habilidades.c.habilidad_id).where(
                        publicacion_habilidades.c.publicacion_id == publicacion_id
                    )
                )
            )
            .scalars()
            .all()
        )
        nombres_req = {}
        if req_ids:
            nombres_req = {
                h.id: h.nombre
                for h in (
                    await self.db.execute(select(Habilidad).where(Habilidad.id.in_(req_ids)))
                )
                .scalars()
                .all()
            }

        vol_ids = [p.voluntario_id for p in filas]
        voluntarios: dict[uuid.UUID, tuple[Voluntario, str, str | None]] = {}
        habs: dict[uuid.UUID, dict[int, str]] = {}
        puntos: dict[uuid.UUID, int] = {}
        if vol_ids:
            rows = (
                await self.db.execute(
                    select(Voluntario, Usuario.nombre, Municipio.nombre)
                    .join(Usuario, Usuario.id == Voluntario.usuario_id)
                    .outerjoin(Municipio, Municipio.id == Voluntario.municipio_id)
                    .where(Voluntario.id.in_(vol_ids))
                )
            ).all()
            voluntarios = {v.id: (v, n, m) for v, n, m in rows}
            for vid, hid, hn in (
                await self.db.execute(
                    select(VoluntarioHabilidad.voluntario_id, Habilidad.id, Habilidad.nombre)
                    .join(Habilidad, Habilidad.id == VoluntarioHabilidad.habilidad_id)
                    .where(VoluntarioHabilidad.voluntario_id.in_(vol_ids))
                )
            ).all():
                habs.setdefault(vid, {})[hid] = hn
            for vid, xp in (
                await self.db.execute(
                    select(VoluntarioPuntos.voluntario_id, VoluntarioPuntos.total_historico).where(
                        VoluntarioPuntos.voluntario_id.in_(vol_ids)
                    )
                )
            ).all():
                puntos[vid] = xp

        data: list[PostulanteOut] = []
        for p in filas:
            out = PostulanteOut.model_validate(p)
            if p.voluntario_id in voluntarios:
                v, nombre, municipio = voluntarios[p.voluntario_id]
                poseidas = habs.get(p.voluntario_id, {})
                out.voluntario = VoluntarioPostulante(
                    nombre=nombre,
                    foto_perfil=v.foto_perfil,
                    municipio=municipio,
                    disponibilidad=v.disponibilidad,
                    experiencia=v.experiencia,
                    descripcion=v.descripcion,
                    idiomas=v.idiomas,
                    profesion=v.profesion,
                    esta_verificado=v.esta_verificado,
                    horas_acumuladas=v.horas_acumuladas or 0,
                    actividades_completadas=v.actividades_completadas or 0,
                    xp_total=puntos.get(p.voluntario_id, 0),
                    habilidades=sorted(poseidas.values()),
                    habilidades_coinciden=sorted(
                        nombres_req[i] for i in req_ids if i in poseidas
                    ),
                    coincidencia=calcular_coincidencia(req_ids, poseidas.keys()),
                    menor_de_edad=es_menor(v.fecha_nacimiento),
                    autorizacion_estado=(
                        estado_autorizacion(v.fecha_nacimiento, v.autorizacion_estado)
                        if es_menor(v.fecha_nacimiento)
                        else None
                    ),
                )
            data.append(out)

        aceptados = await self.repo.contar_aceptadas(publicacion_id)
        pendientes = (
            await self.repo.contar_por_estado(publicacion_id, ESTADO_PENDIENTE)
            + await self.repo.contar_por_estado(publicacion_id, ESTADO_EN_REVISION)
        )
        return PostulantesPage(
            data=data,
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
            resumen=ResumenCupos(
                cupo_maximo=pub.cupo_maximo,
                aceptados=aceptados,
                disponibles=max(pub.cupo_maximo - aceptados, 0),
                pendientes=pendientes,
                lista_espera=await self.repo.contar_por_estado(publicacion_id, ESTADO_LISTA_ESPERA),
            ),
        )

    # ─────────────── Historial (R8) ───────────────

    async def historial(self, postulacion_id: uuid.UUID, usuario: Usuario) -> list[PostulacionHistorial]:
        post = await self.repo.por_id(postulacion_id)
        if post is None:
            raise NotFoundError("Postulación no encontrada.")
        permitido = usuario.rol == "ADMIN"
        if not permitido:
            vol = await self.db.get(Voluntario, post.voluntario_id)
            pub = await self.pub_repo.por_id(post.publicacion_id)
            fund = await self.db.get(Fundacion, pub.fundacion_id) if pub else None
            permitido = bool(
                (vol and vol.usuario_id == usuario.id) or (fund and fund.usuario_id == usuario.id)
            )
        if not permitido:
            raise NotFoundError("Postulación no encontrada.")
        stmt = (
            select(PostulacionHistorial)
            .where(PostulacionHistorial.postulacion_id == postulacion_id)
            .order_by(PostulacionHistorial.fecha)
        )
        return list((await self.db.execute(stmt)).scalars().all())


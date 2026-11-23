"""Gestión administrativa de soporte, privacidad, verificación y reseñas.

Controles de seguridad de las solicitudes de cuenta/privacidad:
- Nunca se ejecutan solas: el administrador debe aprobar Y pedir ejecutar.
- Un administrador no puede resolver solicitudes sobre su propia cuenta.
- No se ejecutan sobre cuentas de administrador.
- Toda resolución queda en la auditoría con quién, cuándo y por qué.
- La eliminación anonimiza los datos personales y CONSERVA los registros que
  tienen valor legal o de trazabilidad (postulaciones, puntos, aceptaciones
  legales), como exige el tratamiento de datos de la Ley 1581 de 2012.
"""

from __future__ import annotations

import math
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.admin_accion import HistorialEstadoVoluntario
from app.models.cuenta import PreferenciasNotificacion
from app.models.fundacion import ESTADO_SUSPENDIDA, Fundacion
from app.models.notificacion import TIPO_CUENTA_ACTUALIZADA, TIPO_RESPUESTA_SOPORTE
from app.models.ofrecimiento import OF_DISPONIBLE, OF_FINALIZADO, Ofrecimiento
from app.models.organizacion import (
    RESENA_PENDIENTE,
    FundacionDocumento,
    ResenaOrganizacion,
)
from app.models.publicacion import Publicacion
from app.models.soporte import (
    ESTADO_EN_REVISION,
    SOL_BLOQUEO_TEMPORAL,
    SOL_ELIMINACION_CUENTA,
    SOL_ELIMINACION_DATOS,
    SOL_ESTADO_APROBADA,
    SOL_ESTADO_COMPLETADA,
    SOL_ESTADO_EN_PROCESO,
    SOL_ESTADO_RECHAZADA,
    SOL_INHABILITACION,
    SolicitudCuenta,
    TicketMensaje,
    TicketSoporte,
)
from app.models.usuario import (
    ESTADO_BLOQUEADO,
    ESTADO_SUSPENDIDO,
    ROL_ADMIN,
    ROL_FUNDACION,
    ROL_VOLUNTARIO,
    Usuario,
)
from app.models.voluntario import Voluntario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.admin import PaginatedAdmin
from app.schemas.admin_gestion import (
    AdminResenaOut,
    AdminResolverSolicitud,
    AdminSolicitudOut,
    AdminTicketDetalle,
    AdminTicketOut,
    AdminVerificacionOut,
    AuditoriaOut,
)
from app.schemas.organizacion import DocumentoVerifOut
from app.schemas.soporte import TicketMensajeOut
from app.services.auditoria_service import AuditoriaService
from app.services.notificacion_service import NotificacionService
from app.services.organizacion_service import OrganizacionService
from app.services.storage_service import StorageService
from app.services.token_service import TokenService

_EJECUTABLES = (
    SOL_BLOQUEO_TEMPORAL, SOL_INHABILITACION, SOL_ELIMINACION_CUENTA, SOL_ELIMINACION_DATOS,
)
_ELIMINACIONES = (SOL_ELIMINACION_CUENTA, SOL_ELIMINACION_DATOS)


def _now() -> datetime:
    return datetime.now(UTC)


def _pagina(data: list, total: int, page: int, per_page: int) -> PaginatedAdmin:
    return PaginatedAdmin(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 1,
    )


class AdminGestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditoriaService(db)
        self.notif = NotificacionService(db)
        self.storage = StorageService(get_settings())

    # ─────────────── Tickets de soporte ───────────────

    async def listar_tickets(
        self, page: int, per_page: int, estado: str | None, categoria: str | None, buscar: str | None
    ) -> PaginatedAdmin[AdminTicketOut]:
        cond = []
        if estado:
            cond.append(TicketSoporte.estado == estado)
        if categoria:
            cond.append(TicketSoporte.categoria == categoria)
        if buscar:
            termino = f"%{buscar}%"
            filtros = [TicketSoporte.asunto.ilike(termino), Usuario.email.ilike(termino)]
            if buscar.lstrip("#").isdigit():
                filtros.append(TicketSoporte.numero == int(buscar.lstrip("#")))
            cond.append(or_(*filtros))
        base = select(TicketSoporte, Usuario.nombre, Usuario.email).join(
            Usuario, Usuario.id == TicketSoporte.usuario_id
        )
        total = (
            await self.db.execute(
                select(func.count())
                .select_from(TicketSoporte)
                .join(Usuario, Usuario.id == TicketSoporte.usuario_id)
                .where(*cond)
            )
        ).scalar_one()
        filas = (
            await self.db.execute(
                base.where(*cond)
                .order_by(TicketSoporte.fecha_actualizacion.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).all()
        data = []
        for t, nombre, email in filas:
            n = (
                await self.db.execute(
                    select(func.count()).select_from(TicketMensaje).where(TicketMensaje.ticket_id == t.id)
                )
            ).scalar_one()
            data.append(
                AdminTicketOut(
                    id=t.id, numero=t.numero, categoria=t.categoria, asunto=t.asunto,
                    descripcion=t.descripcion, estado=t.estado, usuario_id=t.usuario_id,
                    usuario_nombre=nombre, usuario_email=email, fecha_creacion=t.fecha_creacion,
                    fecha_actualizacion=t.fecha_actualizacion, total_mensajes=n,
                )
            )
        return _pagina(data, total, page, per_page)

    async def detalle_ticket(self, ticket_id: uuid.UUID) -> AdminTicketDetalle:
        t = await self.db.get(TicketSoporte, ticket_id)
        if t is None:
            raise NotFoundError("Ticket no encontrado.")
        u = await self.db.get(Usuario, t.usuario_id)
        mensajes = (
            await self.db.execute(
                select(TicketMensaje)
                .where(TicketMensaje.ticket_id == t.id)
                .order_by(TicketMensaje.fecha_creacion)
            )
        ).scalars().all()
        return AdminTicketDetalle(
            id=t.id, numero=t.numero, categoria=t.categoria, asunto=t.asunto,
            descripcion=t.descripcion, estado=t.estado, usuario_id=t.usuario_id,
            usuario_nombre=u.nombre if u else "—", usuario_email=u.email if u else "—",
            fecha_creacion=t.fecha_creacion, fecha_actualizacion=t.fecha_actualizacion,
            total_mensajes=len(mensajes),
            mensajes=[TicketMensajeOut.model_validate(m) for m in mensajes],
        )

    async def responder_ticket(
        self, admin: Usuario, ticket_id: uuid.UUID, mensaje: str, estado: str | None
    ) -> AdminTicketDetalle:
        t = await self.db.get(TicketSoporte, ticket_id)
        if t is None:
            raise NotFoundError("Ticket no encontrado.")
        anterior = t.estado
        self.db.add(
            TicketMensaje(ticket_id=t.id, autor_id=admin.id, es_admin=True, mensaje=mensaje)
        )
        t.estado = estado or ESTADO_EN_REVISION
        t.fecha_actualizacion = _now()
        await self.db.flush()
        await self.notif.notificar(
            t.usuario_id, TIPO_RESPUESTA_SOPORTE,
            f"El equipo de soporte respondió tu solicitud #{t.numero}.", "ticket", t.id,
        )
        await self.audit.registrar(
            admin.id, "SOPORTE_RESPONDIDO", objeto_tipo="ticket", objeto_id=t.id,
            descripcion=f"#{t.numero} {t.asunto}", anterior={"estado": anterior},
            nuevo={"estado": t.estado},
        )
        await self.db.commit()
        return await self.detalle_ticket(ticket_id)

    # ─────────────── Solicitudes de cuenta / privacidad ───────────────

    async def listar_solicitudes(
        self, page: int, per_page: int, estado: str | None, tipo: str | None
    ) -> PaginatedAdmin[AdminSolicitudOut]:
        cond = []
        if estado:
            cond.append(SolicitudCuenta.estado == estado)
        if tipo:
            cond.append(SolicitudCuenta.tipo == tipo)
        total = (
            await self.db.execute(select(func.count()).select_from(SolicitudCuenta).where(*cond))
        ).scalar_one()
        filas = (
            await self.db.execute(
                select(SolicitudCuenta, Usuario.nombre, Usuario.email, Usuario.rol)
                .join(Usuario, Usuario.id == SolicitudCuenta.usuario_id)
                .where(*cond)
                .order_by(SolicitudCuenta.fecha_creacion.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).all()
        data = [
            AdminSolicitudOut(
                id=s.id, tipo=s.tipo, motivo=s.motivo, estado=s.estado,
                respuesta_admin=s.respuesta_admin, usuario_id=s.usuario_id,
                usuario_nombre=n, usuario_email=e, usuario_rol=r,
                fecha_creacion=s.fecha_creacion, fecha_atencion=s.fecha_atencion,
            )
            for s, n, e, r in filas
        ]
        return _pagina(data, total, page, per_page)

    async def resolver_solicitud(
        self, admin: Usuario, solicitud_id: uuid.UUID, data: AdminResolverSolicitud
    ) -> AdminSolicitudOut:
        sol = await self.db.get(SolicitudCuenta, solicitud_id)
        if sol is None:
            raise NotFoundError("Solicitud no encontrada.")
        if sol.usuario_id == admin.id:
            raise ForbiddenError("No puedes resolver solicitudes sobre tu propia cuenta.")
        if sol.estado in (SOL_ESTADO_COMPLETADA, SOL_ESTADO_RECHAZADA):
            raise ConflictError("Esta solicitud ya fue resuelta.")
        respuesta = (data.respuesta or "").strip()
        if data.decision in ("APROBAR", "RECHAZAR") and not respuesta:
            raise AppError("Escribe una respuesta para el solicitante (queda auditada).", 422)
        if data.ejecutar and data.decision != "APROBAR":
            raise AppError("Solo se puede ejecutar una solicitud aprobada.", 422)

        usuario = await self.db.get(Usuario, sol.usuario_id)
        anterior = sol.estado
        ejecutada = False
        if data.decision == "EN_PROCESO":
            sol.estado = SOL_ESTADO_EN_PROCESO
        elif data.decision == "RECHAZAR":
            sol.estado = SOL_ESTADO_RECHAZADA
        else:
            sol.estado = SOL_ESTADO_APROBADA
            if data.ejecutar:
                if sol.tipo not in _EJECUTABLES:
                    raise ConflictError("Este tipo de solicitud no se ejecuta automáticamente.")
                if usuario is None or usuario.rol == ROL_ADMIN:
                    raise ForbiddenError("No se ejecutan acciones sobre cuentas de administrador.")
                await self._ejecutar(admin, sol, usuario, respuesta)
                sol.estado = SOL_ESTADO_COMPLETADA
                ejecutada = True
        sol.respuesta_admin = respuesta or None
        sol.atendida_por = admin.id
        sol.fecha_atencion = _now()
        await self.audit.registrar(
            admin.id, "SOLICITUD_CUENTA_RESUELTA", objeto_tipo="solicitud_cuenta",
            objeto_id=sol.id, descripcion=f"{sol.tipo} de {usuario.email if usuario else '—'}",
            anterior={"estado": anterior}, nuevo={"estado": sol.estado, "ejecutada": ejecutada},
            motivo=respuesta or None,
        )
        # No se notifica una cuenta ya anonimizada o bloqueada: no podría leerlo.
        if usuario is not None and not ejecutada:
            await self.notif.notificar(
                usuario.id, TIPO_CUENTA_ACTUALIZADA,
                f"Tu solicitud ({sol.tipo.replace('_', ' ').lower()}) fue actualizada: "
                f"{sol.estado.replace('_', ' ').lower()}.",
                "solicitud_cuenta", sol.id,
            )
        await self.db.commit()
        return AdminSolicitudOut(
            id=sol.id, tipo=sol.tipo, motivo=sol.motivo, estado=sol.estado,
            respuesta_admin=sol.respuesta_admin, usuario_id=sol.usuario_id,
            usuario_nombre=usuario.nombre if usuario else "—",
            usuario_email=usuario.email if usuario else "—",
            usuario_rol=usuario.rol if usuario else "—",
            fecha_creacion=sol.fecha_creacion, fecha_atencion=sol.fecha_atencion,
        )

    async def _ejecutar(
        self, admin: Usuario, sol: SolicitudCuenta, usuario: Usuario, motivo: str
    ) -> None:
        if sol.tipo in _ELIMINACIONES:
            antes = {"estado": usuario.estado, "email": usuario.email}
            await self._anonimizar(usuario)
            await self.audit.registrar(
                admin.id, "USUARIO_ANONIMIZADO", objeto_tipo="usuario", objeto_id=usuario.id,
                descripcion=f"Anonimización por {sol.tipo}", anterior=antes,
                nuevo={"estado": usuario.estado}, motivo=motivo,
            )
            return
        nuevo = ESTADO_SUSPENDIDO if sol.tipo == SOL_BLOQUEO_TEMPORAL else ESTADO_BLOQUEADO
        self.db.add(
            HistorialEstadoVoluntario(
                usuario_id=usuario.id, estado_anterior=usuario.estado, estado_nuevo=nuevo,
                motivo=f"Solicitud del titular ({sol.tipo}). {motivo}",
                admin_id=await self.audit.perfil_admin_id(admin.id),
            )
        )
        usuario.estado = nuevo
        usuario.fecha_actualizacion = _now()
        await TokenService(self.db, get_settings()).revocar_refresh_tokens(usuario.id)

    async def _anonimizar(self, usuario: Usuario) -> None:
        """Reemplaza los datos personales y conserva los registros con valor legal."""
        sufijo = usuario.id.hex[:16]
        usuario.nombre = "Usuario anonimizado"
        usuario.email = f"anonimo-{usuario.id}@anonimizado.invalid"
        usuario.telefono = None
        usuario.provider_id = None
        usuario.password_hash = hash_password(secrets.token_urlsafe(32))  # cuenta inutilizable
        usuario.provider = "LOCAL"
        usuario.estado = ESTADO_BLOQUEADO
        usuario.email_verificado = False
        usuario.fecha_actualizacion = _now()
        repo = UsuarioRepository(self.db)

        if usuario.rol == ROL_VOLUNTARIO:
            vol = await repo.voluntario_por_usuario(usuario.id)
            if vol is not None:
                self.storage.eliminar_privado(vol.documento_identidad)
                vol.numero_documento = f"ANON-{sufijo}"
                vol.documento_identidad = None
                vol.foto_perfil = None
                vol.esta_verificado = False
                for campo in (
                    "experiencia", "direccion", "descripcion", "telefono_contacto",
                    "nivel_educativo", "profesion", "idiomas",
                    "contacto_emergencia_nombre", "contacto_emergencia_telefono",
                ):
                    setattr(vol, campo, None)
                await self.db.execute(
                    update(Ofrecimiento)
                    .where(Ofrecimiento.voluntario_id == vol.id, Ofrecimiento.estado == OF_DISPONIBLE)
                    .values(estado=OF_FINALIZADO)
                )
        elif usuario.rol == ROL_FUNDACION:
            fund = await repo.fundacion_por_usuario(usuario.id)
            if fund is not None:
                for doc in (
                    await self.db.execute(
                        select(FundacionDocumento).where(FundacionDocumento.fundacion_id == fund.id)
                    )
                ).scalars().all():
                    self.storage.eliminar_privado(doc.ruta_archivo)
                await self.db.execute(
                    delete(FundacionDocumento).where(FundacionDocumento.fundacion_id == fund.id)
                )
                fund.estado_verificacion = ESTADO_SUSPENDIDA  # antes de vaciar el correo
                fund.nombre = "Organización anonimizada"
                fund.nit = None
                fund.representante_legal = "Anonimizado"
                fund.correo_institucional = None
                fund.telefono = "0000000"
                fund.direccion = "Anonimizada"
                fund.descripcion = "Información eliminada por solicitud del titular."
                fund.documento_legal = None
                fund.pagina_web = None
                fund.logo = None
                fund.historia = None
                fund.mision = None
                fund.mostrar_telefono = fund.mostrar_correo = fund.mostrar_direccion = False
                await self.db.execute(
                    update(Publicacion)
                    .where(Publicacion.fundacion_id == fund.id)
                    .values(oculta_por_admin=True, motivo_ocultamiento="Titular anonimizado")
                )

        pref = await self.db.get(PreferenciasNotificacion, usuario.id)
        if pref is not None:
            await self.db.delete(pref)
        await TokenService(self.db, get_settings()).revocar_refresh_tokens(usuario.id)

    # ─────────────── Verificación documental ───────────────

    async def listar_verificaciones(
        self, page: int, per_page: int, estado: str | None
    ) -> PaginatedAdmin[AdminVerificacionOut]:
        cond = [Fundacion.verificacion_documental != "NO_SOLICITADA"]
        if estado:
            cond.append(Fundacion.verificacion_documental == estado)
        total = (
            await self.db.execute(select(func.count()).select_from(Fundacion).where(*cond))
        ).scalar_one()
        fundaciones = (
            await self.db.execute(
                select(Fundacion)
                .where(*cond)
                .order_by(Fundacion.verificacion_documental_fecha.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).scalars().all()
        data = []
        for f in fundaciones:
            docs = (
                await self.db.execute(
                    select(FundacionDocumento).where(FundacionDocumento.fundacion_id == f.id)
                )
            ).scalars().all()
            data.append(
                AdminVerificacionOut(
                    fundacion_id=f.id, nombre=f.nombre, nit=f.nit,
                    tipo_organizacion=f.tipo_organizacion,
                    constituida_legalmente=f.constituida_legalmente,
                    estado=f.verificacion_documental, nota=f.verificacion_documental_nota,
                    fecha=f.verificacion_documental_fecha,
                    documentos=[DocumentoVerifOut.model_validate(d) for d in docs],
                )
            )
        return _pagina(data, total, page, per_page)

    async def resolver_verificacion(
        self, admin: Usuario, fundacion_id: uuid.UUID, accion: str, nota: str | None
    ) -> AdminVerificacionOut:
        servicio = OrganizacionService(self.db)
        anterior = (await self.db.get(Fundacion, fundacion_id))
        estado_previo = anterior.verificacion_documental if anterior else None
        f = await servicio.resolver_verificacion(admin, fundacion_id, accion, nota)
        await self.audit.registrar(
            admin.id, "VERIFICACION_DOCUMENTAL_RESUELTA", objeto_tipo="fundacion",
            objeto_id=f.id, descripcion=f.nombre, anterior={"estado": estado_previo},
            nuevo={"estado": f.verificacion_documental}, motivo=nota,
        )
        await self.db.commit()
        docs = (
            await self.db.execute(
                select(FundacionDocumento).where(FundacionDocumento.fundacion_id == f.id)
            )
        ).scalars().all()
        return AdminVerificacionOut(
            fundacion_id=f.id, nombre=f.nombre, nit=f.nit, tipo_organizacion=f.tipo_organizacion,
            constituida_legalmente=f.constituida_legalmente, estado=f.verificacion_documental,
            nota=f.verificacion_documental_nota, fecha=f.verificacion_documental_fecha,
            documentos=[DocumentoVerifOut.model_validate(d) for d in docs],
        )

    # ─────────────── Moderación de reseñas ───────────────

    async def listar_resenas(
        self, page: int, per_page: int, estado: str | None
    ) -> PaginatedAdmin[AdminResenaOut]:
        cond = [ResenaOrganizacion.estado == (estado or RESENA_PENDIENTE)]
        total = (
            await self.db.execute(select(func.count()).select_from(ResenaOrganizacion).where(*cond))
        ).scalar_one()
        filas = (
            await self.db.execute(
                select(ResenaOrganizacion, Fundacion.nombre, Usuario.nombre)
                .join(Fundacion, Fundacion.id == ResenaOrganizacion.fundacion_id)
                .join(Voluntario, Voluntario.id == ResenaOrganizacion.voluntario_id)
                .join(Usuario, Usuario.id == Voluntario.usuario_id)
                .where(*cond)
                .order_by(ResenaOrganizacion.fecha_creacion.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).all()
        data = [
            AdminResenaOut(
                id=r.id, fundacion_id=r.fundacion_id, fundacion_nombre=fn,
                voluntario_nombre=vn.split(" ")[0], calificacion=r.calificacion,
                comentario=r.comentario, estado=r.estado,
                motivo_moderacion=r.motivo_moderacion, fecha_creacion=r.fecha_creacion,
            )
            for r, fn, vn in filas
        ]
        return _pagina(data, total, page, per_page)

    async def moderar_resena(
        self, admin: Usuario, resena_id: uuid.UUID, accion: str, motivo: str | None
    ) -> None:
        servicio = OrganizacionService(self.db)
        previa = await self.db.get(ResenaOrganizacion, resena_id)
        estado_previo = previa.estado if previa else None
        r = await servicio.moderar_resena(resena_id, accion, motivo)
        await self.audit.registrar(
            admin.id, "RESENA_MODERADA", objeto_tipo="resena", objeto_id=r.id,
            descripcion=r.comentario[:80], anterior={"estado": estado_previo},
            nuevo={"estado": r.estado}, motivo=motivo,
        )
        await self.db.commit()

    # ─────────────── Auditoría ───────────────

    async def listar_auditoria(
        self, page: int, per_page: int, tipo: str | None
    ) -> PaginatedAdmin[AuditoriaOut]:
        filas, total = await self.audit.listar(page, per_page, tipo)
        data = [
            AuditoriaOut(
                id=a.id, admin_nombre=nombre, tipo=a.tipo, objeto_tipo=a.objeto_tipo,
                objeto_id=a.objeto_id, objeto_descripcion=a.objeto_descripcion,
                detalle_anterior=a.detalle_anterior, detalle_nuevo=a.detalle_nuevo,
                motivo=a.motivo, fecha_accion=a.fecha_accion,
            )
            for a, nombre in filas
        ]
        return _pagina(data, total, page, per_page)

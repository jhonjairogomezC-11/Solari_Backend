"""Servicio del panel de administración."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.services.notificacion_service import NotificacionService
from app.models.fundacion import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADA,
    ESTADO_SUSPENDIDA,
)
from app.models.usuario import (
    ESTADO_ACTIVO,
    ESTADO_BLOQUEADO,
    ESTADO_SUSPENDIDO,
    ROL_ADMIN,
    ROL_FUNDACION,
    ROL_VOLUNTARIO,
)
from app.models.admin_accion import HistorialEstadoVoluntario
from app.repositories.admin_repo import AdminRepository
from app.schemas.admin import (
    AdminConvocatoriaOut,
    AdminFundacionOut,
    AdminPostulacionOut,
    AdminUsuarioOut,
    AdminVoluntarioOut,
    ConteoPorEstado,
    DashboardStats,
    SerieTemporalPunto,
)
from app.services.auditoria_service import AuditoriaService
from app.services.notificacion_service import NotificacionService

_ACCION_POR_ESTADO_USUARIO = {
    ESTADO_SUSPENDIDO: "USUARIO_SUSPENDIDO",
    ESTADO_BLOQUEADO: "USUARIO_BLOQUEADO",
    ESTADO_ACTIVO: "USUARIO_REACTIVADO",
}
_ACCION_POR_ESTADO_FUNDACION = {
    ESTADO_APROBADA: "FUNDACION_APROBADA",
    ESTADO_RECHAZADA: "FUNDACION_RECHAZADA",
    ESTADO_SUSPENDIDA: "FUNDACION_SUSPENDIDA",
    ESTADO_PENDIENTE: "FUNDACION_REACTIVADA",
}

_ESTADOS_USUARIO = {ESTADO_ACTIVO, ESTADO_BLOQUEADO, ESTADO_SUSPENDIDO}
_ROLES = {ROL_VOLUNTARIO, ROL_FUNDACION, ROL_ADMIN}
_ESTADOS_VERIF = {ESTADO_PENDIENTE, ESTADO_APROBADA, ESTADO_RECHAZADA, ESTADO_SUSPENDIDA}


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AdminRepository(db)
        self.notif = NotificacionService(db)
        self.audit = AuditoriaService(db)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    async def dashboard(self) -> DashboardStats:
        por_rol = await self.repo.contar_usuarios_por_rol()
        por_estado = await self.repo.contar_usuarios_por_estado()
        por_verif = await self.repo.contar_fundaciones_por_verificacion()
        conv_estado = await self.repo.contar_convocatorias_por_estado()
        post_estado = await self.repo.contar_postulaciones_por_estado()
        ocultas = await self.repo.contar_convocatorias_ocultas()
        nuevos = await self.repo.nuevos_usuarios_desde(datetime.utcnow() - timedelta(days=30))
        series = await self.repo.registros_por_dia(30)

        return DashboardStats(
            total_usuarios=sum(por_rol.values()),
            total_voluntarios=por_rol.get(ROL_VOLUNTARIO, 0),
            total_fundaciones=por_rol.get(ROL_FUNDACION, 0),
            total_admins=por_rol.get(ROL_ADMIN, 0),
            usuarios_activos=por_estado.get(ESTADO_ACTIVO, 0),
            usuarios_bloqueados=por_estado.get(ESTADO_BLOQUEADO, 0),
            usuarios_suspendidos=por_estado.get(ESTADO_SUSPENDIDO, 0),
            nuevos_usuarios_30d=nuevos,
            fundaciones_pendientes=por_verif.get(ESTADO_PENDIENTE, 0),
            fundaciones_aprobadas=por_verif.get(ESTADO_APROBADA, 0),
            fundaciones_rechazadas=por_verif.get(ESTADO_RECHAZADA, 0),
            total_convocatorias=sum(conv_estado.values()),
            convocatorias_publicadas=conv_estado.get("PUBLICADA", 0),
            convocatorias_borrador=conv_estado.get("BORRADOR", 0),
            convocatorias_ocultas=ocultas,
            total_postulaciones=sum(post_estado.values()),
            postulaciones_pendientes=post_estado.get("PENDIENTE", 0),
            postulaciones_aceptadas=post_estado.get("ACEPTADO", 0),
            registros_por_dia=[
                SerieTemporalPunto(fecha=f, total=t) for f, t in series
            ],
            convocatorias_por_estado=[
                ConteoPorEstado(estado=e, total=t) for e, t in conv_estado.items()
            ],
            postulaciones_por_estado=[
                ConteoPorEstado(estado=e, total=t) for e, t in post_estado.items()
            ],
        )

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------
    async def listar_usuarios(self, page, per_page, rol, estado, buscar):
        usuarios, total = await self.repo.listar_usuarios(page, per_page, rol, estado, buscar)
        salida = []
        for u in usuarios:
            tiene, pid, estado_verif = await self.repo.perfil_de_usuario(u)
            dto = AdminUsuarioOut.model_validate(u)
            dto.tiene_perfil = tiene
            dto.perfil_id = pid
            dto.estado_verificacion_fundacion = estado_verif
            salida.append(dto)
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {"data": salida, "total": total, "page": page, "per_page": per_page, "pages": pages}

    async def cambiar_estado_usuario(
        self, admin_id: uuid.UUID, usuario_id: str, estado: str, motivo: str | None
    ):
        if estado not in _ESTADOS_USUARIO:
            raise ConflictError(f"Estado inválido. Debe ser uno de {sorted(_ESTADOS_USUARIO)}.")
        usuario = await self.repo.usuario_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        if str(usuario.id) == str(admin_id):
            raise ForbiddenError("No puedes cambiar el estado de tu propia cuenta.")
        if usuario.rol == ROL_ADMIN:
            raise ForbiddenError("No se puede modificar el estado de otro administrador.")

        anterior = usuario.estado
        usuario.estado = estado
        usuario.fecha_actualizacion = datetime.utcnow()
        # Un usuario bloqueado/suspendido no podría iniciar sesión para ver una
        # notificación; el motivo queda en el historial y en la auditoría.
        self.db.add(
            HistorialEstadoVoluntario(
                usuario_id=usuario.id, estado_anterior=anterior, estado_nuevo=estado,
                motivo=motivo, admin_id=await self.audit.perfil_admin_id(admin_id),
            )
        )
        await self.audit.registrar(
            admin_id, _ACCION_POR_ESTADO_USUARIO[estado], objeto_tipo="usuario",
            objeto_id=usuario.id, descripcion=usuario.email,
            anterior={"estado": anterior}, nuevo={"estado": estado}, motivo=motivo,
        )
        await self.db.commit()
        await self.db.refresh(usuario)
        tiene, pid, verif = await self.repo.perfil_de_usuario(usuario)
        dto = AdminUsuarioOut.model_validate(usuario)
        dto.tiene_perfil, dto.perfil_id, dto.estado_verificacion_fundacion = tiene, pid, verif
        return dto

    async def cambiar_rol_usuario(self, admin_id: uuid.UUID, usuario_id: str, rol: str):
        if rol not in _ROLES:
            raise ConflictError(f"Rol inválido. Debe ser uno de {sorted(_ROLES)}.")
        usuario = await self.repo.usuario_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        if str(usuario.id) == str(admin_id):
            raise ForbiddenError("No puedes cambiar tu propio rol.")

        rol_anterior = usuario.rol
        usuario.rol = rol
        usuario.fecha_actualizacion = datetime.utcnow()
        await self.audit.registrar(
            admin_id, "USUARIO_EDITADO", objeto_tipo="usuario", objeto_id=usuario.id,
            descripcion=usuario.email, anterior={"rol": rol_anterior}, nuevo={"rol": rol},
        )
        await self.db.commit()
        await self.db.refresh(usuario)
        tiene, pid, verif = await self.repo.perfil_de_usuario(usuario)
        dto = AdminUsuarioOut.model_validate(usuario)
        dto.tiene_perfil, dto.perfil_id, dto.estado_verificacion_fundacion = tiene, pid, verif
        return dto

    # ------------------------------------------------------------------
    # Fundaciones
    # ------------------------------------------------------------------
    async def listar_fundaciones(self, page, per_page, estado_verificacion, buscar):
        fundaciones, total = await self.repo.listar_fundaciones(
            page, per_page, estado_verificacion, buscar
        )
        data = [AdminFundacionOut.model_validate(f) for f in fundaciones]
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {"data": data, "total": total, "page": page, "per_page": per_page, "pages": pages}

    async def obtener_fundacion(self, fundacion_id: str):
        f = await self.repo.fundacion_por_id(fundacion_id)
        if f is None:
            raise NotFoundError("Fundación no encontrada.")
        return AdminFundacionOut.model_validate(f)

    async def verificar_fundacion(
        self, admin_id: uuid.UUID, fundacion_id: str, estado: str, motivo: str | None
    ):
        if estado not in _ESTADOS_VERIF:
            raise ConflictError(f"Estado inválido. Debe ser uno de {sorted(_ESTADOS_VERIF)}.")
        f = await self.repo.fundacion_por_id(fundacion_id)
        if f is None:
            raise NotFoundError("Fundación no encontrada.")
        if estado in (ESTADO_RECHAZADA, ESTADO_SUSPENDIDA) and not motivo:
            raise ConflictError("Debes indicar un motivo para rechazar o suspender.")

        estado_anterior = f.estado_verificacion
        await self.audit.registrar(
            admin_id, _ACCION_POR_ESTADO_FUNDACION[estado], objeto_tipo="fundacion",
            objeto_id=f.id, descripcion=f.nombre, anterior={"estado": estado_anterior},
            nuevo={"estado": estado}, motivo=motivo,
        )
        f.estado_verificacion = estado
        f.fecha_verificacion = datetime.utcnow()
        f.motivo_rechazo = motivo if estado in (ESTADO_RECHAZADA, ESTADO_SUSPENDIDA) else None
        f.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()

        notif_por_estado = {
            ESTADO_APROBADA: (
                "FUNDACION_APROBADA",
                "¡Tu fundación ha sido aprobada! Ya puedes publicar convocatorias.",
            ),
            ESTADO_RECHAZADA: (
                "FUNDACION_RECHAZADA",
                f"Tu solicitud de verificación fue rechazada. Motivo: {motivo}",
            ),
            ESTADO_SUSPENDIDA: (
                "FUNDACION_SUSPENDIDA",
                f"Tu fundación ha sido suspendida. Motivo: {motivo}",
            ),
            ESTADO_PENDIENTE: (
                "FUNDACION_REACTIVADA",
                "Tu verificación ha vuelto a estado pendiente.",
            ),
        }
        tipo_notif, mensaje = notif_por_estado[estado]
        await self.notif.notificar(f.usuario_id, tipo_notif, mensaje)

        await self.db.commit()
        await self.db.refresh(f)
        return AdminFundacionOut.model_validate(f)

    # ------------------------------------------------------------------
    # Convocatorias
    # ------------------------------------------------------------------
    async def listar_convocatorias(self, page, per_page, estado, oculta, buscar):
        rows, total = await self.repo.listar_convocatorias(
            page, per_page, estado, oculta, buscar
        )
        data = []
        for pub, fund_nombre, total_post in rows:
            dto = AdminConvocatoriaOut.model_validate(pub)
            dto.fundacion_nombre = fund_nombre
            dto.total_postulaciones = total_post or 0
            data.append(dto)
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {"data": data, "total": total, "page": page, "per_page": per_page, "pages": pages}

    async def ocultar_convocatoria(
        self, admin_id: uuid.UUID, pub_id: str, ocultar: bool, motivo: str | None
    ):
        pub = await self.repo.convocatoria_por_id(pub_id)
        if pub is None:
            raise NotFoundError("Convocatoria no encontrada.")
        if ocultar and not motivo:
            raise ConflictError("Debes indicar un motivo para ocultar la convocatoria.")
        await self.audit.registrar(
            admin_id, "PUBLICACION_OCULTADA" if ocultar else "PUBLICACION_RESTAURADA",
            objeto_tipo="publicacion", objeto_id=pub.id, descripcion=pub.titulo,
            anterior={"oculta": pub.oculta_por_admin}, nuevo={"oculta": ocultar},
            motivo=motivo,
        )

        pub.oculta_por_admin = ocultar
        pub.motivo_ocultamiento = motivo if ocultar else None
        pub.fecha_ocultamiento = datetime.utcnow() if ocultar else None
        pub.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()

        fund = await self.repo.fundacion_por_id(pub.fundacion_id)
        if fund:
            if ocultar:
                msg = (
                    f"Tu convocatoria '{pub.titulo}' fue ocultada por un "
                    f"administrador. Motivo: {motivo}"
                )
            else:
                msg = f"Tu convocatoria '{pub.titulo}' vuelve a ser visible."
            await self.notif.notificar(
                fund.usuario_id, "ACTIVIDAD_MODIFICADA", msg, "PUBLICACION", pub.id
            )

        await self.db.commit()
        await self.db.refresh(pub)
        dto = AdminConvocatoriaOut.model_validate(pub)
        dto.fundacion_nombre = fund.nombre if fund else None
        return dto

    # ------------------------------------------------------------------
    # Postulaciones
    # ------------------------------------------------------------------
    async def listar_postulaciones(self, page, per_page, estado):
        rows, total = await self.repo.listar_postulaciones(page, per_page, estado)
        data = []
        for post, pub_titulo, vol_nombre in rows:
            dto = AdminPostulacionOut.model_validate(post)
            dto.publicacion_titulo = pub_titulo
            dto.voluntario_nombre = vol_nombre
            data.append(dto)
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {"data": data, "total": total, "page": page, "per_page": per_page, "pages": pages}

    # ------------------------------------------------------------------
    # Voluntarios (verificación de identidad)
    # ------------------------------------------------------------------
    async def listar_voluntarios(self, page, per_page, verificado, con_documento, buscar):
        rows, total = await self.repo.listar_voluntarios(
            page, per_page, verificado, con_documento, buscar
        )
        data = []
        for vol, nombre, email, telefono in rows:
            dto = AdminVoluntarioOut.model_validate(vol)
            dto.nombre = nombre
            dto.email = email
            dto.telefono = telefono
            data.append(dto)
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {"data": data, "total": total, "page": page, "per_page": per_page, "pages": pages}

    async def verificar_voluntario(
        self, admin_id: uuid.UUID, voluntario_id: str, verificado: bool
    ):
        vol = await self.repo.voluntario_por_id(voluntario_id)
        if vol is None:
            raise NotFoundError("Voluntario no encontrado.")
        if verificado and not vol.documento_identidad:
            raise ConflictError("El voluntario no ha subido un documento de identidad.")
        await self.audit.registrar(
            admin_id, "VOLUNTARIO_VERIFICADO", objeto_tipo="voluntario", objeto_id=vol.id,
            anterior={"verificado": vol.esta_verificado}, nuevo={"verificado": verificado},
        )
        vol.esta_verificado = verificado
        vol.motivo_rechazo_documento = None  # limpiar rechazo previo si se aprueba
        await NotificacionService(self.db).notificar(
            vol.usuario_id,
            "VERIFICACION_ACTUALIZADA",
            "✅ Tu identidad ha sido verificada. Ya tienes la insignia de voluntario verificado.",
            objeto_tipo="voluntario",
            objeto_id=vol.id,
        )
        await self.db.commit()
        await self.db.refresh(vol)
        dto = AdminVoluntarioOut.model_validate(vol)
        return dto

    async def rechazar_documento_voluntario(
        self, admin_id: uuid.UUID, voluntario_id: str, motivo: str
    ):
        vol = await self.repo.voluntario_por_id(voluntario_id)
        if vol is None:
            raise NotFoundError("Voluntario no encontrado.")
        await self.audit.registrar(
            admin_id, "VOLUNTARIO_VERIFICADO", objeto_tipo="voluntario", objeto_id=vol.id,
            anterior={"verificado": vol.esta_verificado, "motivo": None},
            nuevo={"verificado": False, "motivo": motivo},
        )
        vol.esta_verificado = False
        vol.motivo_rechazo_documento = motivo
        await NotificacionService(self.db).notificar(
            vol.usuario_id,
            "VERIFICACION_ACTUALIZADA",
            f"❌ Tu documento de identidad fue rechazado. Motivo: {motivo}. Por favor sube un nuevo documento desde tu perfil.",
            objeto_tipo="voluntario",
            objeto_id=vol.id,
        )
        await self.db.commit()
        await self.db.refresh(vol)
        dto = AdminVoluntarioOut.model_validate(vol)
        return dto

    # ------------------------------------------------------------------
    # Catálogos
    # ------------------------------------------------------------------
    async def _auditar_catalogo(self, admin_id: uuid.UUID, tipo: str, nombre: str) -> None:
        await self.audit.registrar(
            admin_id, "CATALOGO_MODIFICADO", objeto_tipo=tipo, descripcion=nombre,
            nuevo={"nombre": nombre, "accion": "crear"},
        )

    async def crear_area(self, admin_id: uuid.UUID, nombre: str):
        area = await self.repo.crear_area(nombre)
        await self._auditar_catalogo(admin_id, "area_impacto", nombre)
        await self.db.commit()
        await self.db.refresh(area)
        return area

    async def crear_habilidad(
        self, admin_id: uuid.UUID, nombre: str,
        categoria: str | None = None, es_profesional: bool = False,
    ):
        hab = await self.repo.crear_habilidad(nombre)
        hab.categoria = categoria
        hab.es_profesional = es_profesional
        await self._auditar_catalogo(admin_id, "habilidad", nombre)
        await self.db.commit()
        await self.db.refresh(hab)
        return hab

    async def crear_departamento(self, admin_id: uuid.UUID, nombre: str):
        dep = await self.repo.crear_departamento(nombre)
        await self._auditar_catalogo(admin_id, "departamento", nombre)
        await self.db.commit()
        await self.db.refresh(dep)
        return dep

    async def crear_municipio(self, admin_id: uuid.UUID, nombre: str, departamento_id: int):
        mun = await self.repo.crear_municipio(nombre, departamento_id)
        await self._auditar_catalogo(admin_id, "municipio", nombre)
        await self.db.commit()
        await self.db.refresh(mun)
        return mun

"""Registro de auditoría de acciones administrativas (`admin_acciones`)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.models.admin_accion import AdminAccion, AdminPerfil
from app.models.usuario import Usuario


def _json_seguro(valor: Any) -> Any:
    """Convierte valores (UUID, fechas) a tipos serializables en JSONB."""
    if valor is None:
        return None
    if isinstance(valor, dict):
        return {k: _json_seguro(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [_json_seguro(v) for v in valor]
    if isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


class AuditoriaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def perfil_admin_id(self, usuario_id: uuid.UUID) -> uuid.UUID:
        """Id del perfil de administrador (lo que referencia la auditoría)."""
        perfil_id = (
            await self.db.execute(
                select(AdminPerfil.id).where(
                    AdminPerfil.usuario_id == usuario_id, AdminPerfil.activo.is_(True)
                )
            )
        ).scalar_one_or_none()
        if perfil_id is None:
            raise ForbiddenError("Tu cuenta no tiene un perfil de administración activo.")
        return perfil_id

    async def registrar(
        self,
        admin_id: uuid.UUID,
        tipo: str,
        *,
        objeto_tipo: str | None = None,
        objeto_id: uuid.UUID | str | None = None,
        descripcion: str | None = None,
        anterior: dict | None = None,
        nuevo: dict | None = None,
        motivo: str | None = None,
    ) -> AdminAccion:
        """Añade el registro a la sesión actual (se confirma con el commit del llamador)."""
        accion = AdminAccion(
            admin_id=await self.perfil_admin_id(admin_id),
            tipo=tipo,
            objeto_tipo=objeto_tipo,
            objeto_id=uuid.UUID(str(objeto_id)) if objeto_id else None,
            objeto_descripcion=descripcion,
            detalle_anterior=_json_seguro(anterior),
            detalle_nuevo=_json_seguro(nuevo),
            motivo=motivo,
        )
        self.db.add(accion)
        await self.db.flush()
        return accion

    async def listar(
        self, page: int, per_page: int, tipo: str | None = None
    ) -> tuple[list[tuple], int]:
        condiciones = []
        if tipo:
            condiciones.append(AdminAccion.tipo == tipo)
        total = (
            await self.db.execute(
                select(func.count()).select_from(AdminAccion).where(*condiciones)
            )
        ).scalar_one()
        stmt = (
            select(AdminAccion, Usuario.nombre)
            .join(AdminPerfil, AdminPerfil.id == AdminAccion.admin_id)
            .join(Usuario, Usuario.id == AdminPerfil.usuario_id)
            .where(*condiciones)
            .order_by(AdminAccion.fecha_accion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = (await self.db.execute(stmt)).all()
        return filas, total

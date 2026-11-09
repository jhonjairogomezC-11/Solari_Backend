"""Acceso a datos del panel de administración. Todo vía ORM parametrizado."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import AreaImpacto, Departamento, Habilidad, Municipio
from app.models.fundacion import Fundacion
from app.models.postulacion import Postulacion
from app.models.publicacion import Publicacion
from app.models.usuario import ROL_FUNDACION, ROL_VOLUNTARIO, Usuario
from app.models.voluntario import Voluntario


class AdminRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Estadísticas / dashboard
    # ------------------------------------------------------------------
    async def _count(self, stmt) -> int:
        return (await self.db.execute(stmt)).scalar_one() or 0

    async def contar_usuarios_por_rol(self) -> dict[str, int]:
        stmt = select(Usuario.rol, func.count()).group_by(Usuario.rol)
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def contar_usuarios_por_estado(self) -> dict[str, int]:
        stmt = select(Usuario.estado, func.count()).group_by(Usuario.estado)
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def nuevos_usuarios_desde(self, desde: datetime) -> int:
        return await self._count(
            select(func.count()).select_from(Usuario).where(Usuario.fecha_registro >= desde)
        )

    async def contar_fundaciones_por_verificacion(self) -> dict[str, int]:
        stmt = select(Fundacion.estado_verificacion, func.count()).group_by(
            Fundacion.estado_verificacion
        )
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def contar_convocatorias_por_estado(self) -> dict[str, int]:
        stmt = select(Publicacion.estado, func.count()).group_by(Publicacion.estado)
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def contar_convocatorias_ocultas(self) -> int:
        return await self._count(
            select(func.count()).select_from(Publicacion).where(
                Publicacion.oculta_por_admin.is_(True)
            )
        )

    async def contar_postulaciones_por_estado(self) -> dict[str, int]:
        stmt = select(Postulacion.estado, func.count()).group_by(Postulacion.estado)
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

    async def registros_por_dia(self, dias: int = 30) -> list[tuple]:
        desde = datetime.utcnow() - timedelta(days=dias)
        fecha = func.date(Usuario.fecha_registro)
        stmt = (
            select(fecha.label("fecha"), func.count().label("total"))
            .where(Usuario.fecha_registro >= desde)
            .group_by(fecha)
            .order_by(fecha)
        )
        return (await self.db.execute(stmt)).all()

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------
    async def listar_usuarios(
        self,
        page: int,
        per_page: int,
        rol: str | None = None,
        estado: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[Usuario], int]:
        condiciones = []
        if rol:
            condiciones.append(Usuario.rol == rol)
        if estado:
            condiciones.append(Usuario.estado == estado)
        if buscar:
            patron = f"%{buscar.lower()}%"
            condiciones.append(
                func.lower(Usuario.nombre).like(patron)
                | func.lower(Usuario.email).like(patron)
            )

        count_stmt = select(func.count()).select_from(Usuario)
        data_stmt = select(Usuario).order_by(Usuario.fecha_registro.desc())
        for c in condiciones:
            count_stmt = count_stmt.where(c)
            data_stmt = data_stmt.where(c)

        total = await self._count(count_stmt)
        data_stmt = data_stmt.limit(per_page).offset((page - 1) * per_page)
        usuarios = list((await self.db.execute(data_stmt)).scalars().all())
        return usuarios, total

    async def perfil_de_usuario(
        self, usuario: Usuario
    ) -> tuple[bool, uuid.UUID | None, str | None]:
        """Devuelve (tiene_perfil, perfil_id, estado_verificacion_fundacion)."""
        if usuario.rol == ROL_VOLUNTARIO:
            stmt = select(Voluntario.id).where(Voluntario.usuario_id == usuario.id)
            pid = (await self.db.execute(stmt)).scalar_one_or_none()
            return (pid is not None, pid, None)
        if usuario.rol == ROL_FUNDACION:
            stmt = select(Fundacion.id, Fundacion.estado_verificacion).where(
                Fundacion.usuario_id == usuario.id
            )
            row = (await self.db.execute(stmt)).first()
            if row:
                return (True, row[0], row[1])
            return (False, None, None)
        return (True, None, None)

    async def usuario_por_id(self, usuario_id: str | uuid.UUID) -> Usuario | None:
        return await self.db.get(Usuario, usuario_id)

    # ------------------------------------------------------------------
    # Fundaciones
    # ------------------------------------------------------------------
    async def listar_fundaciones(
        self, page: int, per_page: int, estado_verificacion: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[Fundacion], int]:
        condiciones = []
        if estado_verificacion:
            condiciones.append(Fundacion.estado_verificacion == estado_verificacion)
        if buscar:
            patron = f"%{buscar.lower()}%"
            condiciones.append(
                func.lower(Fundacion.nombre).like(patron)
                | func.lower(Fundacion.nit).like(patron)
            )

        count_stmt = select(func.count()).select_from(Fundacion)
        data_stmt = select(Fundacion).order_by(Fundacion.fecha_creacion.desc())
        for c in condiciones:
            count_stmt = count_stmt.where(c)
            data_stmt = data_stmt.where(c)

        total = await self._count(count_stmt)
        data_stmt = data_stmt.limit(per_page).offset((page - 1) * per_page)
        fundaciones = list((await self.db.execute(data_stmt)).scalars().all())
        return fundaciones, total

    async def fundacion_por_id(self, fundacion_id: str | uuid.UUID) -> Fundacion | None:
        return await self.db.get(Fundacion, fundacion_id)

    # ------------------------------------------------------------------
    # Convocatorias
    # ------------------------------------------------------------------
    async def listar_convocatorias(
        self, page: int, per_page: int, estado: str | None = None,
        oculta: bool | None = None, buscar: str | None = None,
    ) -> tuple[list[tuple], int]:
        """Devuelve filas (Publicacion, fundacion_nombre, total_postulaciones)."""
        post_count = (
            select(func.count())
            .select_from(Postulacion)
            .where(Postulacion.publicacion_id == Publicacion.id)
            .scalar_subquery()
        )
        condiciones = []
        if estado:
            condiciones.append(Publicacion.estado == estado)
        if oculta is not None:
            condiciones.append(Publicacion.oculta_por_admin.is_(oculta))
        if buscar:
            condiciones.append(func.lower(Publicacion.titulo).like(f"%{buscar.lower()}%"))

        count_stmt = select(func.count()).select_from(Publicacion)
        data_stmt = (
            select(Publicacion, Fundacion.nombre, post_count.label("total_post"))
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .order_by(Publicacion.fecha_creacion.desc())
        )
        for c in condiciones:
            count_stmt = count_stmt.where(c)
            data_stmt = data_stmt.where(c)

        total = await self._count(count_stmt)
        data_stmt = data_stmt.limit(per_page).offset((page - 1) * per_page)
        rows = (await self.db.execute(data_stmt)).all()
        return rows, total

    async def convocatoria_por_id(self, pub_id: str | uuid.UUID) -> Publicacion | None:
        return await self.db.get(Publicacion, pub_id)

    # ------------------------------------------------------------------
    # Postulaciones
    # ------------------------------------------------------------------
    async def listar_postulaciones(
        self, page: int, per_page: int, estado: str | None = None,
    ) -> tuple[list[tuple], int]:
        """Devuelve filas (Postulacion, publicacion_titulo, voluntario_nombre)."""
        condiciones = []
        if estado:
            condiciones.append(Postulacion.estado == estado)

        count_stmt = select(func.count()).select_from(Postulacion)
        data_stmt = (
            select(Postulacion, Publicacion.titulo, Usuario.nombre)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Voluntario, Voluntario.id == Postulacion.voluntario_id)
            .join(Usuario, Usuario.id == Voluntario.usuario_id)
            .order_by(Postulacion.fecha_postulacion.desc())
        )
        for c in condiciones:
            count_stmt = count_stmt.where(c)
            data_stmt = data_stmt.where(c)

        total = await self._count(count_stmt)
        data_stmt = data_stmt.limit(per_page).offset((page - 1) * per_page)
        rows = (await self.db.execute(data_stmt)).all()
        return rows, total

    # ------------------------------------------------------------------
    # Voluntarios (verificación de identidad)
    # ------------------------------------------------------------------
    async def listar_voluntarios(
        self, page: int, per_page: int, verificado: bool | None = None,
        con_documento: bool | None = None, buscar: str | None = None,
    ) -> tuple[list[tuple], int]:
        """Devuelve filas (Voluntario, usuario_nombre, usuario_email)."""
        condiciones = []
        if verificado is not None:
            condiciones.append(Voluntario.esta_verificado.is_(verificado))
        if con_documento is True:
            condiciones.append(Voluntario.documento_identidad.isnot(None))
        elif con_documento is False:
            condiciones.append(Voluntario.documento_identidad.is_(None))
        if buscar:
            patron = f"%{buscar.lower()}%"
            condiciones.append(
                func.lower(Usuario.nombre).like(patron)
                | func.lower(Usuario.email).like(patron)
                | func.lower(Voluntario.numero_documento).like(patron)
            )

        count_stmt = (
            select(func.count())
            .select_from(Voluntario)
            .join(Usuario, Usuario.id == Voluntario.usuario_id)
        )
        data_stmt = (
            select(Voluntario, Usuario.nombre, Usuario.email)
            .join(Usuario, Usuario.id == Voluntario.usuario_id)
            .order_by(Voluntario.fecha_creacion.desc())
        )
        for c in condiciones:
            count_stmt = count_stmt.where(c)
            data_stmt = data_stmt.where(c)

        total = await self._count(count_stmt)
        data_stmt = data_stmt.limit(per_page).offset((page - 1) * per_page)
        rows = (await self.db.execute(data_stmt)).all()
        return rows, total

    async def voluntario_por_id(self, voluntario_id: str | uuid.UUID) -> Voluntario | None:
        return await self.db.get(Voluntario, voluntario_id)

    # ------------------------------------------------------------------
    # Catálogos
    # ------------------------------------------------------------------
    async def crear_area(self, nombre: str) -> AreaImpacto:
        area = AreaImpacto(nombre=nombre)
        self.db.add(area)
        await self.db.flush()
        return area

    async def crear_habilidad(self, nombre: str) -> Habilidad:
        hab = Habilidad(nombre=nombre)
        self.db.add(hab)
        await self.db.flush()
        return hab

    async def crear_departamento(self, nombre: str) -> Departamento:
        dep = Departamento(nombre=nombre)
        self.db.add(dep)
        await self.db.flush()
        return dep

    async def crear_municipio(self, nombre: str, departamento_id: int) -> Municipio:
        mun = Municipio(nombre=nombre, departamento_id=departamento_id)
        self.db.add(mun)
        await self.db.flush()
        return mun

    async def area_por_id(self, area_id: int) -> AreaImpacto | None:
        return await self.db.get(AreaImpacto, area_id)

    async def habilidad_por_id(self, hab_id: int) -> Habilidad | None:
        return await self.db.get(Habilidad, hab_id)

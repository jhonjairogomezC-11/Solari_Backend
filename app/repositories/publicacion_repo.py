"""Acceso a datos de publicaciones. Todo vía ORM con consultas parametrizadas."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalogo import Habilidad
from app.models.postulacion import Postulacion
from app.models.publicacion import ESTADO_PUBLICADA, Publicacion


class PublicacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _habilidades(self, ids: list[int]) -> list[Habilidad]:
        if not ids:
            return []
        stmt = select(Habilidad).where(Habilidad.id.in_(ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def listar_publicas(
        self,
        *,
        categoria_id: int | None = None,
        modalidad: str | None = None,
        municipio_id: int | None = None,
        buscar: str | None = None,
        page: int = 1,
        per_page: int = 15,
    ) -> tuple[list[Publicacion], int]:
        condiciones = [
            Publicacion.estado == ESTADO_PUBLICADA,
            Publicacion.oculta_por_admin.is_(False),
        ]
        if categoria_id:
            condiciones.append(Publicacion.categoria_id == categoria_id)
        if modalidad:
            condiciones.append(Publicacion.modalidad == modalidad)
        if municipio_id:
            condiciones.append(Publicacion.municipio_id == municipio_id)
        if buscar:
            term = f"%{buscar}%"
            condiciones.append(
                or_(
                    Publicacion.titulo.ilike(term),
                    Publicacion.descripcion.ilike(term),
                )
            )

        total = (
            await self.db.execute(
                select(func.count()).select_from(Publicacion).where(*condiciones)
            )
        ).scalar_one()

        stmt = (
            select(Publicacion)
            .options(selectinload(Publicacion.habilidades))
            .where(*condiciones)
            .order_by(Publicacion.fecha_inicio)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = list((await self.db.execute(stmt)).scalars().all())
        return filas, total

    async def por_id(self, publicacion_id: uuid.UUID) -> Publicacion | None:
        return await self.db.get(Publicacion, publicacion_id)

    async def por_id_con_habilidades(self, publicacion_id: uuid.UUID) -> Publicacion | None:
        stmt = (
            select(Publicacion)
            .options(selectinload(Publicacion.habilidades))
            .where(Publicacion.id == publicacion_id)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def cargar_habilidades(self, pub: Publicacion) -> None:
        """Carga la relación habilidades de forma async (evita lazy al serializar)."""
        await self.db.refresh(pub, attribute_names=["habilidades"])

    async def por_id_y_fundacion(
        self, publicacion_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> Publicacion | None:
        stmt = select(Publicacion).where(
            Publicacion.id == publicacion_id,
            Publicacion.fundacion_id == fundacion_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def crear(self, data: dict, habilidades: list[int]) -> Publicacion:
        pub = Publicacion(**data)
        pub.habilidades = await self._habilidades(habilidades) if habilidades else []
        self.db.add(pub)
        await self.db.flush()
        # Fuerza que la colección quede cargada (evita lazy-load al serializar).
        await self.db.refresh(pub, attribute_names=["habilidades"])
        return pub

    async def actualizar(
        self, pub: Publicacion, data: dict, habilidades: list[int] | None
    ) -> Publicacion:
        for key, value in data.items():
            setattr(pub, key, value)
        if habilidades is not None:
            pub.habilidades = await self._habilidades(habilidades)
        await self.db.flush()
        await self.db.refresh(pub, attribute_names=["habilidades"])
        return pub

    async def listar_de_fundacion(
        self, fundacion_id: uuid.UUID, page: int = 1, per_page: int = 15
    ) -> tuple[list[Publicacion], int]:
        total = (
            await self.db.execute(
                select(func.count())
                .select_from(Publicacion)
                .where(Publicacion.fundacion_id == fundacion_id)
            )
        ).scalar_one()
        stmt = (
            select(Publicacion)
            .options(selectinload(Publicacion.habilidades))
            .where(Publicacion.fundacion_id == fundacion_id)
            .order_by(Publicacion.fecha_creacion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = list((await self.db.execute(stmt)).scalars().all())
        return filas, total

    async def contar_postulaciones(self, publicacion_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Postulacion).where(
            Postulacion.publicacion_id == publicacion_id
        )
        return (await self.db.execute(stmt)).scalar_one()

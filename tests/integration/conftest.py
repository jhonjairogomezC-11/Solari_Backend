"""Fixtures de integración: usan la BD de desarrollo REAL (esquema completo).

Cada prueba crea sus propios usuarios con correos únicos `it_*@test.local` y, al
terminar, los elimina; el borrado en cascada retira perfiles, convocatorias,
postulaciones, ofrecimientos, notificaciones, etc. No se tocan datos existentes.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
import uuid
from datetime import date, timedelta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault("JWT_SECRET", "secreto-de-prueba-suficientemente-largo-123")

import pytest_asyncio  # noqa: E402
from sqlalchemy import delete, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models.catalogo import Habilidad  # noqa: E402
from app.models.fundacion import Fundacion  # noqa: E402
from app.models.publicacion import ESTADO_PUBLICADA, Publicacion  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.voluntario import Voluntario  # noqa: E402

DEV_URL = get_settings().database_url


@pytest_asyncio.fixture
async def maker():
    engine = create_async_engine(DEV_URL, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(maker):
    creados: list[uuid.UUID] = []
    async with maker() as session:
        session.info["creados"] = creados
        yield session
    # Limpieza en una sesión nueva (la de la prueba puede haber quedado en error).
    async with maker() as limpieza:
        if creados:
            # La auditoría referencia admin_perfiles con RESTRICT: se borra primero.
            sub = "SELECT id FROM admin_perfiles WHERE usuario_id = ANY(:ids)"
            await limpieza.execute(
                text(f"DELETE FROM admin_acciones WHERE admin_id IN ({sub})"), {"ids": creados}
            )
            await limpieza.execute(
                text(
                    f"DELETE FROM historial_estados_voluntario "
                    f"WHERE admin_id IN ({sub}) OR usuario_id = ANY(:ids)"
                ),
                {"ids": creados},
            )
            await limpieza.execute(delete(Usuario).where(Usuario.id.in_(creados)))
            await limpieza.commit()


async def _ids(db, sql: str) -> list[int]:
    return [r[0] for r in (await db.execute(text(sql))).all()]


@pytest_asyncio.fixture
async def catalogos(db):
    return {
        "municipio": (await _ids(db, "SELECT id FROM municipios ORDER BY id LIMIT 1"))[0],
        "area": (await _ids(db, "SELECT id FROM areas_impacto ORDER BY id LIMIT 1"))[0],
        "habilidades": await _ids(db, "SELECT id FROM habilidades ORDER BY id LIMIT 12"),
    }


async def _usuario(db, rol: str) -> Usuario:
    u = Usuario(
        nombre=f"Test {rol.title()} Prueba",
        email=f"it_{uuid.uuid4().hex[:12]}@test.local",
        password_hash="x",
        provider="LOCAL",
        rol=rol,
        estado="ACTIVO",
        email_verificado=True,
    )
    db.add(u)
    await db.commit()
    db.info["creados"].append(u.id)
    return u


@pytest_asyncio.fixture
async def crear_voluntario(db, catalogos):
    async def _crear(disponibilidad: str = "FLEXIBLE") -> Voluntario:
        u = await _usuario(db, "VOLUNTARIO")
        v = Voluntario(
            usuario_id=u.id,
            tipo_documento="CC",
            numero_documento=f"IT{uuid.uuid4().hex[:10]}",
            fecha_nacimiento=date(1995, 1, 1),
            genero="OTRO",
            municipio_id=catalogos["municipio"],
            disponibilidad=disponibilidad,
        )
        db.add(v)
        await db.commit()
        v._usuario = u  # type: ignore[attr-defined]
        return v

    return _crear


@pytest_asyncio.fixture
async def crear_fundacion(db, catalogos):
    async def _crear() -> Fundacion:
        u = await _usuario(db, "FUNDACION")
        nit = f"{random.randint(10**8, 10**9 - 1)}-{random.randint(0, 9)}"
        f = Fundacion(
            usuario_id=u.id,
            nombre=f"Org Prueba {uuid.uuid4().hex[:6]}",
            nit=nit,
            representante_legal="Rep Prueba",
            correo_institucional=f"{uuid.uuid4().hex[:8]}@org.test",
            telefono="3001234567",
            direccion="Calle 1 # 2-3",
            municipio_id=catalogos["municipio"],
            descripcion="Organización de prueba automatizada.",
            documento_legal="doc-prueba",
            estado_verificacion="APROBADA",
        )
        db.add(f)
        await db.commit()
        f._usuario = u  # type: ignore[attr-defined]
        return f

    return _crear


@pytest_asyncio.fixture
async def crear_admin(db):
    async def _crear() -> Usuario:
        u = await _usuario(db, "ADMIN")
        # La auditoría referencia el perfil de administrador, no el usuario.
        await db.execute(
            text(
                "INSERT INTO admin_perfiles (id, usuario_id, nivel, activo) "
                "VALUES (uuid_generate_v4(), :uid, 'OPERATIVO', true)"
            ),
            {"uid": u.id},
        )
        await db.commit()
        return u

    return _crear


@pytest_asyncio.fixture
async def crear_publicacion(db, catalogos):
    async def _crear(
        fundacion: Fundacion,
        *,
        cupo: int = 1,
        horas: int = 0,
        titulo: str | None = None,
        habilidades: list[int] | None = None,
        dias: int = 10,
    ) -> Publicacion:
        ids = habilidades if habilidades is not None else catalogos["habilidades"][:3]
        habs = (
            (await db.execute(select(Habilidad).where(Habilidad.id.in_(ids)))).scalars().all()
            if ids
            else []
        )
        pub = Publicacion(
            fundacion_id=fundacion.id,
            titulo=titulo or f"Jornada prueba {uuid.uuid4().hex[:6]}",
            descripcion="Descripción de la jornada de prueba.",
            categoria_id=catalogos["area"],
            modalidad="PRESENCIAL",
            municipio_id=catalogos["municipio"],
            fecha_inicio=date.today() + timedelta(days=dias),
            fecha_fin=date.today() + timedelta(days=dias),
            cupo_maximo=cupo,
            horas_reconocidas=horas,
            estado=ESTADO_PUBLICADA,
            dificultad="FACIL",
            habilidades=list(habs),
        )
        db.add(pub)
        await db.commit()
        return pub

    return _crear

"""Fixtures de pruebas: BD PostgreSQL de test aislada + cliente HTTP.

El esquema real lo crea Laravel. Para las pruebas se recrea en la base aislada
`voluntapp_test` un esquema equivalente (tablas de auth + columnas aditivas +
tablas legales), de modo que nunca se tocan los datos reales.
"""

from __future__ import annotations

import asyncio
import os
import sys

# psycopg async en Windows requiere SelectorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("JWT_SECRET", "secreto-de-prueba-suficientemente-largo-123")
os.environ.setdefault("GOOGLE_CLIENT_ID", "")

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:admin@127.0.0.1:5432/voluntapp_test",
)

# ── DDL equivalente al esquema real (solo lo necesario para auth) ──
_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS usuario_aceptaciones_legales CASCADE;
DROP TABLE IF EXISTS documento_legal_versiones CASCADE;
DROP TABLE IF EXISTS documentos_legales CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS recuperacion_password CASCADE;
DROP TABLE IF EXISTS verificacion_email CASCADE;
DROP TABLE IF EXISTS voluntarios CASCADE;
DROP TABLE IF EXISTS fundaciones CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Tipos ENUM nativos equivalentes a los del esquema real (idempotentes).
DO $$ BEGIN CREATE TYPE rol_usuario AS ENUM ('VOLUNTARIO','FUNDACION','ADMIN'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE estado_usuario AS ENUM ('ACTIVO','BLOQUEADO','SUSPENDIDO'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE proveedor_auth AS ENUM ('LOCAL','GOOGLE'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE tipo_documento AS ENUM ('CC','TI','CE','PASAPORTE'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE genero_tipo AS ENUM ('MASCULINO','FEMENINO','OTRO'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE disponibilidad_tipo AS ENUM ('ENTRE_SEMANA','FINES_DE_SEMANA','FLEXIBLE'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE estado_verificacion AS ENUM ('PENDIENTE','APROBADA','RECHAZADA','SUSPENDIDA'); EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE usuarios (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre varchar(120) NOT NULL,
    email varchar(150) NOT NULL,
    password_hash text,
    provider proveedor_auth NOT NULL DEFAULT 'LOCAL',
    provider_id varchar(255),
    telefono varchar(20),
    rol rol_usuario NOT NULL,
    estado estado_usuario NOT NULL DEFAULT 'ACTIVO',
    email_verificado boolean NOT NULL DEFAULT false,
    fecha_registro timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_email_provider_unique ON usuarios(email, provider);

CREATE TABLE voluntarios (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_documento tipo_documento NOT NULL,
    numero_documento varchar(30) NOT NULL UNIQUE,
    documento_identidad varchar,
    esta_verificado boolean NOT NULL DEFAULT false,
    fecha_nacimiento date NOT NULL,
    genero genero_tipo NOT NULL,
    municipio_id integer NOT NULL,
    disponibilidad disponibilidad_tipo NOT NULL,
    experiencia text,
    foto_perfil varchar(500),
    direccion varchar(200),
    descripcion text,
    telefono_contacto varchar(20),
    nivel_educativo varchar(100),
    profesion varchar(150),
    idiomas varchar(300),
    preferencia_modalidad varchar(20),
    contacto_emergencia_nombre varchar(150),
    contacto_emergencia_telefono varchar(20),
    horas_acumuladas integer NOT NULL DEFAULT 0,
    actividades_completadas integer NOT NULL DEFAULT 0,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fundaciones (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre varchar(150) NOT NULL,
    nit varchar(20) UNIQUE,
    representante_legal varchar(150) NOT NULL,
    correo_institucional varchar(150),
    telefono varchar(20) NOT NULL,
    direccion varchar(200) NOT NULL,
    municipio_id integer NOT NULL,
    pagina_web varchar(255),
    descripcion text NOT NULL,
    documento_legal text,
    logo varchar(500),
    estado_verificacion estado_verificacion NOT NULL DEFAULT 'PENDIENTE',
    fecha_verificacion timestamp,
    motivo_rechazo text,
    tipo_organizacion varchar(30) NOT NULL DEFAULT 'FUNDACION',
    constituida_legalmente boolean NOT NULL DEFAULT true,
    historia text,
    mision text,
    mostrar_telefono boolean NOT NULL DEFAULT false,
    mostrar_correo boolean NOT NULL DEFAULT false,
    mostrar_direccion boolean NOT NULL DEFAULT false,
    verificacion_documental varchar(30) NOT NULL DEFAULT 'NO_SOLICITADA',
    verificacion_documental_fecha timestamp,
    verificacion_documental_nota text,
    verificacion_documental_por uuid,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_tokens (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token text,
    token_hash varchar(64),
    expiracion timestamp NOT NULL,
    usado boolean NOT NULL DEFAULT false,
    fecha_uso timestamp,
    ip_solicitud varchar(50),
    user_agent text,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recuperacion_password (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token text,
    token_hash varchar(64),
    expiracion timestamp NOT NULL,
    usado boolean NOT NULL DEFAULT false,
    fecha_uso timestamp,
    intentos integer DEFAULT 0,
    ip_solicitud varchar(50),
    user_agent text,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE verificacion_email (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token text,
    token_hash varchar(64),
    expiracion timestamp NOT NULL,
    usado boolean NOT NULL DEFAULT false,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documentos_legales (
    id serial PRIMARY KEY,
    codigo varchar(60) NOT NULL UNIQUE,
    nombre varchar(150) NOT NULL,
    descripcion text,
    requerido_registro boolean NOT NULL DEFAULT true,
    fecha_creacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documento_legal_versiones (
    id serial PRIMARY KEY,
    documento_id integer NOT NULL REFERENCES documentos_legales(id) ON DELETE CASCADE,
    version varchar(40) NOT NULL,
    contenido text,
    contenido_hash varchar(64),
    url_publica varchar(500),
    vigente boolean NOT NULL DEFAULT false,
    fecha_publicacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_version UNIQUE (documento_id, version)
);

CREATE TABLE usuario_aceptaciones_legales (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    version_id integer NOT NULL REFERENCES documento_legal_versiones(id) ON DELETE RESTRICT,
    aceptado boolean NOT NULL DEFAULT true,
    ip_aceptacion varchar(50),
    user_agent text,
    fecha_aceptacion timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, poolclass=None)
    async with engine.begin() as conn:
        # Ejecuta el script completo de una vez (contiene bloques DO $$ con ';'
        # internos que no deben separarse).
        await conn.exec_driver_sql(_SCHEMA_SQL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    from app.api.deps import get_app_settings
    from app.core.config import Settings
    from app.db.session import get_db
    from app.main import create_app

    testing_sessionmaker = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with testing_sessionmaker() as session:
            yield session

    def _override_settings() -> Settings:
        return Settings(  # type: ignore[call-arg]
            jwt_secret="secreto-de-prueba-suficientemente-largo-123",
            database_url=TEST_DB_URL,
        )

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_app_settings] = _override_settings
    # Desactiva el rate limiting en pruebas para no bloquear casos repetidos.
    app.state.limiter.enabled = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def voluntario_payload() -> dict:
    return {
        "nombre": "Ana Prueba",
        "email": "ana.prueba@example.com",
        "password": "ClaveSegura123",
        "password_confirmation": "ClaveSegura123",
        "rol": "VOLUNTARIO",
        "telefono": "3001234567",
        "tipo_documento": "CC",
        "numero_documento": "1234567890",
        "fecha_nacimiento": "2000-01-01",
        "genero": "FEMENINO",
        "municipio_id": 1,
        "disponibilidad": "FLEXIBLE",
    }


@pytest.fixture
def fundacion_payload() -> dict:
    return {
        "nombre": "Rep Legal",
        "email": "contacto@fundacion.org",
        "password": "ClaveSegura123",
        "password_confirmation": "ClaveSegura123",
        "rol": "FUNDACION",
        "nombre_fundacion": "Fundación Ejemplo",
        "nit": "900123456-7",
        "representante_legal": "Rep Legal",
        "telefono_contacto": "6011234567",
        "direccion": "Calle 1 # 2-3",
        "municipio_id": 1,
        "descripcion": "Trabajamos por la comunidad.",
        "documento_legal": "doc-legal-ref",
    }

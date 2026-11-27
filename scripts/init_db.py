"""Inicialización completa de la base de datos PostgreSQL desde cero para Solari.

Crea:
- Extensiones requeridas (uuid-ossp).
- Tipos ENUM nativos de PostgreSQL.
- Todas las tablas del modelo SQLAlchemy (Base.metadata).
- Registro de versión en alembic_version (0004_notif_post).
- Datos semilla (departamentos, municipios, logros, áreas de impacto, habilidades, intereses).
"""

from __future__ import annotations

import asyncio
import sys
from sqlalchemy import text
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
import app.models  # Registra todos los modelos

ENUMS = [
    ("rol_usuario", ["'VOLUNTARIO'", "'FUNDACION'", "'ADMIN'"]),
    ("estado_usuario", ["'ACTIVO'", "'BLOQUEADO'", "'SUSPENDIDO'"]),
    ("proveedor_auth", ["'LOCAL'", "'GOOGLE'"]),
    ("tipo_documento", ["'CC'", "'TI'", "'CE'", "'PASAPORTE'"]),
    ("genero_tipo", ["'MASCULINO'", "'FEMENINO'", "'OTRO'"]),
    ("disponibilidad_tipo", ["'ENTRE_SEMANA'", "'FINES_DE_SEMANA'", "'FLEXIBLE'"]),
    ("estado_verificacion", ["'PENDIENTE'", "'APROBADA'", "'RECHAZADA'", "'SUSPENDIDA'"]),
    ("modalidad_tipo", ["'PRESENCIAL'", "'VIRTUAL'", "'HIBRIDA'"]),
    ("estado_publicacion", ["'BORRADOR'", "'PENDIENTE_APROBACION'", "'PUBLICADA'", "'CERRADA'", "'CANCELADA'", "'COMPLETADA'", "'FINALIZADA'"]),
    ("dificultad_tipo", ["'FACIL'", "'MEDIA'", "'DIFICIL'", "'MUY_DIFICIL'"]),
    ("estado_postulacion", ["'PENDIENTE'", "'ACEPTADO'", "'RECHAZADO'", "'RETIRADO'", "'ASISTIO'", "'NO_ASISTIO'", "'EN_REVISION'", "'LISTA_ESPERA'", "'CANCELADO_FUNDACION'"]),
    ("tipo_notificacion", [
        "'NUEVA_POSTULACION'", "'POSTULACION_RETIRADA'", "'VOLUNTARIO_ASISTIO'", "'VOLUNTARIO_NO_ASISTIO'",
        "'POSTULACION_ACEPTADA'", "'POSTULACION_RECHAZADA'", "'ACTIVIDAD_CANCELADA'", "'ACTIVIDAD_MODIFICADA'",
        "'FUNDACION_APROBADA'", "'FUNDACION_RECHAZADA'", "'NUEVA_CONVOCATORIA_COMPATIBLE'", "'LOGRO_DESBLOQUEADO'",
        "'XP_OBTENIDO'", "'RESPUESTA_SOPORTE'", "'CUENTA_ACTUALIZADA'", "'NUEVO_MENSAJE'", "'INTERES_RECIBIDO'",
        "'INTERES_ACTUALIZADO'", "'PROGRAMACION_PAUSADA'", "'VERIFICACION_ACTUALIZADA'", "'NUEVA_RESENA'",
        "'RESENA_RESPONDIDA'", "'POSTULACION_ACTUALIZADA'"
    ]),
    ("tipo_accion_admin", [
        "'USUARIO_SUSPENDIDO'", "'USUARIO_BLOQUEADO'", "'USUARIO_REACTIVADO'", "'USUARIO_ELIMINADO'",
        "'USUARIO_EDITADO'", "'FUNDACION_APROBADA'", "'FUNDACION_RECHAZADA'", "'FUNDACION_SUSPENDIDA'",
        "'FUNDACION_REACTIVADA'", "'PUBLICACION_OCULTADA'", "'PUBLICACION_RESTAURADA'", "'PUBLICACION_ELIMINADA'",
        "'PUBLICACION_ESTADO_CAMBIADO'", "'POSTULACION_INTERVENIDA'", "'REPORTE_RESUELTO'", "'REPORTE_DESESTIMADO'",
        "'PUNTOS_AJUSTADOS'", "'LOGRO_ASIGNADO'", "'ADMIN_CREADO'", "'ADMIN_DESACTIVADO'", "'ADMIN_PERMISOS_ACTUALIZADOS'",
        "'SOPORTE_RESPONDIDO'", "'SOLICITUD_CUENTA_RESUELTA'", "'USUARIO_ANONIMIZADO'", "'VERIFICACION_DOCUMENTAL_RESUELTA'",
        "'RESENA_MODERADA'", "'VOLUNTARIO_VERIFICADO'", "'CATALOGO_MODIFICADO'"
    ]),
]

LOGROS_DATA = [
    ("valiente", "Valiente", "Participa en al menos 1 convocatoria urgente.", "zap", "urgente", 1),
    ("primer_paso", "Primer Paso", "Completa tu primera actividad de voluntariado.", "award", "participaciones", 1),
    ("heroe", "Héroe", "Completa una actividad de dificultad alta o muy difícil.", "shield", "dificultad", 1),
    ("siempre_presente", "Siempre Presente", "Participa en 3 actividades de voluntariado.", "calendar", "participaciones", 3),
    ("comprometido", "Comprometido", "Participa en 5 actividades de voluntariado.", "heart", "participaciones", 5),
    ("voluntario_activo", "Voluntario Activo", "Participa en 10 actividades de voluntariado.", "check-circle", "participaciones", 10),
    ("impacto_social", "Impacto Social", "Participa en 25 actividades de voluntariado.", "globe", "participaciones", 25),
    ("leyenda_solidaria", "Leyenda Solidaria", "Participa en 50 actividades de voluntariado.", "crown", "participaciones", 50),
    ("acumulador", "Acumulador", "Alcanza 100 puntos de experiencia (XP).", "star", "puntos", 100),
    ("veterano", "Veterano", "Alcanza 500 puntos de experiencia (XP).", "trending-up", "puntos", 500),
    ("elite", "Élite", "Alcanza 1000 puntos de experiencia (XP).", "sparkles", "puntos", 1000),
]

DEPARTAMENTOS_DATA = [
    (1, "Bogotá D.C."),
    (2, "Cundinamarca"),
]

MUNICIPIOS_DATA = [
    (1, "Bogotá D.C.", 1),
    (2, "Soacha", 2),
    (3, "Chía", 2),
    (4, "Zipaquirá", 2),
    (5, "Facatativá", 2),
    (6, "Mosquera", 2),
    (7, "Madrid", 2),
    (8, "Funza", 2),
    (9, "Cajicá", 2),
    (10, "Sibaté", 2),
    (11, "Tocancipá", 2),
    (12, "Tabio", 2),
    (13, "Tenjo", 2),
    (14, "Sopó", 2),
    (15, "Cota", 2),
    (16, "La Calera", 2),
    (17, "Cogua", 2),
    (18, "Nemocón", 2),
    (19, "Subachoque", 2),
    (20, "Bojacá", 2),
    (21, "Gachancipá", 2),
    (22, "El Rosal", 2),
    (23, "Girardot", 2),
    (24, "Fusagasugá", 2),
    (25, "Ubaté", 2),
    (26, "Pacho", 2),
    (27, "Villeta", 2),
    (28, "Guaduas", 2),
    (29, "Chocontá", 2),
    (30, "Cáqueza", 2),
    (31, "La Mesa", 2),
    (32, "Anapoima", 2),
    (33, "Guatavita", 2),
    (34, "Sesquilé", 2),
]


async def main() -> None:
    settings = get_settings()
    print(f"Inicializando BD en {settings.database_url}...")

    async with engine.begin() as conn:
        # 1. Extensiones
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))

        # 2. ENUMs
        for enum_name, values in ENUMS:
            vals_str = ", ".join(values)
            await conn.execute(text(
                f"DO $$ BEGIN CREATE TYPE {enum_name} AS ENUM ({vals_str}); "
                f"EXCEPTION WHEN duplicate_object THEN null; END $$;"
            ))

        # 3. Crear todas las tablas declaradas
        await conn.run_sync(Base.metadata.create_all)

        # 4. Tabla de alembic para marcar la versión head
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"
        ))
        await conn.execute(text(
            "INSERT INTO alembic_version (version_num) VALUES ('0004_notif_post') "
            "ON CONFLICT (version_num) DO NOTHING;"
        ))

    print("Tablas y extensiones creadas exitosamente.")

    # 5. Sembrar catálogos iniciales
    async with AsyncSessionLocal() as db:
        # Departamentos
        for dep_id, dep_nombre in DEPARTAMENTOS_DATA:
            await db.execute(text(
                "INSERT INTO departamentos (id, nombre) VALUES (:id, :nombre) "
                "ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre"
            ), {"id": dep_id, "nombre": dep_nombre})

        # Sincronizar secuencia de departamentos
        await db.execute(text("SELECT setval('departamentos_id_seq', (SELECT COALESCE(MAX(id), 1) FROM departamentos));"))

        # Municipios
        for mun_id, mun_nombre, dep_id in MUNICIPIOS_DATA:
            await db.execute(text(
                "INSERT INTO municipios (id, nombre, departamento_id) VALUES (:id, :nombre, :dep_id) "
                "ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre, departamento_id = EXCLUDED.departamento_id"
            ), {"id": mun_id, "nombre": mun_nombre, "dep_id": dep_id})

        # Sincronizar secuencia de municipios
        await db.execute(text("SELECT setval('municipios_id_seq', (SELECT COALESCE(MAX(id), 1) FROM municipios));"))

        # Logros
        for codigo, nombre, descripcion, icono, tipo, umbral in LOGROS_DATA:
            await db.execute(text(
                "INSERT INTO logros (codigo, nombre, descripcion, icono, tipo, umbral, activo) "
                "VALUES (:codigo, :nombre, :descripcion, :icono, :tipo, :umbral, true) "
                "ON CONFLICT (codigo) DO UPDATE SET "
                "nombre = EXCLUDED.nombre, descripcion = EXCLUDED.descripcion, "
                "icono = EXCLUDED.icono, tipo = EXCLUDED.tipo, umbral = EXCLUDED.umbral"
            ), {
                "codigo": codigo, "nombre": nombre, "descripcion": descripcion,
                "icono": icono, "tipo": tipo, "umbral": umbral
            })

        # Documentos legales por defecto
        await db.execute(text(
            "INSERT INTO documentos_legales (codigo, nombre, descripcion, requerido_registro) "
            "VALUES "
            "('TERMINOS', 'Términos y Condiciones de Uso', 'Términos de servicio para el uso de Solari', true), "
            "('PRIVACIDAD', 'Política de Tratamiento de Datos Personales', 'Cumplimiento de la Ley 1581 de 2012', true) "
            "ON CONFLICT (codigo) DO NOTHING;"
        ))

        # Versiones de documentos legales
        await db.execute(text(
            "INSERT INTO documento_legal_versiones (documento_id, version, contenido, vigente) "
            "SELECT id, '1.0', 'Términos y condiciones vigentes de la plataforma Solari.', true "
            "FROM documentos_legales WHERE codigo = 'TERMINOS' "
            "ON CONFLICT (documento_id, version) DO NOTHING;"
        ))
        await db.execute(text(
            "INSERT INTO documento_legal_versiones (documento_id, version, contenido, vigente) "
            "SELECT id, '1.0', 'Política de privacidad y protección de datos personales de Solari.', true "
            "FROM documentos_legales WHERE codigo = 'PRIVACIDAD' "
            "ON CONFLICT (documento_id, version) DO NOTHING;"
        ))

        await db.commit()

    print("Catálogos básicos (departamentos, municipios, logros, legal) sembrados.")

    # 6. Ejecutar seeds existentes
    from scripts.seed_areas_impacto import main as seed_areas
    from scripts.seed_habilidades import main as seed_habilidades
    from scripts.seed_intereses import main as seed_intereses

    print("Sembrando áreas de impacto...")
    await seed_areas()

    print("Sembrando habilidades...")
    await seed_habilidades()

    print("Sembrando intereses...")
    await seed_intereses()

    print("¡Base de datos inicializada y sembrada completamente con éxito!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())

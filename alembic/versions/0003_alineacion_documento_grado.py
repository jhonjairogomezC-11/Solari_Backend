"""Alineación con el documento de grado.

Revision ID: 0003_alineacion
Revises: 0002_voluntario
Create Date: 2026-11-22

ADITIVA. Añade lo que el documento de grado especifica y el código no tenía:
- Habilidades con categoría y tipo (profesional / general).
- Organizaciones sin constitución legal (NIT y documento legal opcionales),
  perfil público, privacidad de contacto y verificación documental.
- Historial de estados de postulación (R8).
- Actividades recurrentes (R4).
- Objetos y servicios voluntarios con solicitudes de interés y mensajería.
- Galería de la organización y reseñas (R12).
- Valores nuevos en enums de notificación y de auditoría administrativa.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0003_alineacion"
down_revision: str | None = "0002_voluntario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NUEVOS_TIPOS_NOTIF = (
    "NUEVO_MENSAJE", "INTERES_RECIBIDO", "INTERES_ACTUALIZADO",
    "PROGRAMACION_PAUSADA", "VERIFICACION_ACTUALIZADA",
    "NUEVA_RESENA", "RESENA_RESPONDIDA",
)
_NUEVAS_ACCIONES = (
    "SOPORTE_RESPONDIDO", "SOLICITUD_CUENTA_RESUELTA", "USUARIO_ANONIMIZADO",
    "VERIFICACION_DOCUMENTAL_RESUELTA", "RESENA_MODERADA",
    "VOLUNTARIO_VERIFICADO", "CATALOGO_MODIFICADO",
)

_UUID = pg.UUID(as_uuid=True)
_NOW = sa.text("CURRENT_TIMESTAMP")
_UUID_DEF = sa.text("uuid_generate_v4()")


def _add_enum_values() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    for val in _NUEVOS_TIPOS_NOTIF:
        conn.execute(sa.text(f"ALTER TYPE tipo_notificacion ADD VALUE IF NOT EXISTS '{val}'"))
    for val in _NUEVAS_ACCIONES:
        conn.execute(sa.text(f"ALTER TYPE tipo_accion_admin ADD VALUE IF NOT EXISTS '{val}'"))


def upgrade() -> None:
    _add_enum_values()

    # ── Habilidades: categoría y tipo ──
    op.add_column("habilidades", sa.Column("categoria", sa.String(60), nullable=True))
    op.add_column(
        "habilidades",
        sa.Column("es_profesional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # ── Organizaciones: sin constitución legal, perfil público, verificación ──
    op.alter_column("fundaciones", "nit", existing_type=sa.String(20), nullable=True)
    op.alter_column("fundaciones", "documento_legal", existing_type=sa.Text(), nullable=True)
    op.add_column(
        "fundaciones",
        sa.Column("tipo_organizacion", sa.String(30), nullable=False, server_default="FUNDACION"),
    )
    op.add_column(
        "fundaciones",
        sa.Column("constituida_legalmente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("fundaciones", sa.Column("historia", sa.Text(), nullable=True))
    op.add_column("fundaciones", sa.Column("mision", sa.Text(), nullable=True))
    for col in ("mostrar_telefono", "mostrar_correo", "mostrar_direccion"):
        op.add_column(
            "fundaciones",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    op.add_column(
        "fundaciones",
        sa.Column("verificacion_documental", sa.String(30), nullable=False, server_default="NO_SOLICITADA"),
    )
    op.add_column("fundaciones", sa.Column("verificacion_documental_fecha", sa.TIMESTAMP(), nullable=True))
    op.add_column("fundaciones", sa.Column("verificacion_documental_nota", sa.Text(), nullable=True))
    op.add_column(
        "fundaciones",
        sa.Column("verificacion_documental_por", _UUID, sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
    )

    # ── Historial de estados de postulación (R8) ──
    op.create_table(
        "postulacion_historial",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("postulacion_id", _UUID, sa.ForeignKey("postulaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estado_anterior", sa.String(30), nullable=True),
        sa.Column("estado_nuevo", sa.String(30), nullable=False),
        sa.Column("cambiado_por", _UUID, sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rol_actor", sa.String(20), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("fecha", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
    )
    op.create_index("idx_post_hist_post", "postulacion_historial", ["postulacion_id"])

    # ── Actividades recurrentes (R4) ──
    op.create_table(
        "programaciones_recurrentes",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("fundacion_id", _UUID, sa.ForeignKey("fundaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("plantilla", pg.JSONB(), nullable=False),
        sa.Column("unidad_intervalo", sa.String(10), nullable=False),
        sa.Column("intervalo", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("duracion_dias", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fin", sa.Time(), nullable=True),
        sa.Column("cupo_maximo", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ACTIVA"),
        sa.Column("total_generadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ciclo_generadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proxima_fecha", sa.Date(), nullable=False),
        sa.Column("fecha_pausa", sa.TIMESTAMP(), nullable=True),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.Column("fecha_actualizacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.CheckConstraint("intervalo >= 1", name="chk_prog_intervalo"),
    )
    op.create_index("idx_prog_fundacion", "programaciones_recurrentes", ["fundacion_id"])
    op.add_column(
        "publicaciones",
        sa.Column(
            "programacion_id", _UUID,
            sa.ForeignKey("programaciones_recurrentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_pub_programacion", "publicaciones", ["programacion_id"])

    # ── Objetos y servicios voluntarios ──
    op.create_table(
        "ofrecimientos",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("voluntario_id", _UUID, sa.ForeignKey("voluntarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("categoria", sa.String(60), nullable=False),
        sa.Column("cantidad_total", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cantidad_disponible", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estado_producto", sa.String(30), nullable=True),
        sa.Column("modalidad_entrega", sa.String(30), nullable=True),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("disponibilidad", sa.Text(), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("condiciones", sa.Text(), nullable=True),
        sa.Column("imagenes", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("estado", sa.String(30), nullable=False, server_default="DISPONIBLE"),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.Column("fecha_actualizacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.CheckConstraint("tipo IN ('OBJETO','SERVICIO')", name="chk_of_tipo"),
        sa.CheckConstraint("cantidad_total >= 1", name="chk_of_cant_total"),
        sa.CheckConstraint(
            "cantidad_disponible >= 0 AND cantidad_disponible <= cantidad_total",
            name="chk_of_cant_disp",
        ),
    )
    op.create_index("idx_of_voluntario", "ofrecimientos", ["voluntario_id"])
    op.create_index("idx_of_estado_tipo", "ofrecimientos", ["estado", "tipo"])
    op.create_table(
        "ofrecimiento_habilidades",
        sa.Column("ofrecimiento_id", _UUID, sa.ForeignKey("ofrecimientos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("habilidad_id", sa.Integer(), sa.ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "solicitudes_interes",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("ofrecimiento_id", _UUID, sa.ForeignKey("ofrecimientos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fundacion_id", _UUID, sa.ForeignKey("fundaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("confirmada_voluntario", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("confirmada_fundacion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.Column("fecha_actualizacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.Column("fecha_completada", sa.TIMESTAMP(), nullable=True),
        sa.CheckConstraint("cantidad >= 1", name="chk_si_cantidad"),
    )
    op.create_index("idx_si_ofrecimiento", "solicitudes_interes", ["ofrecimiento_id"])
    op.create_index("idx_si_fundacion", "solicitudes_interes", ["fundacion_id"])
    op.create_index(
        "uq_si_activa", "solicitudes_interes", ["ofrecimiento_id", "fundacion_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('PENDIENTE','ACEPTADA','EN_COORDINACION')"),
    )
    op.create_table(
        "mensajes_interes",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("solicitud_id", _UUID, sa.ForeignKey("solicitudes_interes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("autor_id", _UUID, sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
    )
    op.create_index("idx_msg_interes_sol", "mensajes_interes", ["solicitud_id"])

    # ── Galería y reseñas ──
    op.create_table(
        "fundacion_galeria",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("fundacion_id", _UUID, sa.ForeignKey("fundaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ruta", sa.String(500), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("contiene_menores", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("autorizacion_imagen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
    )
    op.create_index("idx_galeria_fund", "fundacion_galeria", ["fundacion_id"])
    op.create_table(
        "resenas_organizacion",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column("fundacion_id", _UUID, sa.ForeignKey("fundaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voluntario_id", _UUID, sa.ForeignKey("voluntarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calificacion", sa.SmallInteger(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="VISIBLE"),
        sa.Column("motivo_moderacion", sa.Text(), nullable=True),
        sa.Column("respuesta", sa.Text(), nullable=True),
        sa.Column("fecha_respuesta", sa.TIMESTAMP(), nullable=True),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.CheckConstraint("calificacion BETWEEN 1 AND 5", name="chk_resena_calif"),
        sa.UniqueConstraint("fundacion_id", "voluntario_id", name="uq_resena_vol_fund"),
    )
    op.create_index("idx_resena_fund_estado", "resenas_organizacion", ["fundacion_id", "estado"])


def downgrade() -> None:
    op.drop_table("resenas_organizacion")
    op.drop_table("fundacion_galeria")
    op.drop_table("mensajes_interes")
    op.drop_table("solicitudes_interes")
    op.drop_table("ofrecimiento_habilidades")
    op.drop_table("ofrecimientos")
    op.drop_index("idx_pub_programacion", table_name="publicaciones")
    op.drop_column("publicaciones", "programacion_id")
    op.drop_table("programaciones_recurrentes")
    op.drop_table("postulacion_historial")
    for col in (
        "verificacion_documental_por", "verificacion_documental_nota",
        "verificacion_documental_fecha", "verificacion_documental",
        "mostrar_direccion", "mostrar_correo", "mostrar_telefono",
        "mision", "historia", "constituida_legalmente", "tipo_organizacion",
    ):
        op.drop_column("fundaciones", col)
    op.drop_column("habilidades", "es_profesional")
    op.drop_column("habilidades", "categoria")
    # nit/documento_legal vuelven a NOT NULL solo si no hay filas nulas.
    # Los valores añadidos a enums nativos no se eliminan (PostgreSQL no lo permite).

"""Aditivo: expansión del módulo de voluntario.

Revision ID: 0002_voluntario
Revises: 0001_aditivo
Create Date: 2026-11-08

ESTRICTAMENTE ADITIVO. Reutiliza tablas que Laravel ya creó
(intereses, logros, voluntario_puntos, transacciones_puntos, publicacion_imagenes).
Solo:
- Añade columnas nullable/con default a `voluntarios` y `publicaciones`.
- Amplía los ENUM nativos `estado_postulacion` y `tipo_notificacion`.
- Crea tablas NUEVAS que no existen: soporte (tickets/mensajes/solicitudes),
  preferencias de notificación y auditoría de perfil.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_voluntario"
down_revision: str | None = "0001_aditivo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NUEVOS_ESTADOS_POST = ("EN_REVISION", "LISTA_ESPERA", "CANCELADO_FUNDACION")
_NUEVOS_TIPOS_NOTIF = (
    "NUEVA_CONVOCATORIA_COMPATIBLE",
    "LOGRO_DESBLOQUEADO",
    "XP_OBTENIDO",
    "RESPUESTA_SOPORTE",
    "CUENTA_ACTUALIZADA",
)


def _add_enum_values() -> None:
    # ADD VALUE debe ejecutarse en autocommit (no dentro del bloque transaccional).
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    for val in _NUEVOS_ESTADOS_POST:
        conn.execute(sa.text(f"ALTER TYPE estado_postulacion ADD VALUE IF NOT EXISTS '{val}'"))
    for val in _NUEVOS_TIPOS_NOTIF:
        conn.execute(sa.text(f"ALTER TYPE tipo_notificacion ADD VALUE IF NOT EXISTS '{val}'"))


def upgrade() -> None:
    _add_enum_values()

    # ── Columnas nuevas en voluntarios ──
    with op.batch_alter_table("voluntarios") as b:
        b.add_column(sa.Column("direccion", sa.String(length=200), nullable=True))
        b.add_column(sa.Column("descripcion", sa.Text(), nullable=True))
        b.add_column(sa.Column("telefono_contacto", sa.String(length=20), nullable=True))
        b.add_column(sa.Column("nivel_educativo", sa.String(length=100), nullable=True))
        b.add_column(sa.Column("profesion", sa.String(length=150), nullable=True))
        b.add_column(sa.Column("idiomas", sa.String(length=300), nullable=True))
        b.add_column(sa.Column("preferencia_modalidad", sa.String(length=20), nullable=True))
        b.add_column(sa.Column("contacto_emergencia_nombre", sa.String(length=150), nullable=True))
        b.add_column(sa.Column("contacto_emergencia_telefono", sa.String(length=20), nullable=True))
        b.add_column(sa.Column("horas_acumuladas", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(
            sa.Column("actividades_completadas", sa.Integer(), nullable=False, server_default="0")
        )

    # ── Columnas nuevas en publicaciones ──
    with op.batch_alter_table("publicaciones") as b:
        b.add_column(sa.Column("objetivo", sa.Text(), nullable=True))
        b.add_column(sa.Column("impacto_esperado", sa.Text(), nullable=True))
        b.add_column(sa.Column("actividades_voluntario", sa.Text(), nullable=True))
        b.add_column(sa.Column("perfil_beneficiarios", sa.Text(), nullable=True))
        b.add_column(sa.Column("que_llevar", sa.Text(), nullable=True))
        b.add_column(sa.Column("recomendaciones", sa.Text(), nullable=True))
        b.add_column(sa.Column("incluye_transporte", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        b.add_column(sa.Column("incluye_alimentacion", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        b.add_column(sa.Column("incluye_seguro", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        b.add_column(sa.Column("politica_cancelacion", sa.Text(), nullable=True))
        b.add_column(sa.Column("otorga_certificado", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        b.add_column(sa.Column("horas_reconocidas", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("nivel_experiencia", sa.String(length=40), nullable=True))
        b.add_column(sa.Column("fecha_limite_postulacion", sa.Date(), nullable=True))

    # ── Soporte (tablas nuevas) ──
    op.execute("CREATE SEQUENCE IF NOT EXISTS ticket_numero_seq START 1")
    op.create_table(
        "tickets_soporte",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.BigInteger(), nullable=False, server_default=sa.text("nextval('ticket_numero_seq')")),
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria", sa.String(length=40), nullable=False),
        sa.Column("asunto", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("adjunto_url", sa.String(length=500), nullable=True),
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="ABIERTO"),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("fecha_actualizacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("numero", name="uq_tickets_numero"),
    )
    op.create_index("idx_tickets_usuario", "tickets_soporte", ["usuario_id"])
    op.create_table(
        "ticket_mensajes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("autor_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("es_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("adjunto_url", sa.String(length=500), nullable=True),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets_soporte.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_ticket_mensajes_ticket", "ticket_mensajes", ["ticket_id"])
    op.create_table(
        "solicitudes_cuenta",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="PENDIENTE"),
        sa.Column("respuesta_admin", sa.Text(), nullable=True),
        sa.Column("atendida_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fecha_atencion", sa.TIMESTAMP(), nullable=True),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["atendida_por"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_solicitudes_usuario", "solicitudes_cuenta", ["usuario_id"])

    # ── Cuenta / auditoría (tablas nuevas) ──
    op.create_table(
        "preferencias_notificacion",
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notif_postulaciones", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_convocatorias", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_recordatorios", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_logros", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_soporte", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("canal_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fecha_actualizacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "auditoria_perfil",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campo", sa.String(length=60), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_nuevo", sa.Text(), nullable=True),
        sa.Column("realizado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip", sa.String(length=50), nullable=True),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["realizado_por"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_auditoria_usuario", "auditoria_perfil", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("idx_auditoria_usuario", table_name="auditoria_perfil")
    op.drop_table("auditoria_perfil")
    op.drop_table("preferencias_notificacion")

    op.drop_index("idx_solicitudes_usuario", table_name="solicitudes_cuenta")
    op.drop_table("solicitudes_cuenta")
    op.drop_index("idx_ticket_mensajes_ticket", table_name="ticket_mensajes")
    op.drop_table("ticket_mensajes")
    op.drop_index("idx_tickets_usuario", table_name="tickets_soporte")
    op.drop_table("tickets_soporte")
    op.execute("DROP SEQUENCE IF EXISTS ticket_numero_seq")

    for col in (
        "fecha_limite_postulacion", "nivel_experiencia", "horas_reconocidas",
        "otorga_certificado", "politica_cancelacion", "incluye_seguro",
        "incluye_alimentacion", "incluye_transporte", "recomendaciones",
        "que_llevar", "perfil_beneficiarios", "actividades_voluntario",
        "impacto_esperado", "objetivo",
    ):
        op.drop_column("publicaciones", col)

    for col in (
        "actividades_completadas", "horas_acumuladas",
        "contacto_emergencia_telefono", "contacto_emergencia_nombre",
        "preferencia_modalidad", "idiomas", "profesion", "nivel_educativo",
        "telefono_contacto", "descripcion", "direccion",
    ):
        op.drop_column("voluntarios", col)

    # Los valores añadidos a los ENUM nativos no se eliminan (PostgreSQL no
    # soporta DROP VALUE). Es inocuo dejarlos.

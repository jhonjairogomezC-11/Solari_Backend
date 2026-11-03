"""Aditivo: token_hash en tablas de tokens + tablas legales (Fase 1).

Revision ID: 0001_aditivo
Revises:
Create Date: 2026-10-24

Esta migración es ESTRICTAMENTE ADITIVA y REVERSIBLE:
- Añade columnas nullable `token_hash` a las tablas de tokens existentes y hace
  nullable la columna `token` para que Python pueda no escribirla (compat Laravel).
- Añade `intentos` a `recuperacion_password`.
- Crea tablas legales nuevas que Laravel no usa.
No se elimina ni modifica ningún dato existente.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_aditivo"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── token_hash aditivo en tablas de tokens ──
    for tabla in ("refresh_tokens", "recuperacion_password", "verificacion_email"):
        op.add_column(tabla, sa.Column("token_hash", sa.String(length=64), nullable=True))
        op.create_index(f"idx_{tabla}_token_hash", tabla, ["token_hash"])
        # El token en claro deja de ser obligatorio (Python guarda solo el hash).
        op.alter_column(tabla, "token", existing_type=sa.Text(), nullable=True)

    op.add_column(
        "recuperacion_password",
        sa.Column("intentos", sa.Integer(), nullable=True, server_default="0"),
    )

    # ── Tablas legales nuevas ──
    op.create_table(
        "documentos_legales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "requerido_registro",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "fecha_creacion",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("codigo", name="uq_documentos_legales_codigo"),
    )

    op.create_table(
        "documento_legal_versiones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=True),
        sa.Column("contenido_hash", sa.String(length=64), nullable=True),
        sa.Column("url_publica", sa.String(length=500), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "fecha_publicacion",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"], ["documentos_legales.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("documento_id", "version", name="uq_doc_version"),
    )
    op.create_index(
        "idx_doc_version_vigente",
        "documento_legal_versiones",
        ["documento_id", "vigente"],
    )

    op.create_table(
        "usuario_aceptaciones_legales",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("aceptado", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ip_aceptacion", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "fecha_aceptacion",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["version_id"], ["documento_legal_versiones.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "idx_aceptacion_usuario", "usuario_aceptaciones_legales", ["usuario_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_aceptacion_usuario", table_name="usuario_aceptaciones_legales")
    op.drop_table("usuario_aceptaciones_legales")
    op.drop_index("idx_doc_version_vigente", table_name="documento_legal_versiones")
    op.drop_table("documento_legal_versiones")
    op.drop_table("documentos_legales")

    op.drop_column("recuperacion_password", "intentos")
    for tabla in ("refresh_tokens", "recuperacion_password", "verificacion_email"):
        op.drop_index(f"idx_{tabla}_token_hash", table_name=tabla)
        op.drop_column(tabla, "token_hash")

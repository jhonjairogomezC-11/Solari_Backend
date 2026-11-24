"""Aditivo: seguridad de cuenta (sesiones activas y verificación en dos pasos).

- refresh_tokens: fecha_ultimo_uso y fecha_inicio_sesion (nullable). `ip_solicitud`
  y `user_agent` ya existían; se reutilizan.
- usuarios: mfa_secret (cifrado con Fernet), mfa_activo, mfa_codigos_respaldo
  (hashes SHA-256 de códigos de un solo uso, JSON) y mfa_ultimo_paso (anti-replay).

Todas las columnas son nullable o tienen default, por lo que Laravel no se ve afectado.

Revision ID: 0006_seguridad
Revises: 0005_mensajes
Create Date: 2026-11-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_seguridad"
down_revision: str | None = "0005_mensajes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens", sa.Column("fecha_ultimo_uso", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "refresh_tokens", sa.Column("fecha_inicio_sesion", sa.DateTime(), nullable=True)
    )
    op.create_index(
        "idx_refresh_tokens_usuario_activos",
        "refresh_tokens",
        ["usuario_id", "usado"],
        if_not_exists=True,
    )

    op.add_column("usuarios", sa.Column("mfa_secret", sa.Text(), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column("mfa_activo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "usuarios",
        sa.Column("mfa_codigos_respaldo", postgresql.JSONB(), nullable=True),
    )
    op.add_column("usuarios", sa.Column("mfa_ultimo_paso", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "mfa_ultimo_paso")
    op.drop_column("usuarios", "mfa_codigos_respaldo")
    op.drop_column("usuarios", "mfa_activo")
    op.drop_column("usuarios", "mfa_secret")
    op.drop_index(
        "idx_refresh_tokens_usuario_activos", table_name="refresh_tokens", if_exists=True
    )
    op.drop_column("refresh_tokens", "fecha_inicio_sesion")
    op.drop_column("refresh_tokens", "fecha_ultimo_uso")

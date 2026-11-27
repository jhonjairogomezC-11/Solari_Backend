"""Agrega motivo_rechazo_documento a voluntarios.

Revision ID: 0008_rechazo_doc
Revises: 0007_menores
Create Date: 2026-11-27
"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision: str = "0008_rechazo_doc"
down_revision: str | None = "0007_menores"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "voluntarios",
        sa.Column("motivo_rechazo_documento", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voluntarios", "motivo_rechazo_documento")

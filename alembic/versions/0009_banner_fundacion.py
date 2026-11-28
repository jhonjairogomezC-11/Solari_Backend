"""Agrega imagen_banner a fundaciones.

Revision ID: 0009_banner_fundacion
Revises: 0008_rechazo_doc
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0009_banner_fundacion"
down_revision: str | None = "0008_rechazo_doc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fundaciones", sa.Column("imagen_banner", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("fundaciones", "imagen_banner")

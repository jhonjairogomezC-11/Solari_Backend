"""Tipo de notificación genérico para cambios de estado de postulación.

Revision ID: 0004_notif_post
Revises: 0003_alineacion
Create Date: 2026-11-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_notif_post"
down_revision: str | None = "0003_alineacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(
        sa.text("ALTER TYPE tipo_notificacion ADD VALUE IF NOT EXISTS 'POSTULACION_ACTUALIZADA'")
    )


def downgrade() -> None:
    # PostgreSQL no permite eliminar valores de un ENUM; es inocuo dejarlo.
    pass

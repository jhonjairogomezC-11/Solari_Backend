"""Aditivo: mensajes entre voluntario y organización dentro de una postulación.

Revision ID: 0005_mensajes
Revises: 0004_notif_post
Create Date: 2026-11-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0005_mensajes"
down_revision: str | None = "0004_notif_post"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = pg.UUID(as_uuid=True)
_NOW = sa.text("CURRENT_TIMESTAMP")
_UUID_DEF = sa.text("uuid_generate_v4()")


def upgrade() -> None:
    op.create_table(
        "mensajes_postulacion",
        sa.Column("id", _UUID, primary_key=True, server_default=_UUID_DEF),
        sa.Column(
            "postulacion_id", _UUID,
            sa.ForeignKey("postulaciones.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "autor_id", _UUID, sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("leido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fecha_creacion", sa.TIMESTAMP(), nullable=False, server_default=_NOW),
        sa.CheckConstraint("char_length(mensaje) <= 1000", name="chk_msg_post_longitud"),
    )
    op.create_index(
        "idx_msg_post_postulacion", "mensajes_postulacion", ["postulacion_id", "fecha_creacion"]
    )
    # Conteo de no leídos por destinatario.
    op.create_index(
        "idx_msg_post_no_leidos", "mensajes_postulacion", ["postulacion_id"],
        postgresql_where=sa.text("leido = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_msg_post_no_leidos", table_name="mensajes_postulacion")
    op.drop_index("idx_msg_post_postulacion", table_name="mensajes_postulacion")
    op.drop_table("mensajes_postulacion")

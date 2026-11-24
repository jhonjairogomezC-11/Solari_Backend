"""Autorización del acudiente para voluntarios menores de edad.

Revision ID: 0007_menores
Revises: 0006_seguridad
Create Date: 2026-11-23

ADITIVA. Añade a `voluntarios` los datos del acudiente y el estado de la
autorización firmada (Código de Infancia y Adolescencia y Ley 1581 de 2012), y
un valor nuevo en el enum de auditoría administrativa.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_menores"
down_revision: str | None = "0006_seguridad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNAS = (
    sa.Column("acudiente_nombre", sa.String(150), nullable=True),
    sa.Column("acudiente_documento", sa.String(30), nullable=True),
    sa.Column("acudiente_telefono", sa.String(20), nullable=True),
    sa.Column("acudiente_parentesco", sa.String(40), nullable=True),
    sa.Column("autorizacion_acudiente", sa.String(500), nullable=True),
    sa.Column("autorizacion_estado", sa.String(20), nullable=True),
    sa.Column("autorizacion_fecha", sa.DateTime(timezone=True), nullable=True),
    sa.Column("autorizacion_nota", sa.Text(), nullable=True),
)


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE se ejecuta fuera de la transacción (igual que 0003/0004).
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(
        sa.text(
            "ALTER TYPE tipo_accion_admin ADD VALUE IF NOT EXISTS 'AUTORIZACION_MENOR_RESUELTA'"
        )
    )

    for columna in _COLUMNAS:
        op.add_column("voluntarios", columna)
    op.create_check_constraint(
        "ck_voluntarios_autorizacion_estado",
        "voluntarios",
        "autorizacion_estado IS NULL OR autorizacion_estado IN "
        "('NO_REQUERIDA', 'PENDIENTE', 'APROBADA', 'RECHAZADA')",
    )
    op.create_index(
        "ix_voluntarios_autorizacion_estado",
        "voluntarios",
        ["autorizacion_estado"],
        postgresql_where=sa.text("autorizacion_estado = 'PENDIENTE'"),
    )


def downgrade() -> None:
    op.drop_index("ix_voluntarios_autorizacion_estado", table_name="voluntarios")
    op.drop_constraint("ck_voluntarios_autorizacion_estado", "voluntarios", type_="check")
    for columna in reversed(_COLUMNAS):
        op.drop_column("voluntarios", columna.name)
    # PostgreSQL no permite quitar valores de un ENUM; es inocuo dejarlo.

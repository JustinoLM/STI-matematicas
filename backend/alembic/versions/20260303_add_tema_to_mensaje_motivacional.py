"""add tema column to mensaje_motivacional

Revision ID: add_tema_to_mensaje_mot
Revises: add_mensaje_motivacional
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "add_tema_to_mensaje_mot"
down_revision = "add_mensaje_motivacional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columna tema (nullable — None = sin tema activo)
    op.add_column(
        "mensaje_motivacional",
        sa.Column("tema", sa.String(length=100), nullable=True),
    )
    # Actualizar el índice para incluir tema en la clave de caché
    op.drop_index("ix_mensaje_mot_lookup", table_name="mensaje_motivacional")
    op.create_index(
        "ix_mensaje_mot_lookup",
        "mensaje_motivacional",
        ["estudiante_id", "tipo", "fecha", "tema"],
    )


def downgrade() -> None:
    op.drop_index("ix_mensaje_mot_lookup", table_name="mensaje_motivacional")
    op.create_index(
        "ix_mensaje_mot_lookup",
        "mensaje_motivacional",
        ["estudiante_id", "tipo", "fecha"],
    )
    op.drop_column("mensaje_motivacional", "tema")

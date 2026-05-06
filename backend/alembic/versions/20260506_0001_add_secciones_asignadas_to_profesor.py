"""add secciones_asignadas to profesor

Permite asignar al profesor qué secciones/grados enseña (ej. ["6A", "6B"]).
Usado para filtrar estudiantes en la vista del profesor.

Revision ID: c2d5e6f7a8b3
Revises: b1c4d5e6f7a2
Create Date: 2026-05-06 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'c2d5e6f7a8b3'
down_revision: str = 'b1c4d5e6f7a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'profesor',
        sa.Column('secciones_asignadas', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('profesor', 'secciones_asignadas')

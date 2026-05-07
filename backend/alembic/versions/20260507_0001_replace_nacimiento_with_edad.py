"""replace anio_nacimiento + mes_nacimiento with edad in estudiante

Revision ID: d3e6f7a8b9c4
Revises: c2d5e6f7a8b3
Create Date: 2026-05-07 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'd3e6f7a8b9c4'
down_revision: str = 'c2d5e6f7a8b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('estudiante', sa.Column('edad', sa.Integer(), nullable=True))
    op.drop_column('estudiante', 'mes_nacimiento')
    op.drop_column('estudiante', 'anio_nacimiento')


def downgrade() -> None:
    op.add_column('estudiante', sa.Column('anio_nacimiento', sa.Integer(), nullable=True))
    op.add_column('estudiante', sa.Column('mes_nacimiento', sa.Integer(), nullable=True))
    op.drop_column('estudiante', 'edad')

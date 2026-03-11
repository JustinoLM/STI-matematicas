"""Add enunciado_tematico table

Revision ID: add_enunciado_tematico
Revises: add_genero_to_estudiante
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_enunciado_tematico'
down_revision = 'add_genero_to_estudiante'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'enunciado_tematico',
        sa.Column('signature', sa.String(64), nullable=False),
        sa.Column('tema', sa.String(100), nullable=False),
        sa.Column('nivel', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('signature', 'tema', 'nivel'),
    )


def downgrade() -> None:
    op.drop_table('enunciado_tematico')

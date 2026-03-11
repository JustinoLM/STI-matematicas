"""Add genero to estudiante

Revision ID: add_genero_to_estudiante
Revises: add_medalla_destacada
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_genero_to_estudiante'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear el tipo enum en PostgreSQL
    genero_enum = sa.Enum('masculino', 'femenino', name='genero')
    genero_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'estudiante',
        sa.Column(
            'genero',
            sa.Enum('masculino', 'femenino', name='genero'),
            nullable=False,
            server_default='masculino',
        ),
    )


def downgrade() -> None:
    op.drop_column('estudiante', 'genero')
    sa.Enum(name='genero').drop(op.get_bind(), checkfirst=True)

"""add_post_test

Adds:
- post_test_activo column to organizacion table
- resultado_post_test table for storing final evaluation results

Revision ID: a9f3c2d1e7b4
Revises: 43f2ee3e8af8
Create Date: 2026-04-22 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9f3c2d1e7b4'
down_revision: Union[str, None] = '43f2ee3e8af8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Organizacion: add post_test_activo ─────────────────────────────────────
    op.add_column('organizacion', sa.Column(
        'post_test_activo', sa.Boolean(), nullable=False, server_default='false'
    ))

    # ── New table: resultado_post_test ─────────────────────────────────────────
    op.create_table(
        'resultado_post_test',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('estudiante_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=True),

        sa.Column('completado', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fecha_inicio', sa.DateTime(), nullable=True),
        sa.Column('fecha_fin', sa.DateTime(), nullable=True),

        sa.Column('problemas_ids', sa.JSON(), nullable=True),

        # Resultados por operación
        sa.Column('suma_nivel1_correcto', sa.Boolean(), nullable=True),
        sa.Column('suma_nivel2_correcto', sa.Boolean(), nullable=True),
        sa.Column('suma_tiempo_total', sa.Integer(), nullable=True),

        sa.Column('resta_nivel1_correcto', sa.Boolean(), nullable=True),
        sa.Column('resta_nivel2_correcto', sa.Boolean(), nullable=True),
        sa.Column('resta_tiempo_total', sa.Integer(), nullable=True),

        sa.Column('mult_nivel1_correcto', sa.Boolean(), nullable=True),
        sa.Column('mult_nivel2_correcto', sa.Boolean(), nullable=True),
        sa.Column('mult_tiempo_total', sa.Integer(), nullable=True),

        sa.Column('div_nivel1_correcto', sa.Boolean(), nullable=True),
        sa.Column('div_nivel2_correcto', sa.Boolean(), nullable=True),
        sa.Column('div_tiempo_total', sa.Integer(), nullable=True),

        # Niveles evaluados (solo referencia)
        sa.Column('nivel_suma_evaluado', sa.Integer(), nullable=True),
        sa.Column('nivel_resta_evaluado', sa.Integer(), nullable=True),
        sa.Column('nivel_mult_evaluado', sa.Integer(), nullable=True),
        sa.Column('nivel_div_evaluado', sa.Integer(), nullable=True),

        # Snapshot del pre-test
        sa.Column('pre_nivel_suma', sa.Integer(), nullable=True),
        sa.Column('pre_nivel_resta', sa.Integer(), nullable=True),
        sa.Column('pre_nivel_mult', sa.Integer(), nullable=True),
        sa.Column('pre_nivel_div', sa.Integer(), nullable=True),
        sa.Column('pre_nivel_actual', sa.Integer(), nullable=True),

        sa.Column('total_correctos', sa.Integer(), nullable=True),
        sa.Column('perfecto', sa.Boolean(), nullable=True, server_default='false'),

        # Constraints
        sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizacion.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('estudiante_id', name='uq_resultado_post_test_estudiante'),
    )
    op.create_index(
        op.f('ix_resultado_post_test_id'), 'resultado_post_test', ['id'], unique=False
    )
    op.create_index(
        'ix_resultado_post_test_estudiante_id', 'resultado_post_test', ['estudiante_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_resultado_post_test_estudiante_id', table_name='resultado_post_test')
    op.drop_index(op.f('ix_resultado_post_test_id'), table_name='resultado_post_test')
    op.drop_table('resultado_post_test')
    op.drop_column('organizacion', 'post_test_activo')

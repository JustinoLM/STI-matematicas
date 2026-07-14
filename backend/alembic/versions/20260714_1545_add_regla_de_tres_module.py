"""add regla de tres module

Revision ID: a0e1d9df5aba
Revises: d3e6f7a8b9c4
Create Date: 2026-07-14 15:45:35.783223+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a0e1d9df5aba'
down_revision: Union[str, None] = 'd3e6f7a8b9c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'problema_regla_tres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('directa', 'inversa', name='tipoproporcion'), nullable=False),
        sa.Column('numero1', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('numero2', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('numero3', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('resultado', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('nivel_dificultad', sa.Integer(), nullable=False),
        sa.Column('cantidad_decimales', sa.Integer(), nullable=False),
        sa.Column('signature', sa.String(length=64), nullable=False),
        sa.Column('fecha_generacion', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_problema_regla_tres_id'), 'problema_regla_tres', ['id'], unique=False)
    op.create_index(op.f('ix_problema_regla_tres_nivel_dificultad'), 'problema_regla_tres', ['nivel_dificultad'], unique=False)
    op.create_index(op.f('ix_problema_regla_tres_signature'), 'problema_regla_tres', ['signature'], unique=True)
    op.create_index(op.f('ix_problema_regla_tres_tipo'), 'problema_regla_tres', ['tipo'], unique=False)

    op.create_table(
        'perfil_regla_tres',
        sa.Column('estudiante_id', sa.Integer(), nullable=False),
        sa.Column('nivel_actual', sa.Integer(), nullable=False),
        sa.Column('consecutivas_correctas', sa.Integer(), nullable=False),
        sa.Column('total_practicados', sa.Integer(), nullable=False),
        sa.Column('fecha_ultima_practica', sa.DateTime(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id']),
        sa.PrimaryKeyConstraint('estudiante_id'),
    )

    op.create_table(
        'sesion_practica_regla_tres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('estudiante_id', sa.Integer(), nullable=False),
        sa.Column('estado', postgresql.ENUM('iniciada', 'en_progreso', 'pausada', 'completada', 'abandonada', name='estadosesion', create_type=False), nullable=False),
        sa.Column('fecha_inicio', sa.DateTime(), nullable=False),
        sa.Column('fecha_fin', sa.DateTime(), nullable=True),
        sa.Column('nivel_al_iniciar', sa.Integer(), nullable=False),
        sa.Column('cantidad_problemas', sa.Integer(), nullable=False),
        sa.Column('problemas_ids', sa.JSON(), nullable=False),
        sa.Column('progreso_actual', sa.Integer(), nullable=False),
        sa.Column('problemas_correctos', sa.Integer(), nullable=False),
        sa.Column('problemas_incorrectos', sa.Integer(), nullable=False),
        sa.Column('puntos_ganados', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sesion_practica_regla_tres_estudiante_id'), 'sesion_practica_regla_tres', ['estudiante_id'], unique=False)
    op.create_index(op.f('ix_sesion_practica_regla_tres_id'), 'sesion_practica_regla_tres', ['id'], unique=False)

    op.create_table(
        'intento_regla_tres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sesion_id', sa.Integer(), nullable=False),
        sa.Column('problema_id', sa.Integer(), nullable=False),
        sa.Column('respuesta_estudiante', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('es_correcto', sa.Boolean(), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['problema_id'], ['problema_regla_tres.id']),
        sa.ForeignKeyConstraint(['sesion_id'], ['sesion_practica_regla_tres.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_intento_regla_tres_es_correcto'), 'intento_regla_tres', ['es_correcto'], unique=False)
    op.create_index(op.f('ix_intento_regla_tres_id'), 'intento_regla_tres', ['id'], unique=False)
    op.create_index(op.f('ix_intento_regla_tres_problema_id'), 'intento_regla_tres', ['problema_id'], unique=False)
    op.create_index(op.f('ix_intento_regla_tres_sesion_id'), 'intento_regla_tres', ['sesion_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_intento_regla_tres_sesion_id'), table_name='intento_regla_tres')
    op.drop_index(op.f('ix_intento_regla_tres_problema_id'), table_name='intento_regla_tres')
    op.drop_index(op.f('ix_intento_regla_tres_id'), table_name='intento_regla_tres')
    op.drop_index(op.f('ix_intento_regla_tres_es_correcto'), table_name='intento_regla_tres')
    op.drop_table('intento_regla_tres')

    op.drop_index(op.f('ix_sesion_practica_regla_tres_id'), table_name='sesion_practica_regla_tres')
    op.drop_index(op.f('ix_sesion_practica_regla_tres_estudiante_id'), table_name='sesion_practica_regla_tres')
    op.drop_table('sesion_practica_regla_tres')

    op.drop_table('perfil_regla_tres')

    op.drop_index(op.f('ix_problema_regla_tres_tipo'), table_name='problema_regla_tres')
    op.drop_index(op.f('ix_problema_regla_tres_signature'), table_name='problema_regla_tres')
    op.drop_index(op.f('ix_problema_regla_tres_nivel_dificultad'), table_name='problema_regla_tres')
    op.drop_index(op.f('ix_problema_regla_tres_id'), table_name='problema_regla_tres')
    op.drop_table('problema_regla_tres')

    op.execute('DROP TYPE IF EXISTS tipoproporcion')

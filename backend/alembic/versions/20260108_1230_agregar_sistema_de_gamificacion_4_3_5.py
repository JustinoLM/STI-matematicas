"""agregar sistema de gamificacion 4.3.5

Revision ID: 20260108_1230
Revises: 4d56aef74793
Create Date: 2026-01-08 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect, text

revision: str = '20260108_1230'
down_revision: Union[str, None] = '4d56aef74793'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    return inspect(conn).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    cols = [c['name'] for c in inspect(conn).get_columns(table_name)]
    return column_name in cols


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname = :n"), {"n": index_name}
    )
    return result.fetchone() is not None


def upgrade() -> None:

    # Agregar campo puntos_totales a estudiante
    if not _column_exists('estudiante', 'puntos_totales'):
        op.add_column('estudiante', sa.Column('puntos_totales', sa.Integer(), nullable=False, server_default='0'))

    # Agregar campos a sesion_practica
    if not _column_exists('sesion_practica', 'puntos_ganados'):
        op.add_column('sesion_practica', sa.Column('puntos_ganados', sa.Integer(), nullable=True, server_default='0'))
    if not _column_exists('sesion_practica', 'desglose_puntos'):
        op.add_column('sesion_practica', sa.Column('desglose_puntos', sa.JSON(), nullable=True))

    # Agregar campos a problema
    if not _column_exists('problema', 'enunciado_tematico'):
        op.add_column('problema', sa.Column('enunciado_tematico', sa.Text(), nullable=True))
    if not _column_exists('problema', 'tema'):
        op.add_column('problema', sa.Column('tema', sa.String(length=50), nullable=True))

    # Crear tabla desbloqueable
    if not _table_exists('desbloqueable'):
        op.create_table(
            'desbloqueable',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('categoria', sa.Enum('tema', 'fondo', 'color', 'musica', 'efecto', name='categoriadesbloqueable'), nullable=False),
            sa.Column('nombre', sa.String(length=100), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('precio_puntos', sa.Integer(), nullable=False),
            sa.Column('nivel_minimo_requerido', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('archivo_referencia', sa.String(length=255), nullable=True),
            sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('es_tema_inicial', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
            sa.PrimaryKeyConstraint('id')
        )
    if not _index_exists('ix_desbloqueable_id'):
        op.create_index(op.f('ix_desbloqueable_id'), 'desbloqueable', ['id'], unique=False)

    # Crear tabla estudiante_desbloqueable
    if not _table_exists('estudiante_desbloqueable'):
        op.create_table(
            'estudiante_desbloqueable',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('estudiante_id', sa.Integer(), nullable=False),
            sa.Column('desbloqueable_id', sa.Integer(), nullable=False),
            sa.Column('fecha_compra', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('puntos_gastados', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['desbloqueable_id'], ['desbloqueable.id'], ),
            sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    if not _index_exists('ix_estudiante_desbloqueable_id'):
        op.create_index(op.f('ix_estudiante_desbloqueable_id'), 'estudiante_desbloqueable', ['id'], unique=False)

    # Crear tabla personalizacion_estudiante
    if not _table_exists('personalizacion_estudiante'):
        op.create_table(
            'personalizacion_estudiante',
            sa.Column('estudiante_id', sa.Integer(), nullable=False),
            sa.Column('tema_activo_id', sa.Integer(), nullable=True),
            sa.Column('fondo_activo_id', sa.Integer(), nullable=True),
            sa.Column('musica_activa_id', sa.Integer(), nullable=True),
            sa.Column('color_fondo', sa.String(length=7), nullable=False, server_default='#FFFFFF'),
            sa.Column('color_texto', sa.String(length=7), nullable=False, server_default='#000000'),
            sa.Column('color_botones', sa.String(length=7), nullable=False, server_default='#007AFF'),
            sa.Column('efectos_activos', sa.JSON(), nullable=True),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id'], ),
            sa.ForeignKeyConstraint(['fondo_activo_id'], ['desbloqueable.id'], ),
            sa.ForeignKeyConstraint(['musica_activa_id'], ['desbloqueable.id'], ),
            sa.ForeignKeyConstraint(['tema_activo_id'], ['desbloqueable.id'], ),
            sa.PrimaryKeyConstraint('estudiante_id')
        )

    # Crear tabla medalla
    if not _table_exists('medalla'):
        op.create_table(
            'medalla',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=100), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=False),
            sa.Column('categoria', sa.Enum('aprendizaje', 'volumen', 'exploracion', 'desafios', name='categoriamedalla'), nullable=False),
            sa.Column('criterio', sa.JSON(), nullable=False),
            sa.Column('imagen_url', sa.String(length=255), nullable=True),
            sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('activa', sa.Boolean(), nullable=False, server_default='true'),
            sa.PrimaryKeyConstraint('id')
        )
    if not _index_exists('ix_medalla_id'):
        op.create_index(op.f('ix_medalla_id'), 'medalla', ['id'], unique=False)

    # Crear tabla estudiante_medalla
    if not _table_exists('estudiante_medalla'):
        op.create_table(
            'estudiante_medalla',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('estudiante_id', sa.Integer(), nullable=False),
            sa.Column('medalla_id', sa.Integer(), nullable=False),
            sa.Column('fecha_obtencion', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('notificada', sa.Boolean(), nullable=False, server_default='false'),
            sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id'], ),
            sa.ForeignKeyConstraint(['medalla_id'], ['medalla.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    if not _index_exists('ix_estudiante_medalla_id'):
        op.create_index(op.f('ix_estudiante_medalla_id'), 'estudiante_medalla', ['id'], unique=False)

    # Crear tabla transaccion_puntos
    if not _table_exists('transaccion_puntos'):
        op.create_table(
            'transaccion_puntos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('estudiante_id', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.Enum('ganancia', 'gasto', name='tipotransaccion'), nullable=False),
            sa.Column('cantidad', sa.Integer(), nullable=False),
            sa.Column('concepto', sa.String(length=255), nullable=False),
            sa.Column('sesion_id', sa.Integer(), nullable=True),
            sa.Column('desbloqueable_id', sa.Integer(), nullable=True),
            sa.Column('saldo_resultante', sa.Integer(), nullable=False),
            sa.Column('fecha', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['desbloqueable_id'], ['desbloqueable.id'], ),
            sa.ForeignKeyConstraint(['estudiante_id'], ['estudiante.id'], ),
            sa.ForeignKeyConstraint(['sesion_id'], ['sesion_practica.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    if not _index_exists('ix_transaccion_puntos_id'):
        op.create_index(op.f('ix_transaccion_puntos_id'), 'transaccion_puntos', ['id'], unique=False)
    if not _index_exists('ix_transaccion_puntos_fecha'):
        op.create_index(op.f('ix_transaccion_puntos_fecha'), 'transaccion_puntos', ['fecha'], unique=False)


def downgrade() -> None:
    # Eliminar tablas en orden inverso
    op.drop_index(op.f('ix_transaccion_puntos_fecha'), table_name='transaccion_puntos')
    op.drop_index(op.f('ix_transaccion_puntos_id'), table_name='transaccion_puntos')
    op.drop_table('transaccion_puntos')
    
    op.drop_index(op.f('ix_estudiante_medalla_id'), table_name='estudiante_medalla')
    op.drop_table('estudiante_medalla')
    
    op.drop_index(op.f('ix_medalla_id'), table_name='medalla')
    op.drop_table('medalla')
    
    op.drop_table('personalizacion_estudiante')
    
    op.drop_index(op.f('ix_estudiante_desbloqueable_id'), table_name='estudiante_desbloqueable')
    op.drop_table('estudiante_desbloqueable')
    
    op.drop_index(op.f('ix_desbloqueable_id'), table_name='desbloqueable')
    op.drop_table('desbloqueable')
    
    op.drop_column('problema', 'tema')
    op.drop_column('problema', 'enunciado_tematico')
    op.drop_column('sesion_practica', 'desglose_puntos')
    op.drop_column('sesion_practica', 'puntos_ganados')
    op.drop_column('estudiante', 'puntos_totales')
    
    op.execute('DROP TYPE IF EXISTS tipotransaccion')
    op.execute('DROP TYPE IF EXISTS categoriamedalla')
    op.execute('DROP TYPE IF EXISTS categoriadesbloqueable')

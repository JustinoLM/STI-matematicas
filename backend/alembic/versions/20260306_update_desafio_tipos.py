"""Actualiza desafios: nuevos tipos, parametro_adicional, recompensa_puntos, puntos_otorgados

Revision ID: 20260306_update_desafio_tipos
Revises: add_animacion_guardada
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa

revision = "20260306_update_desafio_tipos"
down_revision = "add_animacion_guardada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # desafio_grupal: parámetro secundario (max errores / seg / min) y recompensa en puntos
    op.add_column("desafio_grupal", sa.Column("parametro_adicional", sa.Integer(), nullable=True))
    op.add_column("desafio_grupal", sa.Column("recompensa_puntos", sa.Integer(), nullable=True))

    # grupo_desafio: flag para no otorgar XP más de una vez por grupo
    op.add_column("grupo_desafio", sa.Column("puntos_otorgados", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("grupo_desafio", "puntos_otorgados")
    op.drop_column("desafio_grupal", "recompensa_puntos")
    op.drop_column("desafio_grupal", "parametro_adicional")

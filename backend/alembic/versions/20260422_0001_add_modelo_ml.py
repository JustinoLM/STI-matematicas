"""add_modelo_ml

Adds modelo_ml table for persisting trained ML models (KMeans, LogisticRegression)
as binary blobs in PostgreSQL, replacing ephemeral filesystem storage.

Revision ID: b1c4d5e6f7a2
Revises: a9f3c2d1e7b4
Create Date: 2026-04-22 00:01:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c4d5e6f7a2'
down_revision: Union[str, None] = 'a9f3c2d1e7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'modelo_ml',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('modelo_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('scaler_bytes', sa.LargeBinary(), nullable=True),
        sa.Column('entrenado_en', sa.DateTime(), nullable=False),
        sa.Column('perfiles_entrenados', sa.Integer(), nullable=True),

        sa.ForeignKeyConstraint(
            ['org_id'], ['organizacion.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre', 'org_id', name='uq_modelo_ml_nombre_org'),
    )
    op.create_index(
        op.f('ix_modelo_ml_id'), 'modelo_ml', ['id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_modelo_ml_id'), table_name='modelo_ml')
    op.drop_table('modelo_ml')

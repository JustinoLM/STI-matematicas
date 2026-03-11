"""add configuracion_sistema

Revision ID: b3b45a3b71b6
Revises: 20260306_update_desafio_tipos
Create Date: 2026-03-06 10:06:18.798632+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3b45a3b71b6'
down_revision: Union[str, None] = '20260306_update_desafio_tipos'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'configuracion_sistema',
        sa.Column('clave', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.String(length=500), nullable=True),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('clave'),
    )


def downgrade() -> None:
    op.drop_table('configuracion_sistema')

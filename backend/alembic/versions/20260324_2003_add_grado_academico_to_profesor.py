"""add_grado_academico_to_profesor

Revision ID: 43f2ee3e8af8
Revises: 5cf91b327b59
Create Date: 2026-03-24 20:03:19.946449+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '43f2ee3e8af8'
down_revision: Union[str, None] = '5cf91b327b59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('profesor', sa.Column('grado_academico', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('profesor', 'grado_academico')

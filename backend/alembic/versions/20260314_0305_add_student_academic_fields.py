"""add_student_academic_fields

Revision ID: a97cf0d870eb
Revises: b3b45a3b71b6
Create Date: 2026-03-14 03:05:18.263186+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a97cf0d870eb'
down_revision: Union[str, None] = 'b3b45a3b71b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiante', sa.Column('grado_academico', sa.String(length=50), nullable=True))
    op.add_column('estudiante', sa.Column('anio_nacimiento', sa.Integer(), nullable=True))
    op.add_column('estudiante', sa.Column('mes_nacimiento', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('estudiante', 'mes_nacimiento')
    op.drop_column('estudiante', 'anio_nacimiento')
    op.drop_column('estudiante', 'grado_academico')

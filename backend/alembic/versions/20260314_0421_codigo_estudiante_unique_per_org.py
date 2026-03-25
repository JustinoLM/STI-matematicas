"""codigo_estudiante_unique_per_org

Revision ID: 5cf91b327b59
Revises: a97cf0d870eb
Create Date: 2026-03-14 04:21:31.041177+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5cf91b327b59'
down_revision: Union[str, None] = 'a97cf0d870eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Quitar unicidad global en codigo_estudiante
    op.drop_index(op.f('ix_estudiante_codigo_estudiante'), table_name='estudiante')
    op.create_index(op.f('ix_estudiante_codigo_estudiante'), 'estudiante', ['codigo_estudiante'], unique=False)
    # Agregar unicidad compuesta: mismo código solo puede repetirse en distintas orgs
    op.create_unique_constraint('uq_estudiante_codigo_org', 'estudiante', ['codigo_estudiante', 'organizacion_id'])


def downgrade() -> None:
    op.drop_constraint('uq_estudiante_codigo_org', 'estudiante', type_='unique')
    op.drop_index(op.f('ix_estudiante_codigo_estudiante'), table_name='estudiante')
    op.create_index(op.f('ix_estudiante_codigo_estudiante'), 'estudiante', ['codigo_estudiante'], unique=True)

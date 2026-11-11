"""organizacion.pais: valor por defecto Panamá

Cambia solo el valor por defecto de la columna (antes 'Colombia'). Las organizaciones ya
guardadas no se modifican.

Revision ID: f6c0d4e8b3a5
Revises: e5b9c3d7a2f4
Create Date: 2026-08-23 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6c0d4e8b3a5'
down_revision: Union[str, None] = 'e5b9c3d7a2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE organizacion ALTER COLUMN pais SET DEFAULT 'Panamá'")


def downgrade() -> None:
    op.execute("ALTER TABLE organizacion ALTER COLUMN pais SET DEFAULT 'Colombia'")

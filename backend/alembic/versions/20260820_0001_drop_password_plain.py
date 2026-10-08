"""drop password_plain from usuario

Elimina la columna que guardaba la contraseña en texto plano. Las contraseñas
siguen almacenadas solo como hash Argon2 (password_hash).

El downgrade recrea la columna vacía; los valores borrados no se pueden recuperar.

Revision ID: c7d2e9f4a1b8
Revises: a0e1d9df5aba
Create Date: 2026-08-20 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d2e9f4a1b8'
down_revision: Union[str, None] = 'a0e1d9df5aba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE usuario DROP COLUMN IF EXISTS password_plain")


def downgrade() -> None:
    op.add_column('usuario', sa.Column('password_plain', sa.String(length=100), nullable=True))

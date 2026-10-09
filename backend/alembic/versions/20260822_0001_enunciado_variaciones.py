"""enunciado_tematico: varias variaciones por problema

Agrega la columna `variacion` a la clave primaria de enunciado_tematico. Las filas
existentes quedan como variación 1.

Revision ID: e5b9c3d7a2f4
Revises: d4a8b2c6e1f3
Create Date: 2026-08-22 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5b9c3d7a2f4'
down_revision: Union[str, None] = 'd4a8b2c6e1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE enunciado_tematico ADD COLUMN IF NOT EXISTS variacion INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE enunciado_tematico DROP CONSTRAINT IF EXISTS enunciado_tematico_pkey")
    op.execute("ALTER TABLE enunciado_tematico ADD PRIMARY KEY (signature, tema, nivel, variacion)")


def downgrade() -> None:
    # Se conserva solo la variación 1 para poder restaurar la clave anterior
    op.execute("DELETE FROM enunciado_tematico WHERE variacion <> 1")
    op.execute("ALTER TABLE enunciado_tematico DROP CONSTRAINT IF EXISTS enunciado_tematico_pkey")
    op.execute("ALTER TABLE enunciado_tematico ADD PRIMARY KEY (signature, tema, nivel)")
    op.execute("ALTER TABLE enunciado_tematico DROP COLUMN IF EXISTS variacion")

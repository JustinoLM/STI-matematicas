"""medallas del núcleo

Fase 7b del rediseño modular (docs/DISENO_MODULAR.md, sección "Motivación"). Solo agrega una tabla.
El nivel de jugador no necesita columnas: sale de la suma de nucleo_experiencia.

- nucleo_medalla: medallas ganadas por lección, por unidad y por hito del camino (bronce, plata,
  oro). Se ganan una sola vez.

Revision ID: b5d2f8a3c7e1
Revises: a9c4e1f7b2d5
Create Date: 2026-11-16 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b5d2f8a3c7e1'
down_revision: Union[str, None] = 'a9c4e1f7b2d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nucleo_medalla",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False, index=True),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("clave", sa.String(80), nullable=False),
        sa.Column("grado_medalla", sa.String(10), nullable=False, server_default=""),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("vista", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("estudiante_id", "tipo", "clave", "grado_medalla", name="uq_nucleo_medalla"),
        sa.CheckConstraint("tipo IN ('leccion', 'unidad', 'camino')", name="ck_nucleo_medalla_tipo"),
        sa.CheckConstraint("grado_medalla IN ('', 'bronce', 'plata', 'oro')", name="ck_nucleo_medalla_grado"),
    )


def downgrade() -> None:
    op.drop_table("nucleo_medalla")

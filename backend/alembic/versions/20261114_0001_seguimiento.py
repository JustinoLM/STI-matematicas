"""seguimiento del profesor: plan por trimestre, alertas ocultas y ajuste manual

Fase 6b del rediseño modular (docs/DISENO_MODULAR.md).

- nucleo_plan_trimestre: en qué trimestres del año lectivo se habilita cada lección (opcional).
- nucleo_habilitacion.ajuste_manual: el profesor la habilitó o deshabilitó a mano; el plan ya no
  la toca hasta que la devuelva al plan.
- nucleo_alerta_oculta: las alertas del núcleo se calculan al vuelo; aquí solo se guarda lo que el
  profesor ocultó. Las alertas de decimales (alerta_estudiante) no cambian.

Revision ID: f3b8d2e6a4c1
Revises: e7a2c4b9d1f3
Create Date: 2026-11-14 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3b8d2e6a4c1'
down_revision: Union[str, None] = 'e7a2c4b9d1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nucleo_habilitacion",
                  sa.Column("ajuste_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_table(
        "nucleo_plan_trimestre",
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), primary_key=True),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.Column("trimestre", sa.Integer(), primary_key=True),
        sa.CheckConstraint("trimestre BETWEEN 1 AND 3", name="ck_nucleo_plan_trimestre_numero"),
    )
    op.create_table(
        "nucleo_alerta_oculta",
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), primary_key=True),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.Column("tipo", sa.String(15), primary_key=True),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.CheckConstraint("tipo IN ('dificultad', 'excelencia')", name="ck_nucleo_alerta_oculta_tipo"),
    )


def downgrade() -> None:
    op.drop_table("nucleo_alerta_oculta")
    op.drop_table("nucleo_plan_trimestre")
    op.drop_column("nucleo_habilitacion", "ajuste_manual")

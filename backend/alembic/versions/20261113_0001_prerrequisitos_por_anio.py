"""prerrequisitos editables por año lectivo

Fase 6a del rediseño modular (docs/DISENO_MODULAR.md). El profesor edita los prerrequisitos de
una lección en el año lectivo de su salón. Van en tablas aparte de curriculo_prerrequisito para
que recargar el currículo nunca pise sus cambios:

- nucleo_prerrequisito_editado marca la lección como editada en ese año (aunque quede sin
  prerrequisitos);
- nucleo_prerrequisito_anio guarda sus prerrequisitos en ese año.

Revision ID: e7a2c4b9d1f3
Revises: d5f1a9c3e7b2
Create Date: 2026-11-13 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7a2c4b9d1f3'
down_revision: Union[str, None] = 'd5f1a9c3e7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nucleo_prerrequisito_editado",
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), primary_key=True),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.Column("profesor_id", sa.Integer(), sa.ForeignKey("profesor.id"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "nucleo_prerrequisito_anio",
        sa.Column("anio_lectivo_id", sa.Integer(), primary_key=True),
        sa.Column("leccion_id", sa.String(30), primary_key=True),
        sa.Column("prerrequisito_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.ForeignKeyConstraint(
            ["anio_lectivo_id", "leccion_id"],
            ["nucleo_prerrequisito_editado.anio_lectivo_id", "nucleo_prerrequisito_editado.leccion_id"],
            ondelete="CASCADE", name="fk_nucleo_prerrequisito_anio_editado",
        ),
        sa.CheckConstraint("leccion_id <> prerrequisito_id", name="ck_nucleo_prerrequisito_anio_distinto"),
    )


def downgrade() -> None:
    op.drop_table("nucleo_prerrequisito_anio")
    op.drop_table("nucleo_prerrequisito_editado")

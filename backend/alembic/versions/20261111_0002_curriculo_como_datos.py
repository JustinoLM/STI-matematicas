"""currículo como datos: caminos, lecciones y prerrequisitos por defecto

Fase 2 del rediseño modular (docs/DISENO_MODULAR.md, sección 1 → Contenido).

Tablas nuevas, vacías: el contenido se carga desde backend/curriculo/programa_meduca.yaml con
`poetry run python scripts/cargar_curriculo.py`.
- curriculo_camino: conjunto numérico + habilidad.
- curriculo_leccion: lección del programa de MEDUCA (incluida o no en el STI).
- curriculo_leccion_camino: caminos de cada lección (puede tener varios).
- curriculo_prerrequisito: grafo de prerrequisitos por defecto.

Revision ID: c3d8e2a6f1b7
Revises: a7e3c1f9d2b4
Create Date: 2026-11-11 00:02:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d8e2a6f1b7'
down_revision: Union[str, None] = 'a7e3c1f9d2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "curriculo_camino",
        sa.Column("id", sa.String(60), primary_key=True),
        sa.Column("conjunto", sa.String(30), nullable=False),
        sa.Column("habilidad", sa.String(30), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.UniqueConstraint("conjunto", "habilidad", name="uq_curriculo_camino_conjunto_habilidad"),
    )

    op.create_table(
        "curriculo_leccion",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("grado", sa.Integer(), nullable=False),
        sa.Column("unidad_numero", sa.Integer(), nullable=False),
        sa.Column("unidad_titulo", sa.String(200), nullable=False),
        sa.Column("leccion_numero", sa.Integer(), nullable=False),
        sa.Column("leccion_titulo", sa.String(200), nullable=False),
        sa.Column("orden_programa", sa.Integer(), nullable=False),
        sa.Column("incluida", sa.Boolean(), nullable=False),
        sa.Column("motivo_exclusion", sa.Text(), nullable=True),
        sa.Column("parcial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("nota_parcial", sa.Text(), nullable=True),
        sa.Column("presentacion_especial", sa.String(30), nullable=True),
        sa.Column("cubierta_por", sa.String(40), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.UniqueConstraint("orden_programa", name="uq_curriculo_leccion_orden",
                            deferrable=True, initially="DEFERRED"),
        sa.UniqueConstraint("grado", "unidad_numero", "leccion_numero",
                            name="uq_curriculo_leccion_numeracion",
                            deferrable=True, initially="DEFERRED"),
        sa.CheckConstraint("grado BETWEEN 1 AND 6", name="ck_curriculo_leccion_grado"),
        sa.CheckConstraint("incluida OR motivo_exclusion IS NOT NULL", name="ck_curriculo_leccion_motivo"),
        sa.CheckConstraint("NOT parcial OR nota_parcial IS NOT NULL", name="ck_curriculo_leccion_parcial"),
    )
    op.create_index("ix_curriculo_leccion_grado", "curriculo_leccion", ["grado"])

    op.create_table(
        "curriculo_leccion_camino",
        sa.Column("leccion_id", sa.String(30),
                  sa.ForeignKey("curriculo_leccion.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("camino_id", sa.String(60), sa.ForeignKey("curriculo_camino.id"), primary_key=True),
    )
    op.create_index("ix_curriculo_leccion_camino_camino_id", "curriculo_leccion_camino", ["camino_id"])

    op.create_table(
        "curriculo_prerrequisito",
        sa.Column("leccion_id", sa.String(30),
                  sa.ForeignKey("curriculo_leccion.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prerrequisito_id", sa.String(30),
                  sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.CheckConstraint("leccion_id <> prerrequisito_id", name="ck_curriculo_prerrequisito_propio"),
    )
    op.create_index("ix_curriculo_prerrequisito_prerrequisito_id", "curriculo_prerrequisito",
                    ["prerrequisito_id"])


def downgrade() -> None:
    op.drop_index("ix_curriculo_prerrequisito_prerrequisito_id", table_name="curriculo_prerrequisito")
    op.drop_table("curriculo_prerrequisito")
    op.drop_index("ix_curriculo_leccion_camino_camino_id", table_name="curriculo_leccion_camino")
    op.drop_table("curriculo_leccion_camino")
    op.drop_index("ix_curriculo_leccion_grado", table_name="curriculo_leccion")
    op.drop_table("curriculo_leccion")
    op.drop_table("curriculo_camino")

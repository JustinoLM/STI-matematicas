"""diagnóstico inicial del núcleo

Fase 7a del rediseño modular (docs/DISENO_MODULAR.md). Solo agrega; no migra datos.

- nucleo_sesion.tipo: "practica" (todas las existentes) o "diagnostico".
- nucleo_problema_sesion.zona admite "diagnostico" (no cuenta para la regla de dominio).
- nucleo_diagnostico: el diagnóstico de cada estudiante, con su resultado por lección.

Revision ID: a9c4e1f7b2d5
Revises: f3b8d2e6a4c1
Create Date: 2026-11-15 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9c4e1f7b2d5'
down_revision: Union[str, None] = 'f3b8d2e6a4c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ZONAS_ANTES = "('prioridad', 'normal', 'repaso', 'extension', 'refuerzo')"
ZONAS_AHORA = "('prioridad', 'normal', 'repaso', 'extension', 'refuerzo', 'diagnostico')"


def upgrade() -> None:
    op.add_column("nucleo_sesion",
                  sa.Column("tipo", sa.String(15), nullable=False, server_default="practica"))
    op.create_check_constraint("ck_nucleo_sesion_tipo", "nucleo_sesion", "tipo IN ('practica', 'diagnostico')")
    op.drop_constraint("ck_nucleo_problema_sesion_zona", "nucleo_problema_sesion", type_="check")
    op.create_check_constraint("ck_nucleo_problema_sesion_zona", "nucleo_problema_sesion", f"zona IN {ZONAS_AHORA}")
    op.create_table(
        "nucleo_diagnostico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False, index=True),
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), nullable=False, index=True),
        sa.Column("sesion_id", sa.Integer(), sa.ForeignKey("nucleo_sesion.id"), nullable=True),
        sa.Column("estado", sa.String(15), nullable=False, server_default="pendiente"),
        sa.Column("origen", sa.String(15), nullable=False),
        sa.Column("profesor_id", sa.Integer(), sa.ForeignKey("profesor.id"), nullable=True),
        sa.Column("lecciones", sa.JSON(), nullable=True),
        sa.Column("resultado", sa.JSON(), nullable=True),
        sa.Column("motivo_fin", sa.String(20), nullable=True),
        sa.Column("problemas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tiempo_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=True),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.CheckConstraint("estado IN ('pendiente', 'en_curso', 'terminado', 'cerrado', 'cancelado')",
                           name="ck_nucleo_diagnostico_estado"),
        sa.CheckConstraint("origen IN ('automatico', 'profesor')", name="ck_nucleo_diagnostico_origen"),
    )
    op.create_index("uq_nucleo_diagnostico_abierto", "nucleo_diagnostico", ["estudiante_id"], unique=True,
                    postgresql_where=sa.text("estado IN ('pendiente', 'en_curso')"))


def downgrade() -> None:
    op.drop_index("uq_nucleo_diagnostico_abierto", table_name="nucleo_diagnostico")
    op.drop_table("nucleo_diagnostico")
    # Los problemas del diagnóstico se borran antes de restringir la zona
    op.execute("DELETE FROM nucleo_evento WHERE problema_sesion_id IN "
               "(SELECT id FROM nucleo_problema_sesion WHERE zona = 'diagnostico')")
    op.execute("DELETE FROM nucleo_intento WHERE problema_sesion_id IN "
               "(SELECT id FROM nucleo_problema_sesion WHERE zona = 'diagnostico')")
    op.execute("DELETE FROM nucleo_problema_sesion WHERE zona = 'diagnostico'")
    op.drop_constraint("ck_nucleo_problema_sesion_zona", "nucleo_problema_sesion", type_="check")
    op.create_check_constraint("ck_nucleo_problema_sesion_zona", "nucleo_problema_sesion", f"zona IN {ZONAS_ANTES}")
    op.execute("DELETE FROM nucleo_sesion WHERE tipo = 'diagnostico'")
    op.drop_constraint("ck_nucleo_sesion_tipo", "nucleo_sesion", type_="check")
    op.drop_column("nucleo_sesion", "tipo")

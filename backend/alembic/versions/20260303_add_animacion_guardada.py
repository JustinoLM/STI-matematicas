"""add animacion_guardada table

Revision ID: add_animacion_guardada
Revises: add_tema_to_mensaje_mot
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "add_animacion_guardada"
down_revision = "add_tema_to_mensaje_mot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "animacion_guardada",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("problema_id", sa.Integer(), sa.ForeignKey("problema.id"), nullable=False),
        sa.Column("operacion", sa.String(length=20), nullable=False),
        sa.Column("numero1", sa.String(length=30), nullable=False),
        sa.Column("numero2", sa.String(length=30), nullable=False),
        sa.Column("nivel_dificultad", sa.Integer(), nullable=False),
        sa.Column("guardado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estudiante_id", "problema_id", name="uq_animacion_est_problema"),
    )
    op.create_index(
        "ix_animacion_guardada_estudiante",
        "animacion_guardada",
        ["estudiante_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_animacion_guardada_estudiante", table_name="animacion_guardada")
    op.drop_table("animacion_guardada")

"""add mensaje_motivacional table

Revision ID: add_mensaje_motivacional
Revises: add_enunciado_tematico
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "add_mensaje_motivacional"
down_revision = "add_enunciado_tematico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mensaje_motivacional",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mensaje_mot_lookup",
        "mensaje_motivacional",
        ["estudiante_id", "tipo", "fecha"],
    )


def downgrade() -> None:
    op.drop_index("ix_mensaje_mot_lookup", table_name="mensaje_motivacional")
    op.drop_table("mensaje_motivacional")

"""núcleo de práctica: habilitación, asignación, dominio, sesión, intentos, eventos y experiencia

Fase 3b del rediseño modular (docs/DISENO_MODULAR.md). Tablas nuevas y vacías, todas con el
prefijo nucleo_; no se toca ninguna tabla del sistema de decimales.

Revision ID: d5f1a9c3e7b2
Revises: c3d8e2a6f1b7
Create Date: 2026-11-12 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5f1a9c3e7b2'
down_revision: Union[str, None] = 'c3d8e2a6f1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nucleo_habilitacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), nullable=False),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), nullable=False),
        sa.Column("habilitada", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("signo", sa.String(10), nullable=False, server_default="siempre"),
        sa.Column("iconos", sa.String(10), nullable=False, server_default="siempre"),
        sa.Column("pistas", sa.JSON(), nullable=False),
        sa.Column("prioritaria", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("profesor_id", sa.Integer(), sa.ForeignKey("profesor.id"), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("anio_lectivo_id", "leccion_id", name="uq_nucleo_habilitacion_anio_leccion"),
        sa.CheckConstraint("signo IN ('siempre', 'nunca', 'azar')", name="ck_nucleo_habilitacion_signo"),
        sa.CheckConstraint("iconos IN ('siempre', 'nunca', 'azar')", name="ck_nucleo_habilitacion_iconos"),
        sa.CheckConstraint("habilitada OR NOT prioritaria", name="ck_nucleo_habilitacion_prioritaria"),
    )
    op.create_index("ix_nucleo_habilitacion_anio_lectivo_id", "nucleo_habilitacion", ["anio_lectivo_id"])

    op.create_table(
        "nucleo_asignacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), nullable=False),
        sa.Column("estado", sa.String(25), nullable=False, server_default="activa"),
        sa.Column("profesor_id", sa.Integer(), sa.ForeignKey("profesor.id"), nullable=False),
        sa.Column("fecha_asignacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_cierre", sa.DateTime(), nullable=True),
        sa.CheckConstraint("estado IN ('activa', 'cerrada_por_dominio', 'cancelada')",
                           name="ck_nucleo_asignacion_estado"),
    )
    op.create_index("ix_nucleo_asignacion_anio_lectivo_id", "nucleo_asignacion", ["anio_lectivo_id"])
    op.create_index("ix_nucleo_asignacion_estudiante_id", "nucleo_asignacion", ["estudiante_id"])
    op.create_index("uq_nucleo_asignacion_activa", "nucleo_asignacion", ["estudiante_id", "leccion_id"],
                    unique=True, postgresql_where=sa.text("estado = 'activa'"))

    op.create_table(
        "nucleo_ajuste_estudiante",
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), primary_key=True),
        sa.Column("banco_forzado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "nucleo_dominio",
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), primary_key=True),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.Column("estado", sa.String(25), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=False),
        sa.Column("fecha_dominio", sa.DateTime(), nullable=True),
        sa.Column("ultima_practica", sa.DateTime(), nullable=True),
        sa.Column("repaso_desde", sa.DateTime(), nullable=True),
        sa.CheckConstraint("estado IN ('en_progreso', 'dominado', 'dominado_provisional')",
                           name="ck_nucleo_dominio_estado"),
    )
    op.create_index("ix_nucleo_dominio_leccion_id", "nucleo_dominio", ["leccion_id"])

    op.create_table(
        "nucleo_extension",
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), primary_key=True),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), primary_key=True),
        sa.Column("contar_desde", sa.DateTime(), nullable=True),
        sa.Column("pausada_hasta", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "nucleo_sesion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="activa"),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("cantidad_problemas", sa.Integer(), nullable=False),
        sa.Column("progreso", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.CheckConstraint("estado IN ('activa', 'completada', 'abandonada')", name="ck_nucleo_sesion_estado"),
        sa.CheckConstraint("progreso BETWEEN 0 AND cantidad_problemas", name="ck_nucleo_sesion_progreso"),
    )
    op.create_index("ix_nucleo_sesion_estudiante_id", "nucleo_sesion", ["estudiante_id"])
    op.create_index("ix_nucleo_sesion_anio_lectivo_id", "nucleo_sesion", ["anio_lectivo_id"])
    op.create_index("uq_nucleo_sesion_activa", "nucleo_sesion", ["estudiante_id"],
                    unique=True, postgresql_where=sa.text("estado = 'activa'"))

    op.create_table(
        "nucleo_problema_sesion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sesion_id", sa.Integer(), sa.ForeignKey("nucleo_sesion.id"), nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), nullable=False),
        sa.Column("zona", sa.String(15), nullable=False),
        sa.Column("problema", sa.JSON(), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="pendiente"),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pista_max_nivel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correcto", sa.Boolean(), nullable=True),
        sa.Column("acierto", sa.Boolean(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("sesion_id", "orden", name="uq_nucleo_problema_sesion_orden"),
        sa.CheckConstraint("zona IN ('prioridad', 'normal', 'repaso', 'extension', 'refuerzo')",
                           name="ck_nucleo_problema_sesion_zona"),
        sa.CheckConstraint("estado IN ('pendiente', 'terminado')", name="ck_nucleo_problema_sesion_estado"),
        sa.CheckConstraint("pista_max_nivel BETWEEN 0 AND 3", name="ck_nucleo_problema_sesion_pista"),
    )
    op.create_index("ix_nucleo_problema_sesion_resultados", "nucleo_problema_sesion",
                    ["estudiante_id", "leccion_id", "fecha_fin"])

    op.create_table(
        "nucleo_intento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problema_sesion_id", sa.Integer(), sa.ForeignKey("nucleo_problema_sesion.id"), nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("respuestas", sa.JSON(), nullable=False),
        sa.Column("correcto", sa.Boolean(), nullable=False),
        sa.Column("errores", sa.JSON(), nullable=False),
        sa.Column("pista_max_nivel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tiempo_ms", sa.Integer(), nullable=False),
        sa.Column("uso_voz", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("modo_respuesta", sa.String(10), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("problema_sesion_id", "numero", name="uq_nucleo_intento_numero"),
    )
    op.create_index("ix_nucleo_intento_problema_sesion_id", "nucleo_intento", ["problema_sesion_id"])
    op.create_index("ix_nucleo_intento_estudiante_id", "nucleo_intento", ["estudiante_id"])

    op.create_table(
        "nucleo_evento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("problema_sesion_id", sa.Integer(), sa.ForeignKey("nucleo_problema_sesion.id"), nullable=False),
        sa.Column("intento_id", sa.Integer(), sa.ForeignKey("nucleo_intento.id"), nullable=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("valor", sa.JSON(), nullable=True),
        sa.Column("ms", sa.Integer(), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_nucleo_evento_problema_sesion_id", "nucleo_evento", ["problema_sesion_id"])
    op.create_index("ix_nucleo_evento_intento_id", "nucleo_evento", ["intento_id"])

    op.create_table(
        "nucleo_experiencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("leccion_id", sa.String(30), sa.ForeignKey("curriculo_leccion.id"), nullable=True),
        sa.Column("problema_sesion_id", sa.Integer(), sa.ForeignKey("nucleo_problema_sesion.id"), nullable=True),
        sa.Column("primera_vez", sa.Boolean(), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.CheckConstraint("tipo IN ('practica', 'acierto', 'leccion_dominada')", name="ck_nucleo_experiencia_tipo"),
        sa.CheckConstraint("cantidad >= 0", name="ck_nucleo_experiencia_cantidad"),
    )
    op.create_index("ix_nucleo_experiencia_estudiante_id", "nucleo_experiencia", ["estudiante_id"])


def downgrade() -> None:
    op.drop_table("nucleo_experiencia")
    op.drop_table("nucleo_evento")
    op.drop_table("nucleo_intento")
    op.drop_table("nucleo_problema_sesion")
    op.drop_table("nucleo_sesion")
    op.drop_table("nucleo_extension")
    op.drop_table("nucleo_dominio")
    op.drop_table("nucleo_ajuste_estudiante")
    op.drop_table("nucleo_asignacion")
    op.drop_table("nucleo_habilitacion")

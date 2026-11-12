"""organización escolar: salón, año lectivo, matrícula y trimestres

Fase 1 del rediseño modular (docs/DISENO_MODULAR.md, sección 2 → Organización).

- Tablas nuevas: salon, anio_lectivo, matricula y trimestre.
- grupo: pasa a colgar de anio_lectivo (se quitan profesor_id y codigo_grupo).
- configuracion_practica: grupo_id → anio_lectivo_id.
- desafio_grupal: + anio_lectivo_id y estado (activo | completado | no_completado), sin la
  columna booleana completado.
- grupo_desafio: id propio y grupo_id opcional (NULL = el salón completo).
- estudiante.grado_academico y profesor.secciones_asignadas se eliminan: el grado sale del salón.

No migra datos: los grupos de hoy no dicen a qué salón ni a qué grado pertenecen. Si las
tablas afectadas tienen filas, la migración se detiene con un mensaje en vez de inventarlos.

Revision ID: a7e3c1f9d2b4
Revises: f6c0d4e8b3a5
Create Date: 2026-11-11 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7e3c1f9d2b4'
down_revision: Union[str, None] = 'f6c0d4e8b3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _exigir_tablas_vacias(tablas: list[str], motivo: str) -> None:
    conexion = op.get_bind()
    con_filas = [
        t for t in tablas
        if conexion.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {t})")).scalar()
    ]
    if con_filas:
        raise RuntimeError(
            f"{motivo} Tablas con filas: {', '.join(con_filas)}. "
            "Vacíalas (o parte de una base nueva) y vuelve a correr la migración."
        )


def upgrade() -> None:
    _exigir_tablas_vacias(
        ["grupo", "estudiante_grupo", "configuracion_practica", "desafio_grupal", "grupo_desafio"],
        "La migración a salones no convierte grupos existentes.",
    )

    # ── Tablas nuevas ────────────────────────────────────────────────────────
    op.create_table(
        "salon",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizacion_id", sa.Integer(), sa.ForeignKey("organizacion.id"), nullable=False),
        sa.Column("nombre", sa.String(50), nullable=False),
        sa.Column("grado", sa.Integer(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organizacion_id", "nombre", name="uq_salon_org_nombre"),
        sa.CheckConstraint("grado BETWEEN 1 AND 6", name="ck_salon_grado"),
    )
    op.create_index("ix_salon_id", "salon", ["id"])
    op.create_index("ix_salon_organizacion_id", "salon", ["organizacion_id"])

    op.create_table(
        "anio_lectivo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("salon_id", sa.Integer(), sa.ForeignKey("salon.id"), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("profesor_id", sa.Integer(), sa.ForeignKey("profesor.id"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activo"),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_cierre", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("salon_id", "anio", name="uq_anio_lectivo_salon_anio"),
        sa.CheckConstraint("estado IN ('activo', 'cerrado')", name="ck_anio_lectivo_estado"),
    )
    op.create_index("ix_anio_lectivo_id", "anio_lectivo", ["id"])
    op.create_index("ix_anio_lectivo_salon_id", "anio_lectivo", ["salon_id"])
    op.create_index("ix_anio_lectivo_profesor_id", "anio_lectivo", ["profesor_id"])
    op.create_index(
        "uq_anio_lectivo_activo_por_salon", "anio_lectivo", ["salon_id"],
        unique=True, postgresql_where=sa.text("estado = 'activo'"),
    )

    op.create_table(
        "matricula",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio_lectivo_id", sa.Integer(), sa.ForeignKey("anio_lectivo.id"), nullable=False),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiante.id"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activa"),
        sa.Column("fecha_ingreso", sa.DateTime(), nullable=False),
        sa.Column("fecha_salida", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("anio_lectivo_id", "estudiante_id", name="uq_matricula_anio_estudiante"),
        sa.CheckConstraint("estado IN ('activa', 'retirada', 'cerrada')", name="ck_matricula_estado"),
    )
    op.create_index("ix_matricula_id", "matricula", ["id"])
    op.create_index("ix_matricula_anio_lectivo_id", "matricula", ["anio_lectivo_id"])
    op.create_index("ix_matricula_estudiante_id", "matricula", ["estudiante_id"])
    op.create_index(
        "uq_matricula_activa_por_estudiante", "matricula", ["estudiante_id"],
        unique=True, postgresql_where=sa.text("estado = 'activa'"),
    )

    op.create_table(
        "trimestre",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizacion_id", sa.Integer(), sa.ForeignKey("organizacion.id"), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.UniqueConstraint("organizacion_id", "anio", "numero", name="uq_trimestre_org_anio_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 3", name="ck_trimestre_numero"),
        sa.CheckConstraint("fecha_inicio <= fecha_fin", name="ck_trimestre_fechas"),
    )
    op.create_index("ix_trimestre_id", "trimestre", ["id"])
    op.create_index("ix_trimestre_organizacion_id", "trimestre", ["organizacion_id"])

    # ── grupo: cuelga del año lectivo ───────────────────────────────────────
    op.drop_index("ix_grupo_codigo_grupo", table_name="grupo")
    op.drop_index("ix_grupo_profesor_id", table_name="grupo")
    op.drop_constraint("grupo_profesor_id_fkey", "grupo", type_="foreignkey")
    op.drop_column("grupo", "codigo_grupo")
    op.drop_column("grupo", "profesor_id")
    op.add_column("grupo", sa.Column("anio_lectivo_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "grupo_anio_lectivo_id_fkey", "grupo", "anio_lectivo", ["anio_lectivo_id"], ["id"]
    )
    op.create_index("ix_grupo_anio_lectivo_id", "grupo", ["anio_lectivo_id"])
    op.create_unique_constraint("uq_grupo_anio_nombre", "grupo", ["anio_lectivo_id", "nombre"])

    # ── configuracion_practica: grupo_id → anio_lectivo_id ──────────────────
    op.drop_index("ix_configuracion_practica_grupo_id", table_name="configuracion_practica")
    op.drop_constraint(
        "configuracion_practica_grupo_id_fkey", "configuracion_practica", type_="foreignkey"
    )
    op.drop_column("configuracion_practica", "grupo_id")
    op.add_column(
        "configuracion_practica", sa.Column("anio_lectivo_id", sa.Integer(), nullable=False)
    )
    op.create_foreign_key(
        "configuracion_practica_anio_lectivo_id_fkey", "configuracion_practica",
        "anio_lectivo", ["anio_lectivo_id"], ["id"],
    )
    op.create_index(
        "ix_configuracion_practica_anio_lectivo_id", "configuracion_practica", ["anio_lectivo_id"]
    )

    # ── desafio_grupal: año lectivo y estado ────────────────────────────────
    op.add_column("desafio_grupal", sa.Column("anio_lectivo_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "desafio_grupal_anio_lectivo_id_fkey", "desafio_grupal", "anio_lectivo",
        ["anio_lectivo_id"], ["id"],
    )
    op.create_index("ix_desafio_grupal_anio_lectivo_id", "desafio_grupal", ["anio_lectivo_id"])
    op.add_column(
        "desafio_grupal",
        sa.Column("estado", sa.String(20), nullable=False, server_default="activo"),
    )
    op.create_check_constraint(
        "ck_desafio_estado", "desafio_grupal",
        "estado IN ('activo', 'completado', 'no_completado')",
    )
    op.drop_column("desafio_grupal", "completado")

    # ── grupo_desafio: id propio y equipo "salón completo" ──────────────────
    op.drop_constraint("grupo_desafio_pkey", "grupo_desafio", type_="primary")
    op.add_column("grupo_desafio", sa.Column("id", sa.Integer(), sa.Identity(), nullable=False))
    op.create_primary_key("grupo_desafio_pkey", "grupo_desafio", ["id"])
    op.create_index("ix_grupo_desafio_id", "grupo_desafio", ["id"])
    op.alter_column("grupo_desafio", "grupo_id", existing_type=sa.Integer(), nullable=True)
    op.create_index("ix_grupo_desafio_desafio_id", "grupo_desafio", ["desafio_id"])
    op.create_index("ix_grupo_desafio_grupo_id", "grupo_desafio", ["grupo_id"])
    op.create_unique_constraint("uq_grupo_desafio", "grupo_desafio", ["desafio_id", "grupo_id"])
    op.create_index(
        "uq_grupo_desafio_salon_completo", "grupo_desafio", ["desafio_id"],
        unique=True, postgresql_where=sa.text("grupo_id IS NULL"),
    )

    # ── El grado sale del salón ─────────────────────────────────────────────
    op.drop_column("estudiante", "grado_academico")
    op.drop_column("profesor", "secciones_asignadas")


def downgrade() -> None:
    _exigir_tablas_vacias(
        ["salon", "anio_lectivo", "matricula", "grupo", "configuracion_practica",
         "desafio_grupal", "grupo_desafio"],
        "La reversión no convierte salones en grupos.",
    )

    op.add_column("profesor", sa.Column("secciones_asignadas", sa.JSON(), nullable=True))
    op.add_column("estudiante", sa.Column("grado_academico", sa.String(50), nullable=True))

    op.drop_index("uq_grupo_desafio_salon_completo", table_name="grupo_desafio")
    op.drop_constraint("uq_grupo_desafio", "grupo_desafio", type_="unique")
    op.drop_index("ix_grupo_desafio_grupo_id", table_name="grupo_desafio")
    op.drop_index("ix_grupo_desafio_desafio_id", table_name="grupo_desafio")
    op.alter_column("grupo_desafio", "grupo_id", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_grupo_desafio_id", table_name="grupo_desafio")
    op.drop_constraint("grupo_desafio_pkey", "grupo_desafio", type_="primary")
    op.drop_column("grupo_desafio", "id")
    op.create_primary_key("grupo_desafio_pkey", "grupo_desafio", ["desafio_id", "grupo_id"])

    op.add_column(
        "desafio_grupal",
        sa.Column("completado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_constraint("ck_desafio_estado", "desafio_grupal", type_="check")
    op.drop_column("desafio_grupal", "estado")
    op.drop_index("ix_desafio_grupal_anio_lectivo_id", table_name="desafio_grupal")
    op.drop_constraint("desafio_grupal_anio_lectivo_id_fkey", "desafio_grupal", type_="foreignkey")
    op.drop_column("desafio_grupal", "anio_lectivo_id")

    op.drop_index("ix_configuracion_practica_anio_lectivo_id", table_name="configuracion_practica")
    op.drop_constraint(
        "configuracion_practica_anio_lectivo_id_fkey", "configuracion_practica", type_="foreignkey"
    )
    op.drop_column("configuracion_practica", "anio_lectivo_id")
    op.add_column("configuracion_practica", sa.Column("grupo_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "configuracion_practica_grupo_id_fkey", "configuracion_practica", "grupo",
        ["grupo_id"], ["id"],
    )
    op.create_index("ix_configuracion_practica_grupo_id", "configuracion_practica", ["grupo_id"])

    op.drop_constraint("uq_grupo_anio_nombre", "grupo", type_="unique")
    op.drop_index("ix_grupo_anio_lectivo_id", table_name="grupo")
    op.drop_constraint("grupo_anio_lectivo_id_fkey", "grupo", type_="foreignkey")
    op.drop_column("grupo", "anio_lectivo_id")
    op.add_column("grupo", sa.Column("profesor_id", sa.Integer(), nullable=False))
    op.add_column("grupo", sa.Column("codigo_grupo", sa.String(50), nullable=False))
    op.create_foreign_key("grupo_profesor_id_fkey", "grupo", "profesor", ["profesor_id"], ["id"])
    op.create_index("ix_grupo_profesor_id", "grupo", ["profesor_id"])
    op.create_index("ix_grupo_codigo_grupo", "grupo", ["codigo_grupo"], unique=True)

    op.drop_table("trimestre")
    op.drop_table("matricula")
    op.drop_table("anio_lectivo")
    op.drop_table("salon")

"""limpieza de modelos sin uso y tema activo por sesión

- Agrega sesion_practica.tema_activo (tema narrativo con el que se generó la sesión).
- Elimina tablas que ningún flujo usa: videos educativos (video_educativo,
  video_guardado, video_temporal, video_pista), el catálogo vacío de pistas
  (pista_generica), las estadísticas diarias que nunca se escribían
  (estadistica_estudiante) y los desafíos individuales sin endpoints
  (desafio_individual, estudiante_desafio_individual) y la tabla
  categoria_desbloqueable, que ya no tiene modelo.
- Elimina perfil_estudiante.alertas_activas (nunca se escribía; las alertas viven
  en alerta_estudiante).

El downgrade restaura las dos columnas, pero no recrea las tablas eliminadas
(estaban vacías o sin uso).

Revision ID: d4a8b2c6e1f3
Revises: c7d2e9f4a1b8
Create Date: 2026-08-21 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a8b2c6e1f3'
down_revision: Union[str, None] = 'c7d2e9f4a1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLAS_ELIMINADAS = (
    # primero las que dependen de otras
    'video_guardado',
    'video_temporal',
    'video_educativo',
    'video_pista',
    'pista_generica',
    'estudiante_desafio_individual',
    'desafio_individual',
    'estadistica_estudiante',
    'categoria_desbloqueable',
)
TIPOS_ELIMINADOS = ('fuentevideo', 'tipoerror', 'tipocategoria')


def upgrade() -> None:
    op.execute("ALTER TABLE sesion_practica ADD COLUMN IF NOT EXISTS tema_activo VARCHAR(50)")
    op.execute("ALTER TABLE perfil_estudiante DROP COLUMN IF EXISTS alertas_activas")
    for tabla in TABLAS_ELIMINADAS:
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
    for tipo in TIPOS_ELIMINADOS:
        op.execute(f"DROP TYPE IF EXISTS {tipo}")


def downgrade() -> None:
    op.execute("ALTER TABLE perfil_estudiante ADD COLUMN IF NOT EXISTS alertas_activas JSON")
    op.execute("ALTER TABLE sesion_practica DROP COLUMN IF EXISTS tema_activo")

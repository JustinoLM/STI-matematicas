"""
Router de estadísticas de grupo para el panel analítico del profesor.

Expone:
  GET  /api/stats/groups/{grupo_id}              → estadísticas completas
  POST /api/stats/groups/{grupo_id}/ai-analysis  → análisis IA bajo demanda
  GET  /api/stats/salones/{anio_lectivo_id}      → estadísticas del salón completo
  POST /api/stats/salones/{anio_lectivo_id}/ai-analysis
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentTeacher
from app.core.database import get_db
from app.schemas.stats import AnalisisIAResponse, GrupoStatsResponse
from app.services.llm_service import LLMService
from app.services.stats_service import StatsService

router = APIRouter()


@router.get("/groups/{grupo_id}", response_model=GrupoStatsResponse)
async def get_estadisticas_grupo(
    grupo_id: int,
    current_teacher: CurrentTeacher,
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve estadísticas completas del grupo para el panel analítico.

    Incluye:
    - Distribución de perfiles ML (K-Means)
    - Alertas activas por tipo
    - Histograma de niveles por operación
    - Actividad del grupo (últimas 2 semanas)
    - Precisión semanal del grupo (últimas 4 semanas)
    - Datos individuales de cada estudiante con probabilidad de avance (regresión logística)
    """
    service = StatsService(db)
    stats = await service.get_grupo_stats(grupo_id, current_teacher.id)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo no encontrado o no tienes acceso a él",
        )
    return stats


@router.get("/salones/{anio_lectivo_id}", response_model=GrupoStatsResponse)
async def get_estadisticas_salon(
    anio_lectivo_id: int,
    current_teacher: CurrentTeacher,
    db: AsyncSession = Depends(get_db),
):
    """Estadísticas del salón completo (año lectivo), con los mismos datos que las de un grupo."""
    stats = await StatsService(db).get_salon_stats(anio_lectivo_id, current_teacher.id)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salón no encontrado o no tienes acceso a él",
        )
    return stats


@router.post("/salones/{anio_lectivo_id}/ai-analysis", response_model=AnalisisIAResponse)
async def analizar_salon_con_ia(
    anio_lectivo_id: int,
    current_teacher: CurrentTeacher,
    db: AsyncSession = Depends(get_db),
):
    """Análisis pedagógico del salón completo bajo demanda (DeepSeek R1, sin caché)."""
    return await StatsService(db).analizar_con_ia(
        anio_lectivo_id, current_teacher.id, LLMService(), es_salon=True
    )


@router.post("/groups/{grupo_id}/ai-analysis", response_model=AnalisisIAResponse)
async def analizar_grupo_con_ia(
    grupo_id: int,
    current_teacher: CurrentTeacher,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera análisis pedagógico del grupo bajo demanda usando DeepSeek R1.

    - Sin caché: cada llamada genera un análisis fresco con datos actuales.
    - Incluye perfiles ML, alertas, niveles promedio y lista de estudiantes
      que necesitan atención.
    """
    llm = LLMService()
    service = StatsService(db)
    return await service.analizar_con_ia(grupo_id, current_teacher.id, llm)

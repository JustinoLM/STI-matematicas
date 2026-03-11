"""
Router para análisis post-práctica con R1.

GET /api/analisis/{sesion_id}
  → Genera (o devuelve) el análisis pedagógico de una sesión completada.
  → Solo el propio estudiante puede ver el análisis de su sesión.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.api.dependencies import (
    CurrentStudent,
    get_analisis_service,
)
from app.services.analisis_service import AnalisisService

router = APIRouter()


class AnalisisResponse(BaseModel):
    sesion_id: int
    texto: str
    generada_llm: bool


@router.get("/{sesion_id}", response_model=AnalisisResponse)
async def obtener_analisis_sesion(
    sesion_id: int,
    current_student: CurrentStudent,
    analisis_service: AnalisisService = Depends(get_analisis_service),
) -> AnalisisResponse:
    """
    Genera un análisis pedagógico personalizado de la sesión indicada.

    Usa DeepSeek R1 (razonamiento) para producir retroalimentación adaptada
    al rendimiento del estudiante en esa sesión.
    """
    texto, generada_llm = await analisis_service.generar_analisis(
        sesion_id=sesion_id,
        estudiante=current_student,
    )
    return AnalisisResponse(
        sesion_id=sesion_id,
        texto=texto,
        generada_llm=generada_llm,
    )

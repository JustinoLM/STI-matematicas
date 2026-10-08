"""
Router de pistas.

Endpoints:
- POST /hints/request - Solicitar pista
- GET /hints/available - Ver pistas disponibles
"""

from fastapi import APIRouter

from app.api.dependencies import CurrentStudent, HintsServiceDep
from app.schemas.hints import PistaResponse, SolicitarPistaRequest

router = APIRouter()


@router.post("/hints/request", response_model=PistaResponse)
async def solicitar_pista(
    request: SolicitarPistaRequest,
    current_student: CurrentStudent,
    hints_service: HintsServiceDep
):
    """
    Solicita una pista para un problema.
    
    Niveles:
    - 1: Estrategia general (GRATIS)
    - 2: Guía paso a paso (GRATIS)
    - 3: Casi la respuesta (10 puntos)
    
    La pista nivel 3 se genera con LLM personalizada al error del estudiante.
    """
    return await hints_service.solicitar_pista(
        estudiante_id=current_student.id,
        sesion_id=request.sesion_id,
        problema_id=request.problema_id,
        nivel_pista=request.nivel_pista
    )


@router.get("/hints/available")
async def get_pistas_disponibles(
    sesion_id: int,
    problema_id: int,
    current_student: CurrentStudent,
    hints_service: HintsServiceDep
):
    """
    Obtiene información sobre qué pistas están disponibles.
    
    Útil para el frontend para mostrar botones habilitados/deshabilitados.
    """
    return await hints_service.get_pistas_disponibles(
        estudiante_id=current_student.id,
        sesion_id=sesion_id,
        problema_id=problema_id
    )

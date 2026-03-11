"""
Router para enunciados narrativos temáticos.

Endpoints:
- POST /enunciados/lote  — Obtener enunciados para una sesión completa
"""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import CurrentStudent, EnunciadosServiceDep


router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────


class EnunciadosLoteRequest(BaseModel):
    """Request para obtener enunciados de una sesión completa."""

    problema_ids: List[int]
    tema: str  # Nombre del tema activo, ej. "Piratas", "Astronautas"


class EnunciadosLoteResponse(BaseModel):
    """Response con enunciados por problema_id."""

    enunciados: Dict[int, str]  # {problema_id: texto_narrativo}


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/lote", response_model=EnunciadosLoteResponse)
async def obtener_enunciados_lote(
    request: EnunciadosLoteRequest,
    current_student: CurrentStudent,
    enunciados_service: EnunciadosServiceDep,
):
    """
    Obtiene enunciados narrativos temáticos para múltiples problemas.

    Llamar al inicio de cada sesión de práctica con todos los problema_ids
    y el tema activo del estudiante.

    - Los hits de caché se devuelven instantáneamente.
    - Los miss generan texto con DeepSeek V3 (puede tardar unos segundos).
    - Si tema está vacío, retorna dict vacío (frontend usa pregunta genérica).
    - Los errores individuales son silenciosos; el problema simplemente
      no aparece en el resultado (frontend usa fallback).
    """
    if not request.tema or not request.problema_ids:
        return EnunciadosLoteResponse(enunciados={})

    enunciados = await enunciados_service.obtener_enunciados_lote(
        problema_ids=request.problema_ids,
        tema_nombre=request.tema,
    )

    return EnunciadosLoteResponse(enunciados=enunciados)

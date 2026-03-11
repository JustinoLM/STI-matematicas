"""
Router para mensajes motivacionales personalizados.

GET /api/mensajes/{tipo}  — Obtiene mensaje del dashboard o progreso
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import (
    CurrentStudent,
    get_mensajes_service,
    get_adaptive_service,
    get_gamification_service,
)
from app.services.mensajes_service import MensajesService
from app.services.adaptive_service import AdaptiveService
from app.services.gamification_service import GamificationService

router = APIRouter()


class MensajeResponse(BaseModel):
    tipo: str
    texto: str
    generada_llm: bool


def _normalizar_tema(nombre: Optional[str]) -> Optional[str]:
    """Normaliza el nombre del tema al formato de clave usado en _TEMAS_CONFIG."""
    if not nombre:
        return None
    return f"tema-{nombre.lower().strip()}"


@router.get("/{tipo}", response_model=MensajeResponse)
async def obtener_mensaje_motivacional(
    tipo: str,
    current_student: CurrentStudent,
    mensajes_service: MensajesService = Depends(get_mensajes_service),
    adaptive_service: AdaptiveService = Depends(get_adaptive_service),
    gamification_service: GamificationService = Depends(get_gamification_service),
):
    """
    Obtiene mensaje motivacional personalizado para el estudiante.

    - tipo="dashboard": mensaje de bienvenida para el panel principal
    - tipo="progreso":  mensaje motivador para la página de progreso

    Si el estudiante tiene un tema activo (piratas, astronautas, etc.),
    el mensaje se adapta al universo narrativo de ese tema.

    La respuesta viene de caché (instantáneo) o se genera con DeepSeek V3.
    """
    if tipo not in ("dashboard", "progreso"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo debe ser 'dashboard' o 'progreso'",
        )

    # Obtener nivel general del estudiante para el contexto del LLM
    nivel_general = 1
    try:
        perfil = await adaptive_service.get_perfil(current_student.id)
        nivel_general = getattr(perfil, "nivel_actual", 1) or 1
    except Exception:
        pass

    # Obtener tema activo del estudiante
    tema: Optional[str] = None
    try:
        personalizacion = await gamification_service.get_personalizacion(
            current_student.id
        )
        tema_nombre = getattr(personalizacion, "tema_activo_nombre", None)
        tema = _normalizar_tema(tema_nombre)
    except Exception:
        pass  # Sin tema activo — mensaje genérico

    texto, generada_llm = await mensajes_service.obtener_mensaje(
        estudiante=current_student,
        tipo=tipo,
        nivel_general=nivel_general,
        tema=tema,
    )

    return MensajeResponse(tipo=tipo, texto=texto, generada_llm=generada_llm)

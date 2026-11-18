"""
Router para mensajes motivacionales personalizados.

GET /api/mensajes/{tipo}  — Obtiene mensaje del dashboard o progreso

En 1.º y 2.º (fase 7b) no se usa DeepSeek: el mensaje es uno de unos pocos textos fijos, cortos y
fáciles de leer (o de escuchar), que cambia cada día.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import (
    CurrentStudent,
    DBSession,
    get_adaptive_service,
    get_gamification_service,
    get_mensajes_service,
)
from app.services.adaptive_service import AdaptiveService
from app.services.gamification_service import GamificationService
from app.services.mensajes_service import MensajesService

router = APIRouter()

GRADO_MAXIMO_SIN_LLM = 2
MENSAJES_FIJOS = (
    "¡Hola! Hoy vamos a practicar juntos.",
    "¡Qué bueno verte! Cada problema te hace más fuerte.",
    "¡Tú puedes! Vamos paso a paso.",
    "¡Bienvenido de vuelta! Sigamos aprendiendo.",
    "Equivocarse también es aprender. ¡Vamos!",
)


def mensaje_fijo(estudiante_id: int, tipo: str) -> str:
    from app.core.tiempo import hoy_local

    k = (hoy_local().toordinal() + estudiante_id + (0 if tipo == "dashboard" else 2)) % len(MENSAJES_FIJOS)
    return MENSAJES_FIJOS[k]


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
    db: DBSession,
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

    # 1.º y 2.º: sin DeepSeek
    from app.nucleo.servicios.motivacion import ServicioMotivacion

    grado = await ServicioMotivacion(db).grado(current_student.id)
    if grado is not None and grado <= GRADO_MAXIMO_SIN_LLM:
        return MensajeResponse(tipo=tipo, texto=mensaje_fijo(current_student.id, tipo), generada_llm=False)

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

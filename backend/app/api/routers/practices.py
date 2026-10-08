"""
Router para gestión de prácticas e intentos.

Endpoints:
- GET /active - Obtener sesión activa
- POST /{id}/pause - Pausar sesión
- POST /{id}/resume - Reanudar sesión
- POST /{id}/abandon - Abandonar sesión
- GET /{id}/progress - Progreso actual
- POST /{id}/submit-problem - Enviar respuesta
- GET /history - Historial de sesiones
- GET /{id}/summary - Resumen detallado
- GET /stats - Estadísticas globales
- GET /suspicious - Alertas de actividad sospechosa
"""

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentStudent, PracticeServiceDep
from app.schemas.practice import (
    GlobalStatsResponse,
    NextProblemResponse,
    SessionHistoryResponse,
    SessionProgressResponse,
    SessionSummaryResponse,
    SubmitProblemRequest,
    SubmitProblemResponse,
    SuspiciousActivityResponse,
)

router = APIRouter()


# ============================================
# Gestión de Sesiones Activas
# ============================================

@router.get("/active")
async def get_active_session(
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Obtiene la sesión activa del estudiante.
    
    Retorna:
    - Sesión activa si existe (iniciada, en_progreso o pausada)
    - null si no hay sesión activa
    
    Automáticamente marca como abandonadas las sesiones pausadas >4 horas.
    """
    sesion, _ = await practice_service.get_or_create_active_session(current_student.id)
    
    if not sesion:
        return {
            "tiene_sesion_activa": False,
            "sesion": None
        }
    
    return {
        "tiene_sesion_activa": True,
        "sesion": {
            "sesion_id": sesion.id,
            "estado": sesion.estado.value,
            "progreso_actual": sesion.progreso_actual,
            "total_problemas": sesion.cantidad_problemas,
            "fecha_inicio": sesion.fecha_inicio,
            "puede_reanudar": sesion.estado.value == "pausada"
        }
    }


@router.post("/{sesion_id}/pause")
async def pause_session(
    sesion_id: int,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Pausa una sesión activa.
    
    La sesión puede reanudarse dentro de las próximas 4 horas.
    Después de 4 horas, se marca automáticamente como abandonada.
    """
    return await practice_service.pause_session(sesion_id, current_student.id)


@router.post("/{sesion_id}/resume", response_model=NextProblemResponse)
async def resume_session(
    sesion_id: int,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Reanuda una sesión pausada.
    
    Retorna el siguiente problema a resolver.
    
    Error 410 si la sesión expiró (>4 horas pausada).
    """
    return await practice_service.resume_session(sesion_id, current_student.id)


@router.post("/{sesion_id}/abandon")
async def abandon_session(
    sesion_id: int,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Abandona una sesión permanentemente.
    
    - No se pueden reanudar sesiones abandonadas
    - No se ajustan niveles
    - El estudiante debe iniciar una nueva práctica
    """
    return await practice_service.abandon_session(sesion_id, current_student.id)


# ============================================
# Progreso y Resolución de Problemas
# ============================================

@router.get("/{sesion_id}/progress", response_model=SessionProgressResponse)
async def get_session_progress(
    sesion_id: int,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Obtiene el progreso actual de una sesión.
    
    Incluye:
    - Total de problemas
    - Problemas resueltos
    - Correctos/incorrectos
    - Tiempo transcurrido
    - Porcentaje de avance
    """
    return await practice_service.get_session_progress(sesion_id, current_student.id)


@router.post("/{sesion_id}/submit-problem", response_model=SubmitProblemResponse)
async def submit_problem_answer(
    sesion_id: int,
    request: SubmitProblemRequest,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Envía la respuesta de un problema.
    
    Comportamiento:
    1. Valida la respuesta
    2. Registra el intento (INSERT inmediato en BD)
    3. Verifica límite de 3 intentos por problema
    4. Si es correcto o se agotaron intentos → avanza al siguiente problema
    5. Si era el último problema → auto-completa la sesión
    
    Límite: 3 intentos por problema.
    """
    return await practice_service.submit_problem_answer(
        sesion_id=sesion_id,
        estudiante_id=current_student.id,
        problema_id=request.problema_id,
        respuesta=request.respuesta,
        tiempo_resolucion=request.tiempo_resolucion
    )


# ============================================
# Historial y Resúmenes
# ============================================

@router.get("/history", response_model=SessionHistoryResponse)
async def get_practice_history(
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep,
    limit: int = Query(20, ge=1, le=100, description="Cantidad de sesiones a retornar"),
    skip: int = Query(0, ge=0, description="Cantidad de sesiones a saltar")
):
    """
    Obtiene el historial de sesiones del estudiante.
    
    Ordenado por fecha descendente (más reciente primero).
    
    Incluye para cada sesión:
    - Fecha y duración
    - Estado (completada, abandonada, etc.)
    - Resultados (correctos, incorrectos, precisión)
    - Cambios de nivel (si hubo)
    """
    return await practice_service.get_practice_history(
        estudiante_id=current_student.id,
        limit=limit,
        skip=skip
    )


@router.get("/{sesion_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    sesion_id: int,
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Obtiene resumen detallado de una sesión específica.
    
    Incluye:
    - Métricas globales (precisión, tiempo, velocidad)
    - Desglose por operación
    - Detalle de cada problema (intentos, respuestas, tiempos)
    - Análisis de errores comunes
    - Puntos fuertes identificados
    - Recomendaciones personalizadas
    """
    return await practice_service.get_session_summary(sesion_id, current_student.id)


# ============================================
# Estadísticas Globales
# ============================================

@router.get("/stats", response_model=GlobalStatsResponse)
async def get_global_stats(
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Obtiene estadísticas globales del estudiante.
    
    Incluye:
    - Totales: sesiones, problemas resueltos, correctos
    - Promedios: precisión global, velocidad
    - Rachas: actual y mejor racha de prácticas perfectas
    - Días consecutivos practicando
    - Stats por operación
    - Progresión temporal (últimos 7 días)
    """
    return await practice_service.get_global_stats(current_student.id)


# ============================================
# Detección de Actividad Sospechosa
# ============================================

@router.get("/suspicious", response_model=SuspiciousActivityResponse)
async def get_suspicious_activity(
    current_student: CurrentStudent,
    practice_service: PracticeServiceDep
):
    """
    Obtiene alertas de actividad sospechosa del estudiante.
    
    Tipos de alertas detectadas:
    - Velocidad sospechosamente alta
    - Patrón perfecto antinatural
    - Outlier respecto al grupo
    
    Solo para uso del estudiante (ver sus propias alertas).
    Los profesores tienen endpoints separados en /api/alerts.
    """
    return await practice_service.get_suspicious_activity(current_student.id)

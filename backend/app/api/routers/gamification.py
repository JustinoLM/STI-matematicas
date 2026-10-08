"""
Router para gamificación.

Endpoints:
- GET /balance - Saldo de puntos
- GET /transactions - Historial de puntos
- GET /store - Catálogo de la tienda
- GET /store/owned - Items poseídos
- POST /store/buy/{id} - Comprar item
- GET /medals - Medallas del estudiante
- GET /medals/progress - Progreso hacia medallas
- GET /customization - Configuración actual
- PUT /customization - Actualizar configuración
- GET /themes/initial - Temas iniciales disponibles
- POST /themes/initial - Seleccionar tema inicial
- GET /session/{id}/rewards - Recompensas de sesión
"""

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentStudent, GamificationServiceDep
from app.schemas.gamification import (
    ActualizarPersonalizacionRequest,
    ComprarItemResponse,
    DesbloqueableResponse,
    HistorialPuntosResponse,
    MedallasResponse,
    PersonalizacionResponse,
    RecompensasSesionResponse,
    SaldoPuntosResponse,
    SeleccionTemaInicialRequest,
    TemasInicialesResponse,
    TiendaResponse,
)

router = APIRouter()


# ============================================
# Gestión de Puntos
# ============================================

@router.get("/balance", response_model=SaldoPuntosResponse)
async def get_saldo_puntos(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene el saldo actual de puntos del estudiante.
    """
    return await gamification_service.get_saldo(current_student.id)


@router.get("/transactions", response_model=HistorialPuntosResponse)
async def get_historial_transacciones(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep,
    limit: int = Query(50, ge=1, le=100, description="Cantidad de transacciones a retornar")
):
    """
    Obtiene el historial de transacciones de puntos.
    
    Incluye tanto ganancias como gastos, ordenadas por fecha descendente.
    """
    return await gamification_service.get_historial_transacciones(
        current_student.id,
        limit
    )


# ============================================
# Tienda
# ============================================

@router.get("/store", response_model=TiendaResponse)
async def get_tienda(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene el catálogo completo de la tienda.
    
    Incluye:
    - Todos los items disponibles
    - Marcados cuáles ya posees
    - Organizados por categoría (temas, fondos, colores, músicas, efectos)
    """
    return await gamification_service.get_tienda_completa(current_student.id)


@router.get("/store/owned", response_model=list[DesbloqueableResponse])
async def get_items_poseidos(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene solo los items que el estudiante ya posee.
    """
    return await gamification_service.get_items_poseidos(current_student.id)


@router.post("/store/buy/{desbloqueable_id}", response_model=ComprarItemResponse)
async def comprar_item(
    desbloqueable_id: int,
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Compra un item de la tienda.
    
    Validaciones:
    - El item existe y está activo
    - No lo posee ya
    - Tiene suficientes puntos
    - Tiene el nivel mínimo requerido
    
    Al comprar, se gastan los puntos automáticamente.
    """
    return await gamification_service.comprar_item(
        current_student.id,
        desbloqueable_id
    )


# ============================================
# Medallas
# ============================================

@router.get("/medals", response_model=MedallasResponse)
async def get_medallas(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene todas las medallas con su estado de obtención.
    
    Incluye:
    - Medallas obtenidas (con fecha)
    - Medallas no obtenidas
    - Total de medallas y cuántas tienes
    """
    return await gamification_service.get_medallas_estudiante(current_student.id)


@router.put("/medals/highlight/{medal_id}")
async def set_medalla_destacada(
    medal_id: int,
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep,
):
    """Establece la medalla destacada que se muestra en el dashboard."""
    await gamification_service.set_medalla_destacada(current_student.id, medal_id)
    return {"ok": True}


@router.delete("/medals/highlight")
async def quitar_medalla_destacada(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep,
):
    """Quita la medalla destacada del dashboard."""
    await gamification_service.set_medalla_destacada(current_student.id, None)
    return {"ok": True}


# ============================================
# Personalización
# ============================================

@router.get("/customization", response_model=PersonalizacionResponse)
async def get_personalizacion(
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene la configuración actual de personalización.
    
    Incluye:
    - Tema activo
    - Fondo activo
    - Música activa
    - Colores personalizados
    - Efectos activos
    """
    return await gamification_service.get_personalizacion(current_student.id)


@router.put("/customization", response_model=PersonalizacionResponse)
async def actualizar_personalizacion(
    request: ActualizarPersonalizacionRequest,
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Actualiza la configuración de personalización.
    
    Solo puedes activar items que ya posees.
    
    Puedes actualizar uno o varios campos a la vez:
    - tema_activo_id
    - fondo_activo_id
    - musica_activa_id
    - color_fondo
    - color_texto
    - color_botones
    - efectos_activos
    """
    campos = request.model_dump(exclude_none=True)
    
    return await gamification_service.actualizar_personalizacion(
        current_student.id,
        **campos
    )


# ============================================
# Tema Inicial Gratis
# ============================================

@router.get("/themes/initial", response_model=TemasInicialesResponse)
async def get_temas_iniciales(
    gamification_service: GamificationServiceDep
):
    """
    Obtiene los temas disponibles para selección inicial.
    
    El estudiante puede elegir uno gratis la primera vez.
    Esto se hace típicamente después del diagnóstico.
    """
    return await gamification_service.get_temas_iniciales()


@router.post("/themes/initial", response_model=ComprarItemResponse)
async def seleccionar_tema_inicial(
    request: SeleccionTemaInicialRequest,
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Selecciona el tema inicial gratis.
    
    Solo se puede hacer una vez por estudiante.
    El tema se desbloquea sin costo y se activa automáticamente.
    """
    return await gamification_service.seleccionar_tema_inicial(
        current_student.id,
        request.tema_id
    )


# ============================================
# Recompensas Post-Sesión
# ============================================

@router.get("/session/{sesion_id}/rewards", response_model=RecompensasSesionResponse)
async def get_recompensas_sesion(
    sesion_id: int,
    current_student: CurrentStudent,
    gamification_service: GamificationServiceDep
):
    """
    Obtiene las recompensas de una sesión completada.
    
    Incluye:
    - Puntos ganados (con desglose detallado)
    - Saldo total actual
    - Medallas nuevas obtenidas
    - Mensaje motivacional
    
    Este endpoint se llama automáticamente después de completar una sesión.
    """
    return await gamification_service.get_recompensas_sesion(
        sesion_id,
        current_student.id
    )

"""
Schemas Pydantic para gestión de prácticas e intentos.

Define contratos para sesiones, progreso y estadísticas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel

# ============================================
# Schemas de Progreso de Sesión
# ============================================

class SessionProgressResponse(BaseModel):
    """Progreso actual de una sesión en curso."""
    sesion_id: int
    total_problemas: int
    resueltos: int
    correctos: int
    incorrectos: int
    progreso_porcentaje: float
    tiempo_transcurrido: int  # segundos
    estado: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 123,
                "total_problemas": 15,
                "resueltos": 8,
                "correctos": 6,
                "incorrectos": 2,
                "progreso_porcentaje": 53.3,
                "tiempo_transcurrido": 240,
                "estado": "en_progreso"
            }
        }
    }


class NextProblemResponse(BaseModel):
    """Siguiente problema en la secuencia."""
    sesion_id: int
    problema_numero: int  # 1-15
    total_problemas: int
    problema: Dict  # ProblemaDisplay
    intentos_restantes: int  # 3, 2, 1
    es_ultimo: bool
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 123,
                "problema_numero": 9,
                "total_problemas": 15,
                "problema": {
                    "id": 456,
                    "operacion": "×",
                    "numero1": "12.5",
                    "numero2": "8",
                    "nivel_dificultad": 3
                },
                "intentos_restantes": 3,
                "es_ultimo": False
            }
        }
    }


class SubmitProblemRequest(BaseModel):
    """Request para enviar respuesta de un problema."""
    problema_id: int
    respuesta: Decimal
    tiempo_resolucion: int  # segundos en este intento
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "problema_id": 456,
                "respuesta": "100",
                "tiempo_resolucion": 15
            }
        }
    }


class SubmitProblemResponse(BaseModel):
    """Response después de enviar una respuesta."""
    es_correcto: bool
    respuesta_correcta: Optional[str]
    intentos_restantes: int
    mensaje: str
    siguiente_problema: Optional[NextProblemResponse]
    sesion_completada: bool
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "es_correcto": True,
                "respuesta_correcta": None,
                "intentos_restantes": 3,
                "mensaje": "¡Correcto!",
                "siguiente_problema": {},
                "sesion_completada": False
            }
        }
    }


# ============================================
# Schemas de Historial
# ============================================

class SessionHistoryItem(BaseModel):
    """Item de historial de sesiones."""
    sesion_id: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    estado: str
    nivel_actual: int
    cantidad_problemas: int
    problemas_correctos: int
    problemas_incorrectos: int
    precision: float
    tiempo_total_segundos: Optional[int]
    es_practica_perfecta: bool
    cambios_nivel: Optional[Dict]
    
    model_config = {"from_attributes": True}


class SessionHistoryResponse(BaseModel):
    """Lista de sesiones históricas."""
    total: int
    sesiones: List[SessionHistoryItem]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 25,
                "sesiones": []
            }
        }
    }


# ============================================
# Schemas de Resumen de Sesión
# ============================================

class ProblemaSummary(BaseModel):
    """Resumen de un problema en la sesión."""
    problema_id: int
    operacion: str
    enunciado: str
    nivel_dificultad: int
    intentos_realizados: int
    es_correcto: bool
    tiempo_total: int
    respuestas_intentadas: List[str]


class SessionSummaryResponse(BaseModel):
    """Resumen detallado de una sesión específica."""
    sesion_id: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    estado: str
    
    # Métricas globales
    total_problemas: int
    correctos: int
    incorrectos: int
    precision: float
    tiempo_total: int
    velocidad_promedio: float
    
    # Desglose por operación
    stats_por_operacion: Dict[str, Dict]
    
    # Problemas detallados
    problemas: List[ProblemaSummary]
    
    # Análisis
    errores_comunes: List[str]
    puntos_fuertes: List[str]
    recomendaciones: List[str]
    
    model_config = {"from_attributes": True}


# ============================================
# Schemas de Estadísticas Globales
# ============================================

class StatsPerOperation(BaseModel):
    """Estadísticas por operación."""
    operacion: str
    nivel_actual: int
    total_intentos: int
    total_correctos: int
    precision: float
    velocidad_promedio: float
    problemas_resueltos: int


class GlobalStatsResponse(BaseModel):
    """Estadísticas globales del estudiante."""
    estudiante_id: int
    
    # Totales
    total_sesiones: int
    total_sesiones_completas: int
    total_problemas_resueltos: int
    total_problemas_correctos: int
    
    # Promedios
    precision_global: float
    velocidad_promedio_global: float
    
    # Rachas
    racha_actual_perfectas: int
    mejor_racha_perfectas: int
    dias_consecutivos_practicando: int
    
    # Por operación
    stats_por_operacion: List[StatsPerOperation]
    
    # Progresión temporal
    precision_ultimos_7_dias: List[float]
    sesiones_ultimos_7_dias: List[int]
    
    model_config = {"from_attributes": True}


# ============================================
# Schemas de Alertas (Detección Tramposos)
# ============================================

class AlertaSospechosa(BaseModel):
    """Alerta de actividad sospechosa."""
    tipo: str
    severidad: str
    mensaje: str
    datos_contexto: Dict
    fecha_deteccion: datetime
    
    model_config = {"from_attributes": True}


class SuspiciousActivityResponse(BaseModel):
    """Response con alertas de un estudiante."""
    estudiante_id: int
    total_alertas: int
    alertas_activas: int
    alertas: List[AlertaSospechosa]

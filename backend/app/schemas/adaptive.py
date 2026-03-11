"""
Schemas Pydantic para sistema adaptativo y machine learning.

Define contratos para diagnóstico, perfiles, sesiones y recomendaciones.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_serializer
from decimal import Decimal
from datetime import datetime

from app.models.adaptive import PerfilAprendizaje, TipoAlerta, EstadoDiagnostico


# ============================================
# Schemas de Diagnóstico
# ============================================

class DiagnosticoStart(BaseModel):
    """Request para iniciar prueba diagnóstica."""
    pass  # No requiere parámetros, se genera automáticamente


class DiagnosticoSubmit(BaseModel):
    """Request para enviar respuestas del diagnóstico."""
    diagnostico_id: int
    respuestas: Dict[int, Decimal] = Field(
        description="Mapa de problema_id -> respuesta del estudiante"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "diagnostico_id": 1,
                "respuestas": {
                    "1": "8",
                    "2": "15.5",
                    "3": "7",
                    "4": "23.5"
                }
            }
        }
    }


class DiagnosticoResultado(BaseModel):
    """Response con resultados del diagnóstico."""
    estudiante_id: int
    perfecto: bool
    
    # Niveles asignados
    nivel_suma: int
    nivel_resta: int
    nivel_multiplicacion: int
    nivel_division: int
    nivel_actual: int
    
    # Resultados detallados
    correctos_por_operacion: Dict[str, int]
    velocidad_por_operacion: Dict[str, float]
    
    mensaje: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "estudiante_id": 1,
                "perfecto": False,
                "nivel_suma": 3,
                "nivel_resta": 2,
                "nivel_multiplicacion": 2,
                "nivel_division": 1,
                "nivel_actual": 3,
                "correctos_por_operacion": {
                    "suma": 2,
                    "resta": 1,
                    "multiplicacion": 1,
                    "division": 0
                },
                "velocidad_por_operacion": {
                    "suma": 15.5,
                    "resta": 20.3,
                    "multiplicacion": 25.0,
                    "division": 35.2
                },
                "mensaje": "Empezarás en nivel 3 con énfasis en división"
            }
        }
    }


# ============================================
# Schemas de Perfil
# ============================================

class PerfilResponse(BaseModel):
    """Response con perfil completo del estudiante."""
    estudiante_id: int
    
    # Niveles
    nivel_actual: int
    nivel_suma: int
    nivel_resta: int
    nivel_multiplicacion: int
    nivel_division: int
    
    # Operaciones disponibles
    operaciones_disponibles: List[str]
    operaciones_bloqueadas: List[str]
    prerequisitos_faltantes: Dict[str, List[str]]
    
    # Métricas
    precision_ultimos_15: Decimal
    velocidad_promedio: Decimal
    varianza_velocidad: Decimal
    
    # Contadores
    total_sesiones: int
    sesiones_en_nivel_actual: int
    practicas_perfectas_consecutivas: int
    
    # ML
    perfil_aprendizaje: str
    confianza_perfil: Optional[Decimal]
    
    # Progresión
    consecutivas_por_operacion: Dict[str, int]
    umbral_promocion: int
    
    # Actividad
    ultima_actividad: datetime
    dias_sin_practicar: int

    # Diagnóstico
    diagnostico_completado: bool = False

    # Contexto escolar
    grupo_nombre: Optional[str] = None
    profesor_nombre: Optional[str] = None

    @field_serializer('precision_ultimos_15', 'velocidad_promedio', 'varianza_velocidad', 'confianza_perfil')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        return str(value.normalize())
    
    model_config = {"from_attributes": True}


class EstadisticasGrupo(BaseModel):
    """Estadísticas comparativas con el grupo."""
    grupo_id: int
    total_estudiantes: int
    
    # Posición del estudiante
    percentil_velocidad: int  # 0-100
    percentil_precision: int
    
    # Comparativas
    velocidad_estudiante: float
    velocidad_promedio_grupo: float
    velocidad_top_10: float
    
    precision_estudiante: float
    precision_promedio_grupo: float
    
    # Ranking
    posicion_velocidad: int
    posicion_precision: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "grupo_id": 1,
                "total_estudiantes": 25,
                "percentil_velocidad": 85,
                "percentil_precision": 78,
                "velocidad_estudiante": 25.5,
                "velocidad_promedio_grupo": 35.2,
                "velocidad_top_10": 22.0,
                "precision_estudiante": 0.87,
                "precision_promedio_grupo": 0.75,
                "posicion_velocidad": 4,
                "posicion_precision": 6
            }
        }
    }


# ============================================
# Schemas de Sesión de Práctica
# ============================================

class SesionActivaResponse(BaseModel):
    """Response para sesión activa (en progreso) del estudiante."""
    sesion_id: int
    problemas_completados: int
    cantidad_problemas: int
    operaciones_incluidas: Dict[str, int]
    nivel_actual: int
    minutos_transcurridos: int
    fecha_inicio: datetime


class SesionStart(BaseModel):
    """Request para iniciar sesión de práctica."""
    pass  # Sistema decide todo automáticamente


class SesionStartResponse(BaseModel):
    """Response al iniciar sesión."""
    sesion_id: int
    cantidad_problemas: int
    operaciones_incluidas: Dict[str, int]
    nivel_actual: int
    
    # Los problemas (sin resultado)
    problemas: List[dict]  # Lista de ProblemaDisplay
    
    mensaje_intro: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 42,
                "cantidad_problemas": 15,
                "operaciones_incluidas": {
                    "multiplicacion": 7,
                    "suma": 4,
                    "resta": 3,
                    "division": 1
                },
                "nivel_actual": 3,
                "problemas": [],
                "mensaje_intro": "Hoy practicaremos multiplicación (tu operación más débil)"
            }
        }
    }


class SesionComplete(BaseModel):
    """Request para completar sesión."""
    sesion_id: int


class CambioNivel(BaseModel):
    """Información de cambio de nivel."""
    operacion: str
    nivel_anterior: int
    nivel_nuevo: int
    razon: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "operacion": "multiplicacion",
                "nivel_anterior": 2,
                "nivel_nuevo": 3,
                "razon": "10 problemas consecutivos correctos"
            }
        }
    }


class SesionCompleteResponse(BaseModel):
    """Response al completar sesión."""
    sesion_id: int
    
    # Resultados
    problemas_correctos: int
    problemas_incorrectos: int
    precision: float
    tiempo_total_segundos: int
    velocidad_promedio: float
    
    # Cambios de nivel
    cambios_nivel: List[CambioNivel]
    nivel_actual_nuevo: int
    
    # Comparación con grupo
    estadisticas_grupo: Optional[EstadisticasGrupo]
    
    # Feedback
    es_practica_perfecta: bool
    practicas_perfectas_consecutivas: int
    mensaje_motivacional: str
    
    # Próxima sesión
    operaciones_disponibles: List[str]
    operaciones_bloqueadas: List[str]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 42,
                "problemas_correctos": 14,
                "problemas_incorrectos": 1,
                "precision": 0.93,
                "tiempo_total_segundos": 450,
                "velocidad_promedio": 30.0,
                "cambios_nivel": [
                    {
                        "operacion": "multiplicacion",
                        "nivel_anterior": 2,
                        "nivel_nuevo": 3,
                        "razon": "10 consecutivos correctos"
                    }
                ],
                "nivel_actual_nuevo": 3,
                "estadisticas_grupo": None,
                "es_practica_perfecta": False,
                "practicas_perfectas_consecutivas": 0,
                "mensaje_motivacional": "¡Excelente trabajo! Solo un error en 15 problemas.",
                "operaciones_disponibles": ["suma", "resta", "multiplicacion"],
                "operaciones_bloqueadas": ["division"]
            }
        }
    }


# ============================================
# Schemas de Recomendaciones
# ============================================

class Recomendacion(BaseModel):
    """Recomendación de qué practicar."""
    operacion_sugerida: str
    nivel_operacion: int
    nivel_general: int
    cantidad_problemas: int
    
    razon: str
    mensaje_motivacional: str
    
    operaciones_disponibles: List[str]
    operaciones_bloqueadas: Dict[str, List[str]]  # operación -> prerequisitos faltantes
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "operacion_sugerida": "multiplicacion",
                "nivel_operacion": 2,
                "nivel_general": 3,
                "cantidad_problemas": 15,
                "razon": "Multiplicación es tu operación más débil",
                "mensaje_motivacional": "¡Vamos a dominar las multiplicaciones!",
                "operaciones_disponibles": ["suma", "resta", "multiplicacion"],
                "operaciones_bloqueadas": {
                    "division": ["multiplicacion nivel 2"]
                }
            }
        }
    }


# ============================================
# Schemas de Alertas (para futuro)
# ============================================

class AlertaResponse(BaseModel):
    """Response de alerta."""
    id: int
    estudiante_id: int
    tipo: str
    severidad: str
    titulo: str
    mensaje: str
    activa: bool
    leida: bool
    fecha_creacion: datetime
    
    model_config = {"from_attributes": True}


# ============================================
# Schemas de Estadísticas
# ============================================

class HistorialProgresion(BaseModel):
    """Historial de cambios de nivel."""
    operacion: str
    cambios: List[Dict]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "operacion": "suma",
                "cambios": [
                    {
                        "fecha": "2024-01-15T10:00:00",
                        "de": 1,
                        "a": 2,
                        "razon": "10 consecutivos"
                    },
                    {
                        "fecha": "2024-01-20T14:30:00",
                        "de": 2,
                        "a": 3,
                        "razon": "Velocidad top 10%"
                    }
                ]
            }
        }
    }


class EstadisticasDetalladas(BaseModel):
    """Estadísticas completas del estudiante."""
    estudiante_id: int
    nombre_completo: str
    
    # Niveles actuales
    niveles: Dict[str, int]
    nivel_actual: int
    
    # Métricas globales
    total_sesiones: int
    total_intentos: int
    precision_global: float
    velocidad_promedio_global: float
    
    # Por operación
    estadisticas_por_operacion: Dict[str, Dict]
    
    # Historial
    historial_promociones: List[Dict]
    
    # Comparación
    percentiles: Dict[str, int]
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "estudiante_id": 1,
                "nombre_completo": "Juan Pérez",
                "niveles": {
                    "suma": 4,
                    "resta": 3,
                    "multiplicacion": 2,
                    "division": 3
                },
                "nivel_actual": 4,
                "total_sesiones": 25,
                "total_intentos": 375,
                "precision_global": 0.85,
                "velocidad_promedio_global": 28.5,
                "estadisticas_por_operacion": {
                    "suma": {
                        "nivel": 4,
                        "intentos": 100,
                        "precision": 0.90,
                        "velocidad": 20.5
                    }
                },
                "historial_promociones": [],
                "percentiles": {
                    "velocidad": 85,
                    "precision": 78
                }
            }
        }
    }

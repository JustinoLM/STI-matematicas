"""
Schemas Pydantic para sistema adaptativo y machine learning.

Define contratos para diagnóstico, perfiles, sesiones y recomendaciones.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer

# ============================================
# Schemas de Diagnóstico
# ============================================


class DiagnosticoSubmit(BaseModel):
    """Request para enviar respuestas del diagnóstico."""
    diagnostico_id: int
    respuestas: Dict[int, Decimal] = Field(
        description="Mapa de problema_id -> respuesta del estudiante"
    )
    tiempos_por_problema: Optional[Dict[int, int]] = Field(
        default=None,
        description="Mapa de problema_id -> segundos empleados (opcional)"
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
                },
                "tiempos_por_problema": {
                    "1": 12,
                    "2": 25,
                    "3": 18,
                    "4": 40
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


# ============================================
# Schemas de Alertas (para futuro)
# ============================================


# ============================================
# Schemas de Estadísticas
# ============================================


# ============================================
# Schemas de Post-Test
# ============================================

class PostTestEstado(BaseModel):
    """Estado del post-test para el estudiante autenticado."""
    activo: bool        # ¿La organización tiene el post-test habilitado?
    completado: bool    # ¿El estudiante ya lo completó?
    org_id: Optional[int] = None


class PostTestSubmit(BaseModel):
    """Request para enviar respuestas del post-test."""
    post_test_id: int
    respuestas: Dict[int, Decimal] = Field(
        description="Mapa de problema_id -> respuesta del estudiante"
    )
    tiempos_por_problema: Optional[Dict[int, int]] = Field(
        default=None,
        description="Mapa de problema_id -> segundos empleados (opcional)"
    )


class PostTestResultado(BaseModel):
    """Response con resultados del post-test."""
    estudiante_id: int
    perfecto: bool
    total_correctos: int
    correctos_por_operacion: Dict[str, int]
    tiempos_por_operacion: Dict[str, int]   # segundos por operación
    # Comparación con pre-test (si está disponible)
    pre_correctos_por_operacion: Optional[Dict[str, int]] = None
    pre_nivel_actual: Optional[int] = None
    mensaje: str

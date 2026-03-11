"""
Schemas Pydantic para estadísticas de grupo.

Incluye datos por estudiante, distribución de perfiles ML,
alertas activas y respuesta de análisis IA.
"""

from typing import List, Optional
from pydantic import BaseModel


class ActividadDia(BaseModel):
    """Sesiones completadas en un día específico."""
    fecha: str   # "YYYY-MM-DD"
    sesiones: int


class PrecisionSemana(BaseModel):
    """Precisión promedio del grupo en una semana."""
    semana: str      # "2026-W09"
    precision: float  # 0.0 – 100.0


class DistribucionPerfiles(BaseModel):
    """Cuántos estudiantes del grupo tiene cada perfil ML."""
    rapido_preciso: int = 0
    cuidadoso_metodico: int = 0
    impulsivo: int = 0
    en_desarrollo: int = 0
    no_clasificado: int = 0


class AlertaResumen(BaseModel):
    """Contadores de alertas activas en el grupo."""
    posible_trampa: int = 0
    rezagado: int = 0
    inactivo: int = 0
    promocion_rapida: int = 0
    dificultad_persistente: int = 0
    excelencia: int = 0


class NivelesOperacion(BaseModel):
    """
    Histograma de niveles por operación.
    Cada lista tiene 5 elementos: índice 0 = nivel 1, índice 4 = nivel 5.
    Valor = número de estudiantes en ese nivel.
    """
    suma: List[int] = [0, 0, 0, 0, 0]
    resta: List[int] = [0, 0, 0, 0, 0]
    multiplicacion: List[int] = [0, 0, 0, 0, 0]
    division: List[int] = [0, 0, 0, 0, 0]


class EstudianteStatsItem(BaseModel):
    """Stats de un estudiante individual dentro del grupo."""
    id: int
    nombre: str
    codigo: str

    # Niveles por operación
    nivel_suma: int
    nivel_resta: int
    nivel_multiplicacion: int
    nivel_division: int
    nivel_actual: int

    # Métricas de rendimiento
    precision: float           # 0 – 100 (porcentaje)
    velocidad_promedio: float  # segundos/problema
    total_sesiones: int
    sesiones_esta_semana: int
    dias_sin_practicar: int

    # Machine Learning
    perfil_aprendizaje: str    # "rapido_preciso", "en_desarrollo", etc.
    confianza_perfil: float    # 0 – 100 (porcentaje de confianza del clustering)
    probabilidad_avance: float # 0 – 100 (regresión logística)

    # Alertas activas del sistema
    alertas: List[str]

    # Actividad individual (últimas 2 semanas)
    actividad_14_dias: List[ActividadDia]


class GrupoStatsResponse(BaseModel):
    """Estadísticas completas de un grupo para el panel analítico del profesor."""
    grupo_id: int
    grupo_nombre: str
    total_estudiantes: int

    # Distribución de perfiles ML
    distribucion_perfiles: DistribucionPerfiles

    # Resumen de alertas activas
    resumen_alertas: AlertaResumen

    # Histograma de niveles por operación
    niveles_por_operacion: NivelesOperacion

    # Precisión grupal (últimas 4 semanas)
    precision_semanal: List[PrecisionSemana]

    # Actividad grupal (últimas 2 semanas)
    actividad_grupal: List[ActividadDia]

    # Datos individuales de cada estudiante
    estudiantes: List[EstudianteStatsItem]

    model_config = {"from_attributes": True}


class AnalisisIAResponse(BaseModel):
    """Respuesta del análisis pedagógico generado por DeepSeek."""
    texto: str
    generado_por_llm: bool

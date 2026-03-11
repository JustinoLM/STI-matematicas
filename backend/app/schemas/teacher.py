"""Schemas para APIs del profesor."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.adaptive import TipoAlerta


# ==================== GRUPOS ====================

class GrupoCreate(BaseModel):
    """Crear grupo."""
    nombre: str = Field(..., max_length=255)
    codigo_grupo: str = Field(..., max_length=50)


class GrupoUpdate(BaseModel):
    """Actualizar grupo."""
    nombre: Optional[str] = Field(None, max_length=255)
    activo: Optional[bool] = None


class EstudianteEnGrupo(BaseModel):
    """Estudiante en grupo."""
    estudiante_id: int
    codigo_estudiante: str
    nombre_completo: str
    nivel_actual: int
    precision_ultimos_15: float
    fecha_ingreso: datetime
    activo: bool

    class Config:
        from_attributes = True


class GrupoDetalle(BaseModel):
    """Detalle de grupo con estudiantes."""
    id: int
    nombre: str
    codigo_grupo: str
    activo: bool
    profesor_id: int
    cantidad_estudiantes: int
    estudiantes: List[EstudianteEnGrupo] = []

    class Config:
        from_attributes = True


class GrupoResumen(BaseModel):
    """Resumen de grupo para listado."""
    id: int
    nombre: str
    codigo_grupo: str
    activo: bool
    cantidad_estudiantes: int
    promedio_precision: float
    problemas_resueltos_hoy: int

    class Config:
        from_attributes = True


# ==================== CONFIGURACIÓN ====================

class ConfiguracionPracticaCreate(BaseModel):
    """Crear configuración de práctica."""
    grupo_id: int
    operaciones_permitidas: List[str]   # "suma", "resta", "multiplicacion", "division"
    niveles_permitidos: List[int] = Field(default=[1, 2, 3, 4, 5])
    rango_min: Decimal = Field(default=0)
    rango_max: Decimal = Field(default=100)
    decimales_maximos: int = Field(default=2, ge=0, le=5)
    pistas_habilitadas: Dict[str, bool] = Field(
        default={"nivel_1": True, "nivel_2": True, "nivel_3": True}
    )


class ConfiguracionPracticaResponse(BaseModel):
    """Respuesta de configuración."""
    id: int
    grupo_id: int
    operaciones_permitidas: List[str]
    niveles_permitidos: List[int]
    rango_min: Decimal
    rango_max: Decimal
    decimales_maximos: int
    pistas_habilitadas: Dict[str, bool]
    fecha_aplicacion: datetime
    activa: bool

    class Config:
        from_attributes = True


# ==================== DESAFÍOS GRUPALES ====================

class DesafioGrupalCreate(BaseModel):
    """Crear desafío grupal.

    Tipos soportados (de más fácil a más difícil):
    - problemas_resueltos    → objetivo_cantidad = X problemas
    - sesiones_completadas   → objetivo_cantidad = X prácticas
    - practicas_sin_errores  → objetivo_cantidad = X prácticas, parametro_adicional = máx errores
    - problemas_rapidos      → objetivo_cantidad = X problemas, parametro_adicional = máx seg/problema
    - practicas_rapidas      → objetivo_cantidad = X prácticas, parametro_adicional = máx minutos
    """
    nombre: str = Field(..., max_length=255)
    descripcion: Optional[str] = None
    tipo: str = Field(..., max_length=100)
    objetivo_cantidad: int = Field(..., gt=0)
    parametro_adicional: Optional[int] = Field(None, gt=0)   # Parámetro secundario (Y)
    recompensa_texto: Optional[str] = None                    # Recompensa física
    recompensa_puntos: Optional[int] = Field(None, ge=0)      # XP otorgados al completar
    fecha_limite: Optional[datetime] = None
    grupos_ids: List[int]


class ProgresoGrupoDesafio(BaseModel):
    """Progreso de un grupo en desafío."""
    grupo_id: int
    nombre_grupo: str
    progreso_actual: int
    objetivo_cantidad: int
    porcentaje: float
    completado: bool


class DesafioGrupalDetalle(BaseModel):
    """Detalle de desafío grupal."""
    id: int
    profesor_id: int
    nombre: str
    descripcion: Optional[str]
    tipo: str
    objetivo_cantidad: int
    parametro_adicional: Optional[int]  # Parámetro Y (max errores / seg / min)
    recompensa_texto: Optional[str]
    recompensa_puntos: Optional[int]    # XP otorgados al completar
    fecha_creacion: datetime
    fecha_limite: Optional[datetime]
    completado: bool
    vencido: bool  # True si fecha_limite pasó sin alcanzar el objetivo
    eliminado: bool
    progreso_grupos: List[ProgresoGrupoDesafio]

    class Config:
        from_attributes = True


class DesafioGrupalResumen(BaseModel):
    """Resumen de desafío para listado."""
    id: int
    nombre: str
    tipo: str
    objetivo_cantidad: int
    parametro_adicional: Optional[int]
    recompensa_puntos: Optional[int]
    fecha_creacion: datetime
    fecha_limite: Optional[datetime]
    completado: bool
    cantidad_grupos: int
    grupos_completados: int

    class Config:
        from_attributes = True


# ==================== MONITOREO ====================

class EstadisticasGrupo(BaseModel):
    """Estadísticas agregadas del grupo."""
    grupo_id: int
    nombre_grupo: str
    
    # Generales
    total_estudiantes: int
    estudiantes_activos: int
    estudiantes_inactivos: int
    
    # Rendimiento
    promedio_precision: float
    promedio_velocidad: float
    problemas_resueltos_total: int
    problemas_resueltos_hoy: int
    
    # Distribución por nivel
    distribucion_niveles: Dict[int, int]  # {1: 5, 2: 10, ...}
    
    # Progreso
    estudiantes_rezagados: int
    estudiantes_estancados: int
    estudiantes_sobresalientes: int


class ProgresoEstudiante(BaseModel):
    """Progreso individual de estudiante."""
    estudiante_id: int
    codigo_estudiante: str
    nombre_completo: str
    
    # Niveles
    nivel_actual: int
    nivel_suma: int
    nivel_resta: int
    nivel_multiplicacion: int
    nivel_division: int
    
    # Métricas
    precision_ultimos_15: float
    velocidad_promedio: float
    consecutivas_correctas: int
    
    # Actividad
    total_sesiones: int
    ultima_actividad: datetime
    dias_sin_practicar: int
    
    # Alertas activas
    alertas_activas: List[str]

    class Config:
        from_attributes = True


class AlertaEstudianteResponse(BaseModel):
    """Alerta del sistema."""
    id: int
    estudiante_id: int
    codigo_estudiante: str
    nombre_estudiante: str
    tipo: TipoAlerta
    severidad: str
    titulo: str
    mensaje: str
    datos_contexto: Optional[Dict[str, Any]]
    activa: bool
    leida: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True


# ==================== BÚSQUEDA ====================

class BuscarEstudianteRequest(BaseModel):
    """Request de búsqueda."""
    query: str = Field(..., min_length=2)


class EstudianteSearchResult(BaseModel):
    """Resultado de búsqueda de estudiante."""
    estudiante_id: int
    codigo_estudiante: str
    nombre_completo: str
    grupos: List[str]  # Nombres de grupos
    nivel_actual: int
    ultima_actividad: datetime

    class Config:
        from_attributes = True


# ==================== REPORTES ====================

class GenerarReporteRequest(BaseModel):
    """Request para generar reporte PDF."""
    grupo_id: int
    incluir_estadisticas: bool = True
    incluir_progreso_individual: bool = True
    incluir_alertas: bool = True


class ReporteResponse(BaseModel):
    """Respuesta con URL del reporte."""
    url: str
    nombre_archivo: str
    fecha_generacion: datetime

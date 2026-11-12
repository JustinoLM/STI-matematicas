"""Schemas de la organización escolar: salones, años lectivos y trimestres."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.teacher import ConfiguracionPracticaResponse


class SalonCreate(BaseModel):
    """Crear (o reabrir para el año actual) un salón de la organización del profesor."""
    nombre: str = Field(..., min_length=1, max_length=50, examples=["1A"])
    grado: int = Field(..., ge=1, le=6)


class TrimestreOut(BaseModel):
    numero: int
    fecha_inicio: date
    fecha_fin: date

    model_config = {"from_attributes": True}


class TrimestreIn(BaseModel):
    fecha_inicio: date
    fecha_fin: date


class TrimestresUpdate(BaseModel):
    trimestres: List[TrimestreIn] = Field(..., min_length=3, max_length=3)


class SalonResumen(BaseModel):
    """Un salón en un año lectivo, visto por su profesor."""
    anio_lectivo_id: int
    salon_id: int
    nombre: str
    grado: int
    anio: int
    estado: str          # activo | cerrado
    cerrado: bool
    cantidad_estudiantes: int
    cantidad_grupos: int


class EstudianteDelSalon(BaseModel):
    estudiante_id: int
    codigo_estudiante: str
    nombre_completo: str
    nivel_actual: int
    precision_ultimos_15: float
    fecha_ingreso: datetime


class GrupoDelSalon(BaseModel):
    id: int
    nombre: str
    estudiantes_ids: List[int]


class SalonDetalle(SalonResumen):
    profesor_nombre: str
    trimestres: List[TrimestreOut]
    estudiantes: List[EstudianteDelSalon]
    grupos: List[GrupoDelSalon]
    configuracion: Optional[ConfiguracionPracticaResponse] = None


class CandidatoSalon(BaseModel):
    id: int
    codigo_estudiante: str
    nombre_completo: str
    salon_actual: Optional[str] = None   # Salón activo del estudiante, si tiene
    en_este_salon: bool


class BulkMatriculaRequest(BaseModel):
    codigos: List[str]


class BulkMatriculaError(BaseModel):
    fila: int
    codigo: str
    mensaje: str


class BulkMatriculaResult(BaseModel):
    total: int
    agregados: int
    errores: List[BulkMatriculaError]


class SalonOrganizacion(BaseModel):
    """Salón de una organización con su año lectivo más reciente (vista del administrador)."""
    salon_id: int
    nombre: str
    grado: int
    anio_lectivo_id: Optional[int] = None
    anio: Optional[int] = None
    estado: Optional[str] = None
    profesor_nombre: Optional[str] = None
    total_estudiantes: int = 0


class CierreAnioResult(BaseModel):
    anio: int
    anios_cerrados: int
    matriculas_cerradas: int
    desafios_no_completados: int

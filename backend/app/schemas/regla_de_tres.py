"""
Schemas Pydantic para el módulo de Regla de Tres.

Define contratos para práctica adaptativa, evaluación de respuestas
y notas por estudiante (profesor/admin).
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer
from decimal import Decimal
from datetime import datetime

from app.models.regla_de_tres import TipoProporcion


def _format_decimal(value: Decimal) -> str:
    """
    Formatea un Decimal sin ceros decimales sobrantes y SIN notación
    científica — Decimal.normalize() convierte enteros redondos como
    10, 20, 100 en '1E+1', '2E+1', '1E+2', lo cual rompe la UI.
    """
    texto = format(value, 'f')
    if '.' in texto:
        texto = texto.rstrip('0').rstrip('.')
    return texto


# ============================================
# Schemas de Problemas
# ============================================

class ProblemaReglaTresDisplay(BaseModel):
    """Problema de regla de tres para mostrar al estudiante (sin resultado)."""
    id: int
    tipo: str
    numero1: Decimal
    numero2: Decimal
    numero3: Decimal
    nivel_dificultad: int

    @field_serializer('numero1', 'numero2', 'numero3')
    def serialize_decimal(self, value: Decimal) -> str:
        return _format_decimal(value)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "tipo": "directa",
                "numero1": "4",
                "numero2": "12",
                "numero3": "7",
                "nivel_dificultad": 2,
            }
        }
    }


# ============================================
# Schemas de Sesión / Práctica
# ============================================

class SesionReglaTresStartResponse(BaseModel):
    """Response al iniciar una práctica de regla de tres."""
    sesion_id: int
    nivel_al_iniciar: int
    cantidad_problemas: int
    progreso_actual: int
    problema_actual: ProblemaReglaTresDisplay

    model_config = {"from_attributes": True}


class SubmitRespuestaR3Request(BaseModel):
    """Request para enviar respuesta a un problema de regla de tres."""
    problema_id: int
    respuesta: Decimal = Field(description="Respuesta del estudiante")

    model_config = {
        "json_schema_extra": {
            "example": {"problema_id": 1, "respuesta": "21"}
        }
    }


class ResumenSesionR3(BaseModel):
    """Resumen final de una sesión de práctica de regla de tres."""
    correctos: int
    total: int
    nota_pct: float
    nivel_actual: int
    puntos_ganados: int


class SubmitRespuestaR3Response(BaseModel):
    """Response al enviar una respuesta de regla de tres."""
    es_correcto: bool
    resultado_correcto: Decimal
    sesion_completada: bool
    progreso_actual: int
    cantidad_problemas: int
    siguiente_problema: Optional[ProblemaReglaTresDisplay] = None
    resumen: Optional[ResumenSesionR3] = None

    @field_serializer('resultado_correcto')
    def serialize_decimal(self, value: Decimal) -> str:
        return _format_decimal(value)


# ============================================
# Schemas de Notas (profesor / admin)
# ============================================

class EstudianteNotaR3(BaseModel):
    """Nota de la última práctica de regla de tres de un estudiante."""
    estudiante_id: int
    codigo: str
    nombre_completo: str
    tiene_practica: bool
    ultima_fecha: Optional[datetime] = None
    correctos: Optional[int] = None
    total: Optional[int] = None
    nota_pct: Optional[float] = None
    nivel_actual: Optional[int] = None


class NotasReglaTresResponse(BaseModel):
    """Lista de notas de regla de tres para profesor o admin."""
    estudiantes: List[EstudianteNotaR3]

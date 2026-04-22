"""
Schemas Pydantic para organizaciones / colegios.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Schemas de Request
# ============================================

class CreateOrganizacionRequest(BaseModel):
    nombre: str = Field(min_length=3, max_length=255)
    codigo: str = Field(min_length=3, max_length=50)
    descripcion: Optional[str] = None
    ciudad: Optional[str] = Field(None, max_length=100)
    pais: Optional[str] = Field("Panamá", max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Escuela Primaria Central",
                "codigo": "EPC001",
                "descripcion": "Escuela de prueba para tesis",
                "ciudad": "Ciudad de Panamá",
                "pais": "Panamá",
            }
        }


class AsignarOrganizacionRequest(BaseModel):
    """Asignar o quitar organización a un usuario."""
    organizacion_id: Optional[int] = None  # null = quitar asignación


# ============================================
# Schemas de Response
# ============================================

class OrganizacionResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    descripcion: Optional[str]
    ciudad: Optional[str]
    pais: Optional[str]
    fecha_creacion: datetime
    activa: bool
    post_test_activo: bool = False
    total_profesores: int = 0
    total_estudiantes: int = 0

    class Config:
        from_attributes = True


class OrganizacionListResponse(BaseModel):
    total: int
    organizaciones: List[OrganizacionResponse]


class MiembroResponse(BaseModel):
    """Miembro (profesor o estudiante) de una organización."""
    id: int
    codigo: str
    nombre_completo: str
    tipo: str  # "profesor" | "estudiante"

    class Config:
        from_attributes = True


class OrganizacionDetalleResponse(OrganizacionResponse):
    profesores: List[MiembroResponse] = []
    estudiantes: List[MiembroResponse] = []

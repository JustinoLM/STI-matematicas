"""Esquemas del catálogo de lecciones (solo lectura)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CaminoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conjunto: str
    habilidad: str
    nombre: str
    orden: int


class LeccionCatalogoOut(BaseModel):
    id: str
    grado: int
    unidad_numero: int
    unidad_titulo: str
    leccion_numero: int
    leccion_titulo: str
    orden_programa: int
    incluida: bool
    motivo_exclusion: Optional[str] = None
    parcial: bool
    nota_parcial: Optional[str] = None
    presentacion_especial: Optional[str] = None
    cubierta_por: Optional[str] = None
    notas: Optional[str] = None
    caminos: list[str]
    prerrequisitos: list[str]   # prerrequisitos por defecto (ids de lección)

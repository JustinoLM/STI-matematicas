"""
Schemas para la importación del Excel completo (inverso del exportador).

Todo lo importado queda aislado en una organización "sandbox" elegida por
el admin — nunca se sobreescriben datos de organizaciones existentes.
"""

from pydantic import BaseModel


class ConteoHoja(BaseModel):
    """Resultado de procesar una hoja del Excel."""
    hoja: str
    procesados: int = 0
    creados: int = 0
    omitidos: int = 0


class ImportResumen(BaseModel):
    """Resumen completo de una importación de Excel."""
    organizacion_id: int
    organizacion_nombre: str
    organizacion_creada: bool
    hojas: list[ConteoHoja]
    advertencias: list[str]

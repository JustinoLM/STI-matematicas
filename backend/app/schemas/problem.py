"""
Schemas Pydantic para problemas matemáticos.
"""

from decimal import Decimal

from pydantic import BaseModel, field_serializer


class ProblemaDisplay(BaseModel):
    """Problema para mostrar al estudiante (sin resultado)."""
    id: int
    operacion: str
    numero1: Decimal
    numero2: Decimal
    nivel_dificultad: int
    
    @field_serializer('numero1', 'numero2')
    def serialize_decimal(self, value: Decimal) -> str:
        """Serializa Decimal eliminando ceros trailing."""
        return str(value.normalize())
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "operacion": "+",
                "numero1": "12.5",
                "numero2": "8.3",
                "nivel_dificultad": 2
            }
        }
    }

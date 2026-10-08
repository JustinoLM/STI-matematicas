"""
Schemas Pydantic de pistas.

Contratos para solicitar una pista y para su respuesta.
"""

from pydantic import BaseModel, Field


class SolicitarPistaRequest(BaseModel):
    """Request para solicitar una pista."""
    sesion_id: int
    problema_id: int
    nivel_pista: int = Field(..., ge=1, le=3, description="Nivel de pista (1-3)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 123,
                "problema_id": 456,
                "nivel_pista": 2
            }
        }
    }


class PistaResponse(BaseModel):
    """Response con el contenido de la pista."""
    nivel_pista: int
    contenido: str
    puntos_gastados: int
    saldo_nuevo: int
    generada_llm: bool = False
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "nivel_pista": 2,
                "contenido": "Paso 1: Alinea los puntos decimales...",
                "puntos_gastados": 0,
                "saldo_nuevo": 1245,
                "generada_llm": False
            }
        }
    }

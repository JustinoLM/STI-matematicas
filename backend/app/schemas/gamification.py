"""
Schemas Pydantic para gamificación.

Define contratos para tienda, medallas, puntos y personalización.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

# ============================================
# Schemas de Desbloqueables (Tienda)
# ============================================

class DesbloqueableBase(BaseModel):
    """Base para desbloqueables."""
    categoria: str
    nombre: str
    descripcion: Optional[str]
    precio_puntos: int
    nivel_minimo_requerido: int
    archivo_referencia: Optional[str]


class DesbloqueableResponse(DesbloqueableBase):
    """Desbloqueable en el catálogo."""
    id: int
    orden: int
    es_tema_inicial: bool
    
    # Información de propiedad (si el estudiante lo tiene)
    poseido: bool = False
    fecha_compra: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class ComprarItemResponse(BaseModel):
    """Response después de comprar."""
    exito: bool
    mensaje: str
    item_comprado: Optional[DesbloqueableResponse]
    puntos_gastados: int
    saldo_nuevo: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "exito": True,
                "mensaje": "¡Desbloqueaste el tema Pirates!",
                "item_comprado": {},
                "puntos_gastados": 500,
                "saldo_nuevo": 745
            }
        }
    }


class TiendaResponse(BaseModel):
    """Catálogo completo de la tienda."""
    temas: List[DesbloqueableResponse]
    fondos: List[DesbloqueableResponse]
    colores: List[DesbloqueableResponse]
    musicas: List[DesbloqueableResponse]
    efectos: List[DesbloqueableResponse]
    total_items: int


# ============================================
# Schemas de Puntos
# ============================================

class SaldoPuntosResponse(BaseModel):
    """Saldo actual de puntos del estudiante."""
    estudiante_id: int
    puntos_totales: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "estudiante_id": 1,
                "puntos_totales": 1245
            }
        }
    }


class TransaccionPuntosResponse(BaseModel):
    """Una transacción de puntos."""
    id: int
    tipo: str  # "ganancia" o "gasto"
    cantidad: int
    concepto: str
    saldo_resultante: int
    fecha: datetime
    
    model_config = {"from_attributes": True}


class HistorialPuntosResponse(BaseModel):
    """Historial de transacciones."""
    total: int
    transacciones: List[TransaccionPuntosResponse]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 45,
                "transacciones": []
            }
        }
    }


class DesglosePuntosResponse(BaseModel):
    """Desglose detallado de puntos ganados en una sesión."""
    total: int
    desglose: Dict[str, int]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 175,
                "desglose": {
                    "practica_perfecta": 100,
                    "bonus_velocidad": 20,
                    "primera_del_dia": 10,
                    "subio_suma": 75
                }
            }
        }
    }


# ============================================
# Schemas de Medallas
# ============================================

class MedallaBase(BaseModel):
    """Base para medallas."""
    nombre: str
    descripcion: str
    categoria: str
    imagen_url: Optional[str]
    es_secreta: bool = False


class MedallaResponse(MedallaBase):
    """Medalla con información de obtención."""
    id: int
    orden: int

    # Información de obtención
    obtenida: bool = False
    fecha_obtencion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MedallasResponse(BaseModel):
    """Todas las medallas del estudiante."""
    total_medallas: int
    medallas_obtenidas: int
    medallas: List[MedallaResponse]
    medalla_destacada_id: Optional[int] = None


# ============================================
# Schemas de Personalización
# ============================================

class PersonalizacionResponse(BaseModel):
    """Configuración actual de personalización."""
    estudiante_id: int
    
    # Items activos (IDs)
    tema_activo_id: Optional[int]
    fondo_activo_id: Optional[int]
    musica_activa_id: Optional[int]
    
    # Items activos (nombres)
    tema_activo_nombre: Optional[str]
    fondo_activo_nombre: Optional[str]
    musica_activa_nombre: Optional[str]
    
    # Colores
    color_fondo: str
    color_texto: str
    color_botones: str
    
    # Efectos
    efectos_activos: List[int]
    
    fecha_actualizacion: datetime
    
    model_config = {"from_attributes": True}


class ActualizarPersonalizacionRequest(BaseModel):
    """Request para cambiar personalización activa."""
    tema_activo_id: Optional[int] = None
    fondo_activo_id: Optional[int] = None
    musica_activa_id: Optional[int] = None
    color_fondo: Optional[str] = None
    color_texto: Optional[str] = None
    color_botones: Optional[str] = None
    efectos_activos: Optional[List[int]] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "tema_activo_id": 2,
                "fondo_activo_id": 5,
                "color_fondo": "#1E3A5F"
            }
        }
    }


class SeleccionTemaInicialRequest(BaseModel):
    """Request para seleccionar tema gratis inicial."""
    tema_id: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "tema_id": 1
            }
        }
    }


# ============================================
# Schemas de Recompensas (Post-Sesión)
# ============================================

class MedallaNuevaResponse(BaseModel):
    """Medalla recién obtenida."""
    id: int
    nombre: str
    descripcion: str
    imagen_url: Optional[str]


class RecompensasSesionResponse(BaseModel):
    """Recompensas obtenidas al completar una sesión."""
    sesion_id: int
    
    # Puntos
    puntos_ganados: int
    desglose_puntos: Dict[str, int]
    saldo_total: int
    
    # Medallas nuevas
    medallas_nuevas: List[MedallaNuevaResponse]
    
    # Feedback motivacional
    mensaje_motivacional: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sesion_id": 123,
                "puntos_ganados": 175,
                "desglose_puntos": {
                    "practica_perfecta": 100,
                    "bonus_velocidad": 20,
                    "primera_del_dia": 10,
                    "subio_suma": 75
                },
                "saldo_total": 1420,
                "medallas_nuevas": [],
                "mensaje_motivacional": "¡Excelente trabajo! Sigue así."
            }
        }
    }


# ============================================
# Schemas de Temas Iniciales
# ============================================

class TemaInicialResponse(BaseModel):
    """Tema disponible para selección inicial."""
    id: int
    nombre: str
    descripcion: str
    archivo_referencia: Optional[str]
    preview_url: Optional[str]  # Para mostrar preview en frontend
    
    model_config = {"from_attributes": True}


class TemasInicialesResponse(BaseModel):
    """Lista de temas para elegir el inicial gratis."""
    temas: List[TemaInicialResponse]
    mensaje: str = "Elige tu primer tema (gratis)"

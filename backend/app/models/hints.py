"""
Modelos del sistema de pistas.

NivelPista y TipoError son enumeraciones; UsoPista registra cada pista solicitada y
GeneracionLLM guarda el historial de las pistas generadas con el LLM.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.core.database import Base


class NivelPista(int, enum.Enum):
    """Niveles de pistas disponibles."""
    NIVEL_1 = 1  # Estrategia general (gratis)
    NIVEL_2 = 2  # Paso a paso (gratis)
    NIVEL_3 = 3  # Casi la respuesta (10 puntos)


class TipoError(str, enum.Enum):
    """Categorías de errores detectados."""
    DESALINEACION_DECIMALES = "desalineacion_decimales"
    PUNTO_MAL_COLOCADO = "punto_mal_colocado"
    CONFUNDIO_OPERACION = "confundio_operacion"
    ORDEN_INCORRECTO = "orden_incorrecto"
    ERROR_TABLA = "error_tabla"
    ERROR_CALCULO_GENERAL = "error_calculo_general"


class UsoPista(Base):
    """
    Tracking de uso de pistas por estudiante.
    
    Permite analytics y detección de patrones.
    """
    __tablename__ = "uso_pista"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    sesion_id = Column(Integer, ForeignKey("sesion_practica.id"), nullable=False)
    problema_id = Column(Integer, ForeignKey("problema.id"), nullable=False)
    
    nivel_pista = Column(Enum(NivelPista), nullable=False)
    puntos_gastados = Column(Integer, default=0)
    
    # Para pistas generadas con LLM
    generada_llm = Column(Boolean, default=False)
    contenido_pista = Column(Text, nullable=True)  # Guardar pista generada
    
    fecha = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<UsoPista estudiante={self.estudiante_id} N{self.nivel_pista.value}>"


class GeneracionLLM(Base):
    """
    Historial de generaciones con LLM.
    
    Para debugging, analytics y mejora de prompts.
    """
    __tablename__ = "generacion_llm"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Contexto
    tipo = Column(String(50), nullable=False)  # pista_nivel_3
    problema_id = Column(Integer, ForeignKey("problema.id"), nullable=True)
    tema = Column(String(50), nullable=True)  # pirates, astronauts, etc.
    
    # Request
    prompt_usado = Column(Text, nullable=False)
    modelo = Column(String(50), nullable=False)  # ej. deepseek-chat
    
    # Response
    respuesta_llm = Column(Text, nullable=False)
    tokens_usados = Column(Integer, nullable=True)
    tiempo_generacion_ms = Column(Integer, nullable=True)
    
    # Metadata
    fecha = Column(DateTime, default=datetime.utcnow, index=True)
    exitoso = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<GeneracionLLM {self.tipo} exitoso={self.exitoso}>"

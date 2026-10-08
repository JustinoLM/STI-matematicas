"""
Modelos de problemas matemáticos e intentos.

Problema: Ejercicios matemáticos generados.
Intento: Respuestas de estudiantes a problemas.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Operacion(str, enum.Enum):
    """Enum para tipos de operaciones matemáticas."""
    SUMA = "+"
    RESTA = "-"
    MULTIPLICACION = "×"
    DIVISION = "÷"


class TipoSesion(str, enum.Enum):
    """Enum para tipos de sesión de práctica."""
    PRACTICA = "practica"
    DESAFIO = "desafio"
    REDENCION = "redencion"


class Problema(Base):
    """
    Problema matemático generado.
    
    Cada problema es único identificado por su signature (hash).
    
    Relaciones:
    - Tiene múltiples Intentos (1:N)
    """
    __tablename__ = "problema"
    
    id = Column(Integer, primary_key=True, index=True)
    operacion = Column(Enum(Operacion), nullable=False, index=True)
    numero1 = Column(Numeric(10, 3), nullable=False)
    numero2 = Column(Numeric(10, 3), nullable=False)
    resultado = Column(Numeric(10, 3), nullable=False)
    nivel_dificultad = Column(Integer, nullable=False, index=True)  # 1-5
    cantidad_decimales = Column(Integer, nullable=False)
    signature = Column(String(64), unique=True, nullable=False, index=True)  # Hash único
    fecha_generacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    intentos = relationship("Intento", back_populates="problema")
    errores_detectados = relationship("EstudianteError", back_populates="problema")
    
    def __repr__(self):
        return f"<Problema(id={self.id}, op={self.operacion}, nivel={self.nivel_dificultad})>"


class Intento(Base):
    """
    Intento de resolución de un problema por un estudiante.
    
    Registra respuesta, tiempo, si solicitó pista, y contexto de la sesión.
    
    Relaciones:
    - Pertenece a un Estudiante (N:1)
    - Resuelve un Problema (N:1)
    """
    __tablename__ = "intento"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    problema_id = Column(Integer, ForeignKey("problema.id"), nullable=False, index=True)
    respuesta_estudiante = Column(Numeric(10, 3), nullable=False)
    es_correcto = Column(Boolean, nullable=False, index=True)
    tiempo_resolucion = Column(Integer, nullable=False)  # segundos
    solicito_pista = Column(Boolean, default=False, nullable=False)
    tipo_sesion = Column(Enum(TipoSesion), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sesion_id = Column(Integer, ForeignKey("sesion_practica.id"), nullable=True)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="intentos")
    problema = relationship("Problema", back_populates="intentos")
    sesion = relationship("SesionPractica", back_populates="intentos")

    
    def __repr__(self):
        return f"<Intento(id={self.id}, estudiante_id={self.estudiante_id}, correcto={self.es_correcto})>"

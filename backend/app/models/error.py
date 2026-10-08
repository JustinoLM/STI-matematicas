"""
Modelos del Buggy Model (sistema de detección de errores comunes).

ErrorComun: Catálogo de misconceptions matemáticos.
EstudianteError: Tracking de errores cometidos por estudiantes.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ErrorComun(Base):
    """
    Catálogo de errores comunes (misconceptions) matemáticos.
    
    Ejemplos:
    - DECIMAL_ALIGN: Alinear decimales por la derecha en vez de por el punto
    - SUBTRACT_SMALLER: Siempre restar el número menor del mayor
    - MULTIPLY_ADD: Confundir multiplicación con suma
    
    Relaciones:
    - Detectado en múltiples Estudiantes (1:N via EstudianteError)
    """
    __tablename__ = "error_comun"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(100), unique=True, nullable=False, index=True)  # ej: 'DECIMAL_ALIGN'
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    operacion_asociada = Column(String(50), nullable=True)  # '+', '-', '×', '÷', null (aplica a todas)
    patron_deteccion = Column(Text, nullable=True)  # Regex o regla de detección
    
    # Relaciones
    estudiantes_afectados = relationship("EstudianteError", back_populates="error")
    
    def __repr__(self):
        return f"<ErrorComun(id={self.id}, codigo={self.codigo}, nombre={self.nombre})>"


class EstudianteError(Base):
    """
    Tracking de errores comunes cometidos por estudiantes.
    
    Permite identificar misconceptions persistentes y ofrecer
    intervención pedagógica específica.
    
    Relaciones:
    - Pertenece a un Estudiante (N:1)
    - Es un ErrorComun específico (N:1)
    - Detectado en un Problema (N:1)
    """
    __tablename__ = "estudiante_error"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    error_id = Column(Integer, ForeignKey("error_comun.id"), nullable=False, index=True)
    problema_id = Column(Integer, ForeignKey("problema.id"), nullable=False, index=True)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resuelto = Column(Boolean, default=False, nullable=False, index=True)
    fecha_resolucion = Column(DateTime, nullable=True)
    
    # Relaciones
    estudiante = relationship("Estudiante")
    error = relationship("ErrorComun", back_populates="estudiantes_afectados")
    problema = relationship("Problema", back_populates="errores_detectados")
    
    def __repr__(self):
        return f"<EstudianteError(id={self.id}, estudiante_id={self.estudiante_id}, error_id={self.error_id})>"

"""
Modelo de narrativas del sistema de gamificación.

Las narrativas son temas visuales que personalizan la experiencia
del estudiante (Piratas, Astronautas, etc.).
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Narrativa(Base):
    """
    Narrativas temáticas del sistema.
    
    Ejemplos: Piratas, Astronautas, Magos, Caballeros, Cowboys, Princesas Inventoras.
    
    Relaciones:
    - Tiene múltiples Estudiantes que la seleccionaron (1:N)
    """
    __tablename__ = "narrativa"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    icono_url = Column(String(500), nullable=True)
    
    # Relaciones
    estudiantes = relationship("Estudiante", back_populates="narrativa")
    
    def __repr__(self):
        return f"<Narrativa(id={self.id}, nombre={self.nombre})>"

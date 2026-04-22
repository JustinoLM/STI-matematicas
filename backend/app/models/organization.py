"""
Modelo de Organización / Colegio.

Agrupa profesores (y opcionalmente estudiantes) bajo una misma institución.
Permite al administrador separar usuarios de diferentes colegios o contextos.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Organizacion(Base):
    """
    Organización o colegio al que pertenecen profesores y estudiantes.

    Un profesor pertenece a una organización.
    Los estudiantes pueden pertenecer directamente a una organización
    o heredarla a través de su grupo (relación con el profesor).
    """
    __tablename__ = "organizacion"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, unique=True)
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    descripcion = Column(Text, nullable=True)
    ciudad = Column(String(100), nullable=True)
    pais = Column(String(100), nullable=True, default="Colombia")
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    activa = Column(Integer, default=1, nullable=False)  # 1=activa, 0=inactiva

    # Post-test activado por el admin para medir mejora final
    post_test_activo = Column(Boolean, default=False, nullable=False)

    # Relaciones
    profesores = relationship("Profesor", back_populates="organizacion")
    estudiantes = relationship("Estudiante", back_populates="organizacion")

    def __repr__(self):
        return f"<Organizacion(codigo={self.codigo}, nombre={self.nombre})>"

"""
Modelos de grupos escolares y membresía de estudiantes.

Grupo representa una clase/sección escolar.
EstudianteGrupo es la tabla asociativa para la relación N:M.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Grupo(Base):
    """
    Grupo escolar (clase/sección).
    
    Relaciones:
    - Pertenece a un Profesor (N:1)
    - Tiene múltiples Estudiantes (N:M via EstudianteGrupo)
    - Tiene múltiples ConfiguracionesPractica (1:N)
    - Participa en múltiples DesafiosGrupales (N:M)
    """
    __tablename__ = "grupo"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False, index=True)
    codigo_grupo = Column(String(50), unique=True, nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)
    
    # Relaciones
    profesor = relationship("Profesor", back_populates="grupos")
    estudiantes = relationship("EstudianteGrupo", back_populates="grupo")
    configuraciones_practica = relationship("ConfiguracionPractica", back_populates="grupo")
    desafios = relationship("GrupoDesafio", back_populates="grupo")
    
    def __repr__(self):
        return f"<Grupo(id={self.id}, nombre={self.nombre}, codigo={self.codigo_grupo})>"


class EstudianteGrupo(Base):
    """
    Tabla asociativa para la relación N:M entre Estudiante y Grupo.
    
    Permite que un estudiante pertenezca a múltiples grupos
    y un grupo tenga múltiples estudiantes.
    """
    __tablename__ = "estudiante_grupo"
    
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    grupo_id = Column(Integer, ForeignKey("grupo.id"), primary_key=True)
    fecha_ingreso = Column(DateTime, default=datetime.utcnow, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="grupos")
    grupo = relationship("Grupo", back_populates="estudiantes")
    
    def __repr__(self):
        return f"<EstudianteGrupo(estudiante_id={self.estudiante_id}, grupo_id={self.grupo_id})>"

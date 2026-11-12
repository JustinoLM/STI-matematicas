"""
Modelos de grupos escolares y membresía de estudiantes.

Grupo es un subconjunto opcional de estudiantes dentro de un año lectivo de un salón
(por ejemplo, para desafíos). Se cierra junto con el año lectivo y queda de solo lectura.
EstudianteGrupo es la tabla asociativa para la relación N:M.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Grupo(Base):
    """
    Grupo dentro de un año lectivo.

    Relaciones:
    - Pertenece a un AnioLectivo (N:1); el profesor es el del año lectivo
    - Tiene múltiples Estudiantes (N:M via EstudianteGrupo), todos matriculados en ese año
    - Participa en múltiples DesafiosGrupales (N:M)
    """
    __tablename__ = "grupo"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)

    # Relaciones
    anio_lectivo = relationship("AnioLectivo", back_populates="grupos")
    estudiantes = relationship("EstudianteGrupo", back_populates="grupo")
    desafios = relationship("GrupoDesafio", back_populates="grupo")

    __table_args__ = (
        UniqueConstraint("anio_lectivo_id", "nombre", name="uq_grupo_anio_nombre"),
    )

    def __repr__(self):
        return f"<Grupo(id={self.id}, nombre={self.nombre}, anio_lectivo_id={self.anio_lectivo_id})>"


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

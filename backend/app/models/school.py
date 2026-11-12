"""
Organización escolar: salón fijo, año lectivo, matrícula y trimestres.

- Salon: el salón permanente de una organización ("1A"), con su grado (1 a 6).
- AnioLectivo: el salón en un año concreto ("1A en 2026"), con su profesor. Un salón tiene
  como máximo un año lectivo activo; al cerrarse queda de solo lectura y no se borra nada.
- Matricula: el estudiante en un año lectivo. Un estudiante tiene como máximo una matrícula
  activa en todo el sistema (índice único parcial en la base de datos).
- Trimestre: fechas de los 3 trimestres de una organización en un año. Las edita el
  administrador para toda la organización; los años lectivos las leen de aquí.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# Estados (texto con CHECK en vez de tipos ENUM de PostgreSQL, más simples de migrar)
ANIO_ACTIVO = "activo"
ANIO_CERRADO = "cerrado"

MATRICULA_ACTIVA = "activa"
MATRICULA_RETIRADA = "retirada"   # el profesor quitó al estudiante durante el año
MATRICULA_CERRADA = "cerrada"     # el año lectivo se cerró con el estudiante dentro


class Salon(Base):
    """Salón fijo de una organización, con id permanente."""

    __tablename__ = "salon"

    id = Column(Integer, primary_key=True, index=True)
    organizacion_id = Column(Integer, ForeignKey("organizacion.id"), nullable=False, index=True)
    nombre = Column(String(50), nullable=False)  # Ej: "1A"
    grado = Column(Integer, nullable=False)       # 1 a 6
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    organizacion = relationship("Organizacion")
    anios_lectivos = relationship("AnioLectivo", back_populates="salon")

    __table_args__ = (
        UniqueConstraint("organizacion_id", "nombre", name="uq_salon_org_nombre"),
        CheckConstraint("grado BETWEEN 1 AND 6", name="ck_salon_grado"),
    )

    def __repr__(self):
        return f"<Salon(id={self.id}, nombre={self.nombre}, grado={self.grado})>"


class AnioLectivo(Base):
    """El salón en un año concreto: profesor, estudiantes, grupos, configuración y desafíos."""

    __tablename__ = "anio_lectivo"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salon.id"), nullable=False, index=True)
    anio = Column(Integer, nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default=ANIO_ACTIVO, server_default=ANIO_ACTIVO)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_cierre = Column(DateTime, nullable=True)

    salon = relationship("Salon", back_populates="anios_lectivos")
    profesor = relationship("Profesor")
    matriculas = relationship("Matricula", back_populates="anio_lectivo")
    grupos = relationship("Grupo", back_populates="anio_lectivo")

    __table_args__ = (
        UniqueConstraint("salon_id", "anio", name="uq_anio_lectivo_salon_anio"),
        CheckConstraint("estado IN ('activo', 'cerrado')", name="ck_anio_lectivo_estado"),
        Index(
            "uq_anio_lectivo_activo_por_salon",
            "salon_id",
            unique=True,
            postgresql_where=text("estado = 'activo'"),
        ),
    )

    @property
    def cerrado(self) -> bool:
        return self.estado == ANIO_CERRADO

    def __repr__(self):
        return f"<AnioLectivo(id={self.id}, salon_id={self.salon_id}, anio={self.anio}, estado={self.estado})>"


class Matricula(Base):
    """Estudiante en un año lectivo."""

    __tablename__ = "matricula"

    id = Column(Integer, primary_key=True, index=True)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default=MATRICULA_ACTIVA, server_default=MATRICULA_ACTIVA)
    fecha_ingreso = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_salida = Column(DateTime, nullable=True)

    anio_lectivo = relationship("AnioLectivo", back_populates="matriculas")
    estudiante = relationship("Estudiante")

    __table_args__ = (
        UniqueConstraint("anio_lectivo_id", "estudiante_id", name="uq_matricula_anio_estudiante"),
        CheckConstraint("estado IN ('activa', 'retirada', 'cerrada')", name="ck_matricula_estado"),
        Index(
            "uq_matricula_activa_por_estudiante",
            "estudiante_id",
            unique=True,
            postgresql_where=text("estado = 'activa'"),
        ),
    )

    def __repr__(self):
        return f"<Matricula(estudiante_id={self.estudiante_id}, anio_lectivo_id={self.anio_lectivo_id}, estado={self.estado})>"


class Trimestre(Base):
    """Fechas de un trimestre de una organización en un año."""

    __tablename__ = "trimestre"

    id = Column(Integer, primary_key=True, index=True)
    organizacion_id = Column(Integer, ForeignKey("organizacion.id"), nullable=False, index=True)
    anio = Column(Integer, nullable=False)
    numero = Column(Integer, nullable=False)  # 1, 2 o 3
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("organizacion_id", "anio", "numero", name="uq_trimestre_org_anio_numero"),
        CheckConstraint("numero BETWEEN 1 AND 3", name="ck_trimestre_numero"),
        CheckConstraint("fecha_inicio <= fecha_fin", name="ck_trimestre_fechas"),
    )

    def __repr__(self):
        return f"<Trimestre(org={self.organizacion_id}, anio={self.anio}, numero={self.numero})>"

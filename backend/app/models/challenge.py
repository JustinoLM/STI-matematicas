"""
Modelos de desafíos grupales.

DesafioGrupal: Retos dentro de un año lectivo de un salón (ej: "Resolver 100 problemas entre
todos"). Nunca abarcan varios salones.
GrupoDesafio: Un equipo del desafío con su progreso. El equipo es un grupo del salón o, si
grupo_id es NULL, el salón completo (sus estudiantes matriculados).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

DESAFIO_ACTIVO = "activo"
DESAFIO_COMPLETADO = "completado"
DESAFIO_NO_COMPLETADO = "no_completado"  # cerrado con el año lectivo sin alcanzar el objetivo


class DesafioGrupal(Base):
    """
    Desafío grupal creado por profesor.
    
    Ejemplos:
    - "Resolver 100 problemas en una semana"
    - "Todos alcancen nivel 3"
    - "10 problemas consecutivos correctos"
    
    Relaciones:
    - Creado por un Profesor (N:1)
    - Pertenece a un AnioLectivo (N:1): siempre dentro de un mismo salón
    - Tiene uno o más equipos (GrupoDesafio): grupos del salón o el salón completo
    """
    __tablename__ = "desafio_grupal"
    
    id = Column(Integer, primary_key=True, index=True)
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False, index=True)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(100), nullable=False)  # problemas_resueltos | sesiones_completadas | practicas_sin_errores | problemas_rapidos | practicas_rapidas
    objetivo_cantidad = Column(Integer, nullable=False)   # Meta principal (X)
    parametro_adicional = Column(Integer, nullable=True)  # Parámetro secundario (Y): max errores / seg por problema / min por práctica
    recompensa_texto = Column(Text, nullable=True)        # Descripción de recompensa física (opcional)
    recompensa_puntos = Column(Integer, nullable=True)    # XP otorgados al completar (opcional, alternativa o complemento al texto)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_limite = Column(DateTime, nullable=True)
    # activo | completado | no_completado (cerrado con el año lectivo sin terminar)
    estado = Column(String(20), nullable=False, default=DESAFIO_ACTIVO, server_default=DESAFIO_ACTIVO)
    eliminado = Column(Boolean, default=False, nullable=False)  # Soft delete
    
    # Relaciones
    profesor = relationship("Profesor", back_populates="desafios_grupales")
    anio_lectivo = relationship("AnioLectivo")
    grupos = relationship("GrupoDesafio", back_populates="desafio")

    __table_args__ = (
        CheckConstraint(
            "estado IN ('activo', 'completado', 'no_completado')", name="ck_desafio_estado"
        ),
    )

    @property
    def completado(self) -> bool:
        return self.estado == DESAFIO_COMPLETADO

    def __repr__(self):
        return f"<DesafioGrupal(id={self.id}, nombre={self.nombre}, tipo={self.tipo})>"


class GrupoDesafio(Base):
    """
    Equipo de un desafío con su progreso.

    Relaciones:
    - Pertenece a un DesafioGrupal (N:1)
    - Pertenece a un Grupo (N:1), o a ninguno: grupo_id NULL = el salón completo
    """
    __tablename__ = "grupo_desafio"

    id = Column(Integer, primary_key=True, index=True)
    desafio_id = Column(Integer, ForeignKey("desafio_grupal.id"), nullable=False, index=True)
    grupo_id = Column(Integer, ForeignKey("grupo.id"), nullable=True, index=True)
    progreso_actual = Column(Integer, nullable=False, default=0)
    puntos_otorgados = Column(Boolean, default=False, nullable=False)  # Evita otorgar XP más de una vez
    
    # Relaciones
    desafio = relationship("DesafioGrupal", back_populates="grupos")
    grupo = relationship("Grupo", back_populates="desafios")

    __table_args__ = (
        UniqueConstraint("desafio_id", "grupo_id", name="uq_grupo_desafio"),
        # Un solo equipo "salón completo" por desafío (los NULL no chocan en el UNIQUE normal)
        Index(
            "uq_grupo_desafio_salon_completo",
            "desafio_id",
            unique=True,
            postgresql_where=text("grupo_id IS NULL"),
        ),
    )
    
    def __repr__(self):
        return f"<GrupoDesafio(desafio_id={self.desafio_id}, grupo_id={self.grupo_id}, progreso={self.progreso_actual})>"

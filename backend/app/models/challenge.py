"""
Modelos de desafíos grupales.

DesafioGrupal: Retos para grupos completos (ej: "Resolver 100 problemas entre todos").
GrupoDesafio: Tabla asociativa para tracking de progreso por grupo.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class DesafioGrupal(Base):
    """
    Desafío grupal creado por profesor.
    
    Ejemplos:
    - "Resolver 100 problemas en una semana"
    - "Todos alcancen nivel 3"
    - "10 problemas consecutivos correctos"
    
    Relaciones:
    - Creado por un Profesor (N:1)
    - Asignado a múltiples Grupos (N:M via GrupoDesafio)
    """
    __tablename__ = "desafio_grupal"
    
    id = Column(Integer, primary_key=True, index=True)
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(100), nullable=False)  # problemas_resueltos | sesiones_completadas | practicas_sin_errores | problemas_rapidos | practicas_rapidas
    objetivo_cantidad = Column(Integer, nullable=False)   # Meta principal (X)
    parametro_adicional = Column(Integer, nullable=True)  # Parámetro secundario (Y): max errores / seg por problema / min por práctica
    recompensa_texto = Column(Text, nullable=True)        # Descripción de recompensa física (opcional)
    recompensa_puntos = Column(Integer, nullable=True)    # XP otorgados al completar (opcional, alternativa o complemento al texto)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_limite = Column(DateTime, nullable=True)
    completado = Column(Boolean, default=False, nullable=False)
    eliminado = Column(Boolean, default=False, nullable=False)  # Soft delete
    
    # Relaciones
    profesor = relationship("Profesor", back_populates="desafios_grupales")
    grupos = relationship("GrupoDesafio", back_populates="desafio")
    
    def __repr__(self):
        return f"<DesafioGrupal(id={self.id}, nombre={self.nombre}, tipo={self.tipo})>"


class GrupoDesafio(Base):
    """
    Tabla asociativa para tracking de progreso de desafíos grupales.
    
    Almacena el progreso actual de cada grupo en un desafío.
    
    Relaciones:
    - Pertenece a un DesafioGrupal (N:1)
    - Pertenece a un Grupo (N:1)
    """
    __tablename__ = "grupo_desafio"
    
    desafio_id = Column(Integer, ForeignKey("desafio_grupal.id"), primary_key=True)
    grupo_id = Column(Integer, ForeignKey("grupo.id"), primary_key=True)
    progreso_actual = Column(Integer, nullable=False, default=0)
    puntos_otorgados = Column(Boolean, default=False, nullable=False)  # Evita otorgar XP más de una vez
    
    # Relaciones
    desafio = relationship("DesafioGrupal", back_populates="grupos")
    grupo = relationship("Grupo", back_populates="desafios")
    
    def __repr__(self):
        return f"<GrupoDesafio(desafio_id={self.desafio_id}, grupo_id={self.grupo_id}, progreso={self.progreso_actual})>"

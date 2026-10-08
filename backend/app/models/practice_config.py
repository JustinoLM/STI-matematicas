"""Modelo de configuración de prácticas por grupo."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConfiguracionPractica(Base):
    """Configuración de práctica aplicada a un grupo."""
    
    __tablename__ = "configuracion_practica"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("grupo.id"), nullable=False, index=True)
    aplicada_por_profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False)
    
    operaciones_permitidas = Column(JSON, nullable=False)
    niveles_permitidos = Column(JSON, nullable=False)
    
    rango_min = Column(Numeric(10, 3), nullable=False, default=0)
    rango_max = Column(Numeric(10, 3), nullable=False, default=100)
    decimales_maximos = Column(Integer, nullable=False, default=2)
    
    pistas_habilitadas = Column(JSON, nullable=False)
    
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
    
    grupo = relationship("Grupo", back_populates="configuraciones_practica")
    aplicada_por_profesor = relationship("Profesor", back_populates="configuraciones")
    
    def __repr__(self):
        return f"<ConfiguracionPractica(id={self.id}, grupo_id={self.grupo_id})>"

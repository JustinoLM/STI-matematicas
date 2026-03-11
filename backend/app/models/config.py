"""
Modelo para configuración global del sistema.

Tabla de clave-valor para parámetros persistentes como
la fecha del último entrenamiento ML.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime

from app.core.database import Base


class ConfiguracionSistema(Base):
    """
    Tabla de configuración clave-valor del sistema.

    Ejemplos de claves:
      - "ml_ultimo_entrenamiento" → ISO datetime del último ciclo K-Means
    """
    __tablename__ = "configuracion_sistema"

    clave = Column(String(100), primary_key=True)
    valor = Column(String(500), nullable=True)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ConfiguracionSistema(clave={self.clave!r}, valor={self.valor!r})>"

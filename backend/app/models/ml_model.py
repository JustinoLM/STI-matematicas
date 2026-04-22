"""
Modelo SQLAlchemy para persistir modelos ML entrenados en PostgreSQL.

Almacena los bytes serializados de los modelos scikit-learn (KMeans, scaler,
LogisticRegression) en columnas LargeBinary para sobrevivir reinicios del servidor.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)

from app.core.database import Base


class ModeloML(Base):
    """
    Persistencia de modelos ML entrenados.

    Filas típicas:
      - nombre="clustering", org_id=1  → KMeans + StandardScaler de org 1
      - nombre="prediccion", org_id=NULL → LogisticRegression global
    """

    __tablename__ = "modelo_ml"

    id = Column(Integer, primary_key=True, index=True)

    # "clustering" o "prediccion"
    nombre = Column(String(50), nullable=False)

    # NULL para modelos globales (prediccion)
    org_id = Column(
        Integer,
        ForeignKey("organizacion.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Bytes serializados con pickle
    modelo_bytes = Column(LargeBinary, nullable=False)

    # Solo para clustering (StandardScaler)
    scaler_bytes = Column(LargeBinary, nullable=True)

    # Metadata
    entrenado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    perfiles_entrenados = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("nombre", "org_id", name="uq_modelo_ml_nombre_org"),
    )

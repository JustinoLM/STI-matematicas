"""
Currículo como datos: catálogo de lecciones, caminos y grafo de prerrequisitos por defecto.

La fuente de verdad es backend/curriculo/programa_meduca.yaml; estas tablas las escribe solo el
cargador (app/services/curriculo_service.py). Diseño: docs/DISENO_MODULAR.md, sección 1.

- CaminoCurricular: conjunto numérico + habilidad (por ejemplo "naturales.suma").
- LeccionCurricular: una lección del programa de MEDUCA, incluida o no en el STI. Su id es
  permanente: el dominio, la habilitación y la asignación individual apuntarán a él.
- LeccionCamino: una lección puede pertenecer a varios caminos ("Sumemos y restemos 3 números").
- PrerrequisitoDefecto: el grafo por defecto. Las ediciones del profesor (fase 6) irán en una
  tabla aparte por año lectivo, así una nueva carga del archivo nunca las pisa.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# Valores admitidos (texto validado por el cargador, no enum de PostgreSQL)
PRESENTACIONES_ESPECIALES = ("semirrecta", "cinta")
CUBIERTA_POR = ("sistema_decimales", "modulo_regla_de_tres")


class CaminoCurricular(Base):
    __tablename__ = "curriculo_camino"

    id = Column(String(60), primary_key=True)          # "naturales.suma"
    conjunto = Column(String(30), nullable=False)       # naturales, decimales, fracciones, ...
    habilidad = Column(String(30), nullable=False)      # numeracion, suma, resta, ...
    nombre = Column(String(120), nullable=False)
    orden = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("conjunto", "habilidad", name="uq_curriculo_camino_conjunto_habilidad"),
    )

    def __repr__(self):
        return f"<CaminoCurricular(id={self.id})>"


class LeccionCurricular(Base):
    __tablename__ = "curriculo_leccion"

    id = Column(String(30), primary_key=True)           # "g1-u03-l01", permanente
    grado = Column(Integer, nullable=False, index=True)
    unidad_numero = Column(Integer, nullable=False)
    unidad_titulo = Column(String(200), nullable=False)
    leccion_numero = Column(Integer, nullable=False)
    leccion_titulo = Column(String(200), nullable=False)
    orden_programa = Column(Integer, nullable=False)
    incluida = Column(Boolean, nullable=False)
    motivo_exclusion = Column(Text, nullable=True)
    parcial = Column(Boolean, nullable=False, default=False, server_default="false")
    nota_parcial = Column(Text, nullable=True)
    presentacion_especial = Column(String(30), nullable=True)
    cubierta_por = Column(String(40), nullable=True)
    notas = Column(Text, nullable=True)

    caminos = relationship(
        "CaminoCurricular", secondary="curriculo_leccion_camino",
        order_by="CaminoCurricular.orden", viewonly=True,
    )

    __table_args__ = (
        # Diferibles: al reordenar el programa, dos lecciones intercambian valores en la misma carga
        UniqueConstraint("orden_programa", name="uq_curriculo_leccion_orden",
                         deferrable=True, initially="DEFERRED"),
        UniqueConstraint("grado", "unidad_numero", "leccion_numero", name="uq_curriculo_leccion_numeracion",
                         deferrable=True, initially="DEFERRED"),
        CheckConstraint("grado BETWEEN 1 AND 6", name="ck_curriculo_leccion_grado"),
        CheckConstraint("incluida OR motivo_exclusion IS NOT NULL", name="ck_curriculo_leccion_motivo"),
        CheckConstraint("NOT parcial OR nota_parcial IS NOT NULL", name="ck_curriculo_leccion_parcial"),
    )

    def __repr__(self):
        return f"<LeccionCurricular(id={self.id}, incluida={self.incluida})>"


class LeccionCamino(Base):
    __tablename__ = "curriculo_leccion_camino"

    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id", ondelete="CASCADE"), primary_key=True)
    camino_id = Column(String(60), ForeignKey("curriculo_camino.id"), primary_key=True, index=True)


class PrerrequisitoDefecto(Base):
    __tablename__ = "curriculo_prerrequisito"

    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id", ondelete="CASCADE"), primary_key=True)
    prerrequisito_id = Column(String(30), ForeignKey("curriculo_leccion.id"), primary_key=True, index=True)

    __table_args__ = (
        CheckConstraint("leccion_id <> prerrequisito_id", name="ck_curriculo_prerrequisito_propio"),
    )

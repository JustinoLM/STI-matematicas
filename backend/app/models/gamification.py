"""
Modelos de gamificación.

Sistema de puntos, medallas, desbloqueables y personalización.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class CategoriaDesbloqueable(str, enum.Enum):
    """Categorías de items desbloqueables."""
    TEMA = "tema"
    FONDO = "fondo"
    COLOR = "color"
    MUSICA = "musica"
    EFECTO = "efecto"


class CategoriaMedalla(str, enum.Enum):
    """Categorías de medallas."""
    APRENDIZAJE = "aprendizaje"
    VOLUMEN = "volumen"
    EXPLORACION = "exploracion"
    DESAFIOS = "desafios"


class TipoTransaccion(str, enum.Enum):
    """Tipos de transacciones de puntos."""
    GANANCIA = "ganancia"
    GASTO = "gasto"


class Desbloqueable(Base):
    """
    Catálogo de items que los estudiantes pueden comprar.
    
    Incluye temas, fondos, colores, músicas y efectos.
    """
    __tablename__ = "desbloqueable"
    
    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(Enum(CategoriaDesbloqueable, values_callable=lambda x: [e.value for e in x]), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    precio_puntos = Column(Integer, nullable=False)
    nivel_minimo_requerido = Column(Integer, default=1)
    
    # Path del asset (música, imagen de fondo, etc.)
    # Ejemplo: "themes/pirates/background.png"
    archivo_referencia = Column(String(255), nullable=True)
    
    # Para ordenar en la tienda
    orden = Column(Integer, default=0)
    
    # Para temas que son gratis inicialmente
    es_tema_inicial = Column(Boolean, default=False)
    
    # Metadata
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True)
    
    # Relaciones
    estudiantes_que_lo_poseen = relationship(
        "EstudianteDesbloqueable",
        back_populates="desbloqueable"
    )
    
    def __repr__(self):
        return f"<Desbloqueable {self.nombre} ({self.categoria.value})>"


class EstudianteDesbloqueable(Base):
    """
    Relación entre estudiantes y items que han comprado.
    """
    __tablename__ = "estudiante_desbloqueable"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    desbloqueable_id = Column(Integer, ForeignKey("desbloqueable.id"), nullable=False)
    
    # Histórico
    fecha_compra = Column(DateTime, default=datetime.utcnow)
    puntos_gastados = Column(Integer, nullable=False)  # Precio al momento de compra
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="desbloqueables")
    desbloqueable = relationship("Desbloqueable", back_populates="estudiantes_que_lo_poseen")

    def __repr__(self):
        return f"<EstudianteDesbloqueable estudiante={self.estudiante_id} item={self.desbloqueable_id}>"


class PersonalizacionEstudiante(Base):
    """
    Configuración activa de personalización del estudiante.
    
    Guarda qué tema, fondo, colores y música tiene activados actualmente.
    """
    __tablename__ = "personalizacion_estudiante"
    
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    
    # Items activos
    tema_activo_id = Column(Integer, ForeignKey("desbloqueable.id"), nullable=True)
    fondo_activo_id = Column(Integer, ForeignKey("desbloqueable.id"), nullable=True)
    musica_activa_id = Column(Integer, ForeignKey("desbloqueable.id"), nullable=True)
    
    # Colores (guardados directamente como hex)
    color_fondo = Column(String(7), default="#FFFFFF")  # Hex color
    color_texto = Column(String(7), default="#000000")
    color_botones = Column(String(7), default="#007AFF")
    
    # Efectos activos (lista de IDs de desbloqueables tipo EFECTO)
    efectos_activos = Column(JSON, default=list)

    # Medalla destacada en el dashboard
    medalla_destacada_id = Column(Integer, ForeignKey("medalla.id"), nullable=True)

    # Metadata
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PersonalizacionEstudiante estudiante={self.estudiante_id}>"


class Medalla(Base):
    """
    Catálogo de medallas/logros que los estudiantes pueden ganar.
    """
    __tablename__ = "medalla"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=False)
    categoria = Column(Enum(CategoriaMedalla, values_callable=lambda x: [e.value for e in x]), nullable=False)
    
    # Criterio de obtención (JSON con condiciones)
    # Ejemplo: {"tipo": "nivel", "operacion": "suma", "nivel": 3}
    # Ejemplo: {"tipo": "volumen", "cantidad": 100}
    criterio = Column(JSON, nullable=False)
    
    # Path de la imagen de la medalla
    imagen_url = Column(String(255), nullable=True)
    
    # Para ordenar en la galería
    orden = Column(Integer, default=0)

    # Si es True, el nombre/descripción se ocultan hasta que el estudiante la gana
    es_secreta = Column(Boolean, default=False)

    # Metadata
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    activa = Column(Boolean, default=True)
    
    # Relaciones
    estudiantes_que_la_ganaron = relationship(
        "EstudianteMedalla",
        back_populates="medalla"
    )
    
    def __repr__(self):
        return f"<Medalla {self.nombre}>"


class EstudianteMedalla(Base):
    """
    Relación entre estudiantes y medallas que han ganado.
    """
    __tablename__ = "estudiante_medalla"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    medalla_id = Column(Integer, ForeignKey("medalla.id"), nullable=False)
    
    # Cuándo la ganó
    fecha_obtencion = Column(DateTime, default=datetime.utcnow)
    
    # Si ya se le notificó (para push notifications)
    notificada = Column(Boolean, default=False)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="medallas")
    medalla = relationship("Medalla", back_populates="estudiantes_que_la_ganaron")

    def __repr__(self):
        return f"<EstudianteMedalla estudiante={self.estudiante_id} medalla={self.medalla_id}>"


class TransaccionPuntos(Base):
    """
    Historial de transacciones de puntos (auditoría).
    
    Registra cada ganancia o gasto de puntos.
    """
    __tablename__ = "transaccion_puntos"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    
    tipo = Column(Enum(TipoTransaccion, values_callable=lambda x: [e.value for e in x]), nullable=False)
    cantidad = Column(Integer, nullable=False)
    concepto = Column(String(255), nullable=False)
    
    # Referencias opcionales
    sesion_id = Column(Integer, ForeignKey("sesion_practica.id"), nullable=True)
    desbloqueable_id = Column(Integer, ForeignKey("desbloqueable.id"), nullable=True)
    
    # Saldo después de la transacción
    saldo_resultante = Column(Integer, nullable=False)
    
    fecha = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<TransaccionPuntos {self.tipo.value} {self.cantidad} pts>"

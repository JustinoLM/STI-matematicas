"""
Modelos ORM para funcionalidades LLM.

Tablas de caché para contenido generado con DeepSeek:
- EnunciadoTematico: narrativas de problemas (caché permanente)
- MensajeMotivacional: mensajes del dashboard/progreso (caché diaria)
- AnimacionGuardada: colección de animaciones paso a paso (máx 10 por estudiante)
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Text, DateTime, Date, ForeignKey, Index, UniqueConstraint

from app.core.database import Base


class EnunciadoTematico(Base):
    """
    Caché permanente de enunciados narrativos temáticos.

    PK compuesta: (signature × tema × nivel)
    - signature: hash único del Problema (Problema.signature)
    - tema:      nombre normalizado, ej. "tema-piratas", "tema-astronautas"
    - nivel:     nivel de dificultad 1-5

    Un enunciado se genera UNA SOLA VEZ con DeepSeek V3 y se reutiliza
    para todos los estudiantes que compartan el mismo tema activo.
    """

    __tablename__ = "enunciado_tematico"

    signature = Column(String(64), primary_key=True)
    tema = Column(String(100), primary_key=True)
    nivel = Column(Integer, primary_key=True)
    texto = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<EnunciadoTematico("
            f"sig={self.signature[:8]}…, tema={self.tema}, nivel={self.nivel})>"
        )


class MensajeMotivacional(Base):
    """
    Caché diaria de mensajes motivacionales generados con DeepSeek V3.

    Un mensaje se genera UNA VEZ por día por estudiante y tipo.
    Tipos:
      - "dashboard": bienvenida en el panel principal
      - "progreso":  motivación en la página de progreso

    La clave de caché es (estudiante_id, tipo, fecha, tema).
    Si el estudiante cambia de tema, se genera un nuevo mensaje ese día.
    """

    __tablename__ = "mensaje_motivacional"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estudiante_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    tipo = Column(String(20), nullable=False)      # "dashboard" | "progreso"
    texto = Column(Text, nullable=False)
    fecha = Column(Date, nullable=False)           # fecha local (cache key diario)
    tema = Column(String(100), nullable=True)      # tema activo normalizado (None = sin tema)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_mensaje_mot_lookup", "estudiante_id", "tipo", "fecha", "tema"),
    )

    def __repr__(self) -> str:
        return f"<MensajeMotivacional(est={self.estudiante_id}, tipo={self.tipo}, fecha={self.fecha})>"


class AnimacionGuardada(Base):
    """
    Colección de animaciones paso a paso guardadas por el estudiante.

    Se genera automáticamente tras agotar los 3 intentos de un problema.
    El estudiante puede guardar hasta 10 animaciones (se elimina la más
    antigua automáticamente si se alcanza el límite).

    Los datos del problema se desnormalizan para poder re-renderizar
    la animación sin necesidad de joins adicionales.
    """

    __tablename__ = "animacion_guardada"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estudiante_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    problema_id = Column(Integer, ForeignKey("problema.id"), nullable=False)
    operacion = Column(String(20), nullable=False)      # SUMA | RESTA | MULTIPLICACION | DIVISION
    numero1 = Column(String(30), nullable=False)        # desnormalizado para render
    numero2 = Column(String(30), nullable=False)        # desnormalizado para render
    nivel_dificultad = Column(Integer, nullable=False)
    guardado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("estudiante_id", "problema_id", name="uq_animacion_est_problema"),
        Index("ix_animacion_guardada_estudiante", "estudiante_id"),
    )

    def __repr__(self) -> str:
        return f"<AnimacionGuardada(est={self.estudiante_id}, op={self.operacion}, prob={self.problema_id})>"

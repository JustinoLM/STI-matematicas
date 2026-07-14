"""
Modelos del módulo de Regla de Tres (proporciones directa/inversa).

Módulo paralelo e independiente al sistema de las 4 operaciones base:
tiene su propio perfil adaptativo, sus propias sesiones de práctica y
sus propios problemas. No se relaciona con Operacion, PerfilEstudiante,
PruebaDiagnostica ni ResultadoPostTest.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, JSON, ForeignKey, Enum
import enum

from app.core.database import Base
from app.models.adaptive import EstadoSesion


class TipoProporcion(str, enum.Enum):
    """Tipo de proporción de un problema de regla de tres."""
    DIRECTA = "directa"
    INVERSA = "inversa"


class ProblemaReglaTres(Base):
    """
    Problema de regla de tres: a : b :: c : x (se conocen a, b, c; se despeja x).

    Directa:  x = (b * c) / a
    Inversa:  x = (a * b) / c

    Único por signature, igual que Problema (4 operaciones).
    """
    __tablename__ = "problema_regla_tres"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoProporcion, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    numero1 = Column(Numeric(10, 3), nullable=False)  # a
    numero2 = Column(Numeric(10, 3), nullable=False)  # b
    numero3 = Column(Numeric(10, 3), nullable=False)  # c
    resultado = Column(Numeric(10, 3), nullable=False)  # x
    nivel_dificultad = Column(Integer, nullable=False, index=True)  # 1-5
    cantidad_decimales = Column(Integer, nullable=False)
    signature = Column(String(64), unique=True, nullable=False, index=True)
    fecha_generacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProblemaReglaTres(id={self.id}, tipo={self.tipo}, nivel={self.nivel_dificultad})>"


class PerfilReglaTres(Base):
    """
    Perfil adaptativo del estudiante para regla de tres.

    Una sola dimensión de nivel (1-5), sin prerequisitos cruzados
    ni columnas por operación — más simple que PerfilEstudiante.
    """
    __tablename__ = "perfil_regla_tres"

    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)

    nivel_actual = Column(Integer, default=1, nullable=False)
    consecutivas_correctas = Column(Integer, default=0, nullable=False)
    total_practicados = Column(Integer, default=0, nullable=False)

    fecha_ultima_practica = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PerfilReglaTres(estudiante_id={self.estudiante_id}, nivel_actual={self.nivel_actual})>"


class SesionPracticaReglaTres(Base):
    """Sesión de práctica de regla de tres."""
    __tablename__ = "sesion_practica_regla_tres"

    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)

    estado = Column(
        Enum(EstadoSesion, values_callable=lambda x: [e.value for e in x]),
        default=EstadoSesion.INICIADA,
        nullable=False,
    )
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)

    nivel_al_iniciar = Column(Integer, nullable=False)
    cantidad_problemas = Column(Integer, nullable=False)
    problemas_ids = Column(JSON, nullable=False)  # lista ordenada de ids
    progreso_actual = Column(Integer, default=0, nullable=False)  # índice 0-based

    problemas_correctos = Column(Integer, default=0, nullable=False)
    problemas_incorrectos = Column(Integer, default=0, nullable=False)
    puntos_ganados = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<SesionPracticaReglaTres(id={self.id}, estudiante_id={self.estudiante_id}, estado={self.estado})>"


class IntentoReglaTres(Base):
    """Intento de resolución de un problema de regla de tres."""
    __tablename__ = "intento_regla_tres"

    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesion_practica_regla_tres.id"), nullable=False, index=True)
    problema_id = Column(Integer, ForeignKey("problema_regla_tres.id"), nullable=False, index=True)
    respuesta_estudiante = Column(Numeric(10, 3), nullable=False)
    es_correcto = Column(Boolean, nullable=False, index=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<IntentoReglaTres(id={self.id}, sesion_id={self.sesion_id}, correcto={self.es_correcto})>"

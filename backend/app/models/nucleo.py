"""
Núcleo de práctica (fase 3b): habilitación, asignación individual, dominio, sesión, intentos,
eventos y experiencia. Diseño: docs/DISENO_MODULAR.md.

Va en paralelo al sistema de decimales: no comparte tablas con sesion_practica, problema ni
intento. Los estados son texto con CHECK (como en school.py), no tipos ENUM de PostgreSQL.

- NucleoHabilitacion: lección habilitada en el año lectivo de un salón, con su configuración
  (signo, íconos, pistas por nivel y prioridad). Deshabilitar conserva la fila.
- NucleoAsignacion: lección asignada solo a un estudiante; se cierra sola al dominarla.
- NucleoAjusteEstudiante: adaptaciones por estudiante (banco forzado).
- NucleoDominio: estado del estudiante en una lección. Sin fila = no iniciada.
- NucleoExtension: pausa de la zona de extensión por estudiante y lección.
- NucleoSesion / NucleoProblemaSesion / NucleoIntento / NucleoEvento: la práctica.
- NucleoExperiencia: experiencia acumulada, aparte del saldo de puntos.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
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

# ─── Valores admitidos ───────────────────────────────────────────────────────

MODOS = ("siempre", "nunca", "azar")

ASIGNACION_ACTIVA = "activa"
ASIGNACION_CERRADA = "cerrada_por_dominio"
ASIGNACION_CANCELADA = "cancelada"

DOMINIO_EN_PROGRESO = "en_progreso"
DOMINIO_DOMINADO = "dominado"
DOMINIO_PROVISIONAL = "dominado_provisional"   # lo marca el diagnóstico (fase 7)
NO_INICIADO = "no_iniciado"                    # sin fila en nucleo_dominio

SESION_ACTIVA = "activa"
SESION_COMPLETADA = "completada"
SESION_ABANDONADA = "abandonada"

ZONA_PRIORIDAD = "prioridad"
ZONA_NORMAL = "normal"
ZONA_REPASO = "repaso"
ZONA_EXTENSION = "extension"
ZONA_REFUERZO = "refuerzo"
ZONAS = (ZONA_PRIORIDAD, ZONA_NORMAL, ZONA_REPASO, ZONA_EXTENSION, ZONA_REFUERZO)

PROBLEMA_PENDIENTE = "pendiente"
PROBLEMA_TERMINADO = "terminado"

XP_PRACTICA = "practica"
XP_ACIERTO = "acierto"
XP_LECCION_DOMINADA = "leccion_dominada"


def _en(valores) -> str:
    return "(" + ", ".join(f"'{v}'" for v in valores) + ")"


# ─── Profesor: habilitación, asignación y ajustes ────────────────────────────

class NucleoHabilitacion(Base):
    __tablename__ = "nucleo_habilitacion"

    id = Column(Integer, primary_key=True)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), nullable=False)
    habilitada = Column(Boolean, nullable=False, default=True, server_default="true")
    signo = Column(String(10), nullable=False, default="siempre", server_default="siempre")
    iconos = Column(String(10), nullable=False, default="siempre", server_default="siempre")
    pistas = Column(JSON, nullable=False)          # {"1": true, "2": true, "3": true}
    prioritaria = Column(Boolean, nullable=False, default=False, server_default="false")
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("anio_lectivo_id", "leccion_id", name="uq_nucleo_habilitacion_anio_leccion"),
        CheckConstraint(f"signo IN {_en(MODOS)}", name="ck_nucleo_habilitacion_signo"),
        CheckConstraint(f"iconos IN {_en(MODOS)}", name="ck_nucleo_habilitacion_iconos"),
        CheckConstraint("habilitada OR NOT prioritaria", name="ck_nucleo_habilitacion_prioritaria"),
    )


class NucleoAsignacion(Base):
    __tablename__ = "nucleo_asignacion"

    id = Column(Integer, primary_key=True)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), nullable=False)
    estado = Column(String(25), nullable=False, default=ASIGNACION_ACTIVA, server_default=ASIGNACION_ACTIVA)
    profesor_id = Column(Integer, ForeignKey("profesor.id"), nullable=False)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_cierre = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"estado IN {_en((ASIGNACION_ACTIVA, ASIGNACION_CERRADA, ASIGNACION_CANCELADA))}",
            name="ck_nucleo_asignacion_estado",
        ),
        Index(
            "uq_nucleo_asignacion_activa", "estudiante_id", "leccion_id",
            unique=True, postgresql_where=text("estado = 'activa'"),
        ),
    )


class NucleoAjusteEstudiante(Base):
    __tablename__ = "nucleo_ajuste_estudiante"

    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    banco_forzado = Column(Boolean, nullable=False, default=False, server_default="false")
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ─── Dominio y extensión ─────────────────────────────────────────────────────

class NucleoDominio(Base):
    __tablename__ = "nucleo_dominio"

    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), primary_key=True, index=True)
    estado = Column(String(25), nullable=False)
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_dominio = Column(DateTime, nullable=True)     # última vez que pasó a dominado
    ultima_practica = Column(DateTime, nullable=True)   # último problema terminado (sin extensión)
    repaso_desde = Column(DateTime, nullable=True)      # inicio de la ventana de repaso en curso

    __table_args__ = (
        CheckConstraint(
            f"estado IN {_en((DOMINIO_EN_PROGRESO, DOMINIO_DOMINADO, DOMINIO_PROVISIONAL))}",
            name="ck_nucleo_dominio_estado",
        ),
    )


class NucleoExtension(Base):
    __tablename__ = "nucleo_extension"

    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), primary_key=True)
    contar_desde = Column(DateTime, nullable=True)      # los fallos se cuentan desde aquí
    pausada_hasta = Column(DateTime, nullable=True)


# ─── Sesión, problemas, intentos y eventos ───────────────────────────────────

class NucleoSesion(Base):
    __tablename__ = "nucleo_sesion"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    anio_lectivo_id = Column(Integer, ForeignKey("anio_lectivo.id"), nullable=False, index=True)
    estado = Column(String(15), nullable=False, default=SESION_ACTIVA, server_default=SESION_ACTIVA)
    plan = Column(JSON, nullable=False)                 # [{"leccion_id": ..., "zona": ...}, ...]
    cantidad_problemas = Column(Integer, nullable=False)
    progreso = Column(Integer, nullable=False, default=0, server_default="0")  # problemas terminados
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)

    problemas = relationship("NucleoProblemaSesion", back_populates="sesion", order_by="NucleoProblemaSesion.orden")

    __table_args__ = (
        CheckConstraint(
            f"estado IN {_en((SESION_ACTIVA, SESION_COMPLETADA, SESION_ABANDONADA))}",
            name="ck_nucleo_sesion_estado",
        ),
        CheckConstraint("progreso BETWEEN 0 AND cantidad_problemas", name="ck_nucleo_sesion_progreso"),
        Index("uq_nucleo_sesion_activa", "estudiante_id", unique=True,
              postgresql_where=text("estado = 'activa'")),
    )


class NucleoProblemaSesion(Base):
    """Un problema de la sesión. `acierto` es lo que cuenta para el dominio: correcto al primer
    intento y sin la pista de nivel 3."""

    __tablename__ = "nucleo_problema_sesion"

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("nucleo_sesion.id"), nullable=False)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    orden = Column(Integer, nullable=False)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), nullable=False)
    zona = Column(String(15), nullable=False)
    problema = Column(JSON, nullable=False)             # problema_a_dict(incluir_respuestas=True)
    estado = Column(String(15), nullable=False, default=PROBLEMA_PENDIENTE, server_default=PROBLEMA_PENDIENTE)
    intentos = Column(Integer, nullable=False, default=0, server_default="0")
    pista_max_nivel = Column(Integer, nullable=False, default=0, server_default="0")
    correcto = Column(Boolean, nullable=True)           # lo resolvió (en cualquier intento)
    acierto = Column(Boolean, nullable=True)            # cuenta como acierto para el dominio
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)

    sesion = relationship("NucleoSesion", back_populates="problemas")

    __table_args__ = (
        UniqueConstraint("sesion_id", "orden", name="uq_nucleo_problema_sesion_orden"),
        CheckConstraint(f"zona IN {_en(ZONAS)}", name="ck_nucleo_problema_sesion_zona"),
        CheckConstraint(f"estado IN {_en((PROBLEMA_PENDIENTE, PROBLEMA_TERMINADO))}",
                        name="ck_nucleo_problema_sesion_estado"),
        CheckConstraint("pista_max_nivel BETWEEN 0 AND 3", name="ck_nucleo_problema_sesion_pista"),
        Index("ix_nucleo_problema_sesion_resultados", "estudiante_id", "leccion_id", "fecha_fin"),
    )


class NucleoIntento(Base):
    __tablename__ = "nucleo_intento"

    id = Column(Integer, primary_key=True)
    problema_sesion_id = Column(Integer, ForeignKey("nucleo_problema_sesion.id"), nullable=False, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)            # 1, 2, 3
    respuestas = Column(JSON, nullable=False)           # tal como llegaron
    correcto = Column(Boolean, nullable=False)
    errores = Column(JSON, nullable=False)              # {hueco_id: código de regla} de los incorrectos
    pista_max_nivel = Column(Integer, nullable=False, default=0, server_default="0")
    tiempo_ms = Column(Integer, nullable=False)
    uso_voz = Column(Boolean, nullable=False, default=False, server_default="false")
    modo_respuesta = Column(String(10), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("problema_sesion_id", "numero", name="uq_nucleo_intento_numero"),
    )


class NucleoEvento(Base):
    """Registro de eventos de un problema: opción elegida, cambios de opción, voz, pistas."""

    __tablename__ = "nucleo_evento"

    id = Column(Integer, primary_key=True)
    problema_sesion_id = Column(Integer, ForeignKey("nucleo_problema_sesion.id"), nullable=False, index=True)
    intento_id = Column(Integer, ForeignKey("nucleo_intento.id"), nullable=True, index=True)
    tipo = Column(String(40), nullable=False)
    valor = Column(JSON, nullable=True)
    ms = Column(Integer, nullable=True)                 # ms desde que se mostró el problema
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)


# ─── Experiencia ─────────────────────────────────────────────────────────────

class NucleoExperiencia(Base):
    __tablename__ = "nucleo_experiencia"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)
    cantidad = Column(Integer, nullable=False)
    leccion_id = Column(String(30), ForeignKey("curriculo_leccion.id"), nullable=True)
    problema_sesion_id = Column(Integer, ForeignKey("nucleo_problema_sesion.id"), nullable=True)
    primera_vez = Column(Boolean, nullable=True)        # solo en leccion_dominada
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(f"tipo IN {_en((XP_PRACTICA, XP_ACIERTO, XP_LECCION_DOMINADA))}",
                        name="ck_nucleo_experiencia_tipo"),
        CheckConstraint("cantidad >= 0", name="ck_nucleo_experiencia_cantidad"),
    )

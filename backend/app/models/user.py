"""
Modelos de usuarios del sistema.

Sistema de autenticación basado en códigos únicos (no emails).
Los usuarios son creados por administradores, no hay registro público.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TipoUsuario(str, enum.Enum):
    """Enum para tipos de usuario."""
    ESTUDIANTE = "estudiante"
    PROFESOR = "profesor"


class Genero(str, enum.Enum):
    """Género del estudiante — usado para conjugación en mensajes LLM."""
    MASCULINO = "masculino"
    FEMENINO = "femenino"


class Usuario(Base):
    """
    Clase base para todos los usuarios del sistema.

    Autenticación: codigo único + password (sin email)
    """
    __tablename__ = "usuario"

    # Campos principales
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=True, index=True)  # Opcional para notificaciones
    password_hash = Column(String(255), nullable=False)
    password_plain = Column(String(100), nullable=True)   # MVP: contraseña en texto plano para admin
    tipo_usuario = Column(Enum(TipoUsuario), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    ultimo_acceso = Column(DateTime, nullable=True)
    activo = Column(Integer, default=1, nullable=False)  # 1=activo, 0=inactivo

    # Configuración de herencia
    __mapper_args__ = {
        "polymorphic_identity": "usuario",
        "polymorphic_on": tipo_usuario,
    }

    def __repr__(self):
        return f"<Usuario(id={self.id}, tipo={self.tipo_usuario})>"


class Estudiante(Usuario):
    """
    Modelo de estudiante.

    Login: codigo_estudiante + password
    """
    __tablename__ = "estudiante"

    id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    codigo_estudiante = Column(String(50), nullable=False, index=True)
    nombre_completo = Column(String(255), nullable=False)
    genero = Column(
        Enum(Genero, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        server_default=Genero.MASCULINO.value,
    )
    narrativa_seleccionada_id = Column(Integer, ForeignKey("narrativa.id"), nullable=True)
    organizacion_id = Column(Integer, ForeignKey("organizacion.id"), nullable=True)
    puntos_totales = Column(Integer, default=0, nullable=False, server_default="0")

    # Datos académicos y personales
    grado_academico = Column(String(50), nullable=True)   # Ej: "5to grado"
    anio_nacimiento = Column(Integer, nullable=True)      # Ej: 2014
    mes_nacimiento  = Column(Integer, nullable=True)      # 1-12

    # Relaciones
    narrativa = relationship("Narrativa", back_populates="estudiantes")
    perfil = relationship("PerfilEstudiante", back_populates="estudiante", uselist=False)
    grupos = relationship("EstudianteGrupo", back_populates="estudiante")
    intentos = relationship("Intento", back_populates="estudiante")
    estadisticas = relationship("EstadisticaEstudiante", back_populates="estudiante")
    medallas = relationship("EstudianteMedalla", back_populates="estudiante")
    desbloqueables = relationship("EstudianteDesbloqueable", back_populates="estudiante")
    diagnostico = relationship("PruebaDiagnostica", back_populates="estudiante", uselist=False)
    post_test = relationship("ResultadoPostTest", back_populates="estudiante", uselist=False)
    sesiones = relationship("SesionPractica", back_populates="estudiante")
    alertas = relationship("AlertaEstudiante", back_populates="estudiante")
    organizacion = relationship("Organizacion", back_populates="estudiantes", foreign_keys=[organizacion_id])

    # Unicidad por organización — mismo código puede existir en distintas orgs
    __table_args__ = (
        UniqueConstraint("codigo_estudiante", "organizacion_id", name="uq_estudiante_codigo_org"),
    )

    # Configuración de herencia
    __mapper_args__ = {
        "polymorphic_identity": TipoUsuario.ESTUDIANTE,
    }

    def __repr__(self):
        return f"<Estudiante(codigo={self.codigo_estudiante}, nombre={self.nombre_completo})>"


class Profesor(Usuario):
    """
    Modelo de profesor.

    Login: codigo_profesor + password
    """
    __tablename__ = "profesor"

    id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    codigo_profesor = Column(String(50), unique=True, nullable=False, index=True)
    nombre_completo = Column(String(255), nullable=False)
    institucion = Column(String(255), nullable=True)
    organizacion_id = Column(Integer, ForeignKey("organizacion.id"), nullable=True)
    grado_academico = Column(String(100), nullable=True)  # Ej: "Licenciatura", "Maestría"
    secciones_asignadas = Column(JSON, nullable=True)  # Ej: ["6A", "6B"] — secciones/grados que enseña

    # Relaciones
    grupos = relationship("Grupo", back_populates="profesor")
    configuraciones = relationship("ConfiguracionPractica", back_populates="aplicada_por_profesor")
    desafios_grupales = relationship("DesafioGrupal", back_populates="profesor")
    desafios_individuales = relationship("DesafioIndividual", back_populates="profesor")
    organizacion = relationship("Organizacion", back_populates="profesores", foreign_keys=[organizacion_id])

    # Configuración de herencia
    __mapper_args__ = {
        "polymorphic_identity": TipoUsuario.PROFESOR,
    }

    def __repr__(self):
        return f"<Profesor(codigo={self.codigo_profesor}, nombre={self.nombre_completo})>"

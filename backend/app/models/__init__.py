"""
Módulo de modelos SQLAlchemy.

Centraliza todos los modelos para facilitar importaciones.
"""

# Organization models (must be imported BEFORE user to resolve FK)
# Adaptive learning models
from app.models.adaptive import (
    AlertaEstudiante,
    EstadoDiagnostico,
    EstadoSesion,
    PerfilAprendizaje,
    PerfilEstudiante,
    PruebaDiagnostica,
    ResultadoPostTest,
    SesionPractica,
    TipoAlerta,
)

# Challenge models
from app.models.challenge import (
    DesafioGrupal,
    GrupoDesafio,
)

# Currículo como datos: caminos, lecciones y prerrequisitos por defecto
from app.models.curriculo import (
    CaminoCurricular,
    LeccionCamino,
    LeccionCurricular,
    PrerrequisitoDefecto,
)

# Error / Buggy Model
from app.models.error import (
    ErrorComun,
    EstudianteError,
)

# Gamification models
from app.models.gamification import (
    CategoriaDesbloqueable,
    CategoriaMedalla,
    Desbloqueable,
    EstudianteDesbloqueable,
    EstudianteMedalla,
    Medalla,
    PersonalizacionEstudiante,
    TipoTransaccion,
    TransaccionPuntos,
)

# Group models
from app.models.group import (
    EstudianteGrupo,
    Grupo,
)

# System configuration
# ML model persistence
from app.models.ml_model import ModeloML

# Hint (old video-pista system, referenced by Narrativa)
# Narrative models
from app.models.narrative import (
    Narrativa,
)

# Núcleo de práctica (fase 3b)
from app.models.nucleo import (
    NucleoAjusteEstudiante,
    NucleoAsignacion,
    NucleoDominio,
    NucleoEvento,
    NucleoExperiencia,
    NucleoExtension,
    NucleoHabilitacion,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.models.organization import (
    Organizacion,
)

# Practice Configuration models
from app.models.practice_config import (
    ConfiguracionPractica,
)

# Problem models
from app.models.problem import (
    Intento,
    Operacion,
    Problema,
)

# Regla de Tres models (módulo paralelo e independiente)
from app.models.regla_de_tres import (
    IntentoReglaTres,
    PerfilReglaTres,
    ProblemaReglaTres,
    SesionPracticaReglaTres,
    TipoProporcion,
)

# Organización escolar: salón, año lectivo, matrícula y trimestres
from app.models.school import (
    AnioLectivo,
    Matricula,
    Salon,
    Trimestre,
)

# User and authentication models
from app.models.user import (
    Estudiante,
    Profesor,
    TipoUsuario,
    Usuario,
)

__all__ = [
    # Organization
    "Organizacion",
    # User
    "TipoUsuario",
    "Usuario",
    "Estudiante",
    "Profesor",
    # Problem
    "Operacion",
    "Problema",
    "Intento",
    # Adaptive
    "PerfilAprendizaje",
    "EstadoDiagnostico",
    "TipoAlerta",
    "PerfilEstudiante",
    "PruebaDiagnostica",
    "ResultadoPostTest",
    "SesionPractica",
    "EstadoSesion",
    "AlertaEstudiante",
    # Regla de Tres
    "TipoProporcion",
    "ProblemaReglaTres",
    "PerfilReglaTres",
    "SesionPracticaReglaTres",
    "IntentoReglaTres",
    # Gamification
    "CategoriaDesbloqueable",
    "CategoriaMedalla",
    "TipoTransaccion",
    "Desbloqueable",
    "EstudianteDesbloqueable",
    "PersonalizacionEstudiante",
    "Medalla",
    "EstudianteMedalla",
    "TransaccionPuntos",
    # Organización escolar
    "Salon",
    "AnioLectivo",
    "Matricula",
    "Trimestre",
    # Currículo
    "CaminoCurricular",
    "LeccionCurricular",
    "LeccionCamino",
    "PrerrequisitoDefecto",
    # Núcleo de práctica
    "NucleoAjusteEstudiante",
    "NucleoAsignacion",
    "NucleoDominio",
    "NucleoEvento",
    "NucleoExperiencia",
    "NucleoExtension",
    "NucleoHabilitacion",
    "NucleoIntento",
    "NucleoProblemaSesion",
    "NucleoSesion",
    # Group
    "Grupo",
    "EstudianteGrupo",
    # Hint (old video-pista system)
    # Narrative
    "Narrativa",
    # Practice Configuration
    "ConfiguracionPractica",
    # Challenges
    "DesafioGrupal",
    "GrupoDesafio",
    # Error / Buggy Model
    "ErrorComun",
    "EstudianteError",
    # ML model persistence
    "ModeloML",
    # Pistas
    "NivelPista",
    "TipoError",
    "UsoPista",
    "GeneracionLLM",
    # LLM
    "EnunciadoTematico",
    "MensajeMotivacional",
    "AnimacionGuardada",
]

# Pistas
# Configuración del sistema (registra la tabla en Base.metadata)
from app.models.config import ConfiguracionSistema  # noqa: F401
from app.models.hints import (
    GeneracionLLM,
    NivelPista,
    TipoError,
    UsoPista,
)

# Caché de LLM y animaciones guardadas
from app.models.llm import (
    AnimacionGuardada,
    EnunciadoTematico,
    MensajeMotivacional,
)

"""
Módulo de modelos SQLAlchemy.

Centraliza todos los modelos para facilitar importaciones.
"""

# Organization models (must be imported BEFORE user to resolve FK)
from app.models.organization import (
    Organizacion,
)

# User and authentication models
from app.models.user import (
    TipoUsuario,
    Usuario,
    Estudiante,
    Profesor,
)

# Problem models
from app.models.problem import (
    Operacion,
    Problema,
    Intento,
)

# Adaptive learning models
from app.models.adaptive import (
    PerfilAprendizaje,
    EstadoDiagnostico,
    TipoAlerta,
    PerfilEstudiante,
    PruebaDiagnostica,
    ResultadoPostTest,
    SesionPractica,
    EstadoSesion,
    AlertaEstudiante,
    EstadisticaEstudiante,
)

# Gamification models
from app.models.gamification import (
    CategoriaDesbloqueable,
    CategoriaMedalla,
    TipoTransaccion,
    Desbloqueable,
    EstudianteDesbloqueable,
    PersonalizacionEstudiante,
    Medalla,
    EstudianteMedalla,
    TransaccionPuntos,
)

# Group models
from app.models.group import (
    Grupo,
    EstudianteGrupo,
)

# Hint (old video-pista system, referenced by Narrativa)
from app.models.hint import (
    VideoPista,
)

# Narrative models
from app.models.narrative import (
    Narrativa,
)

# Practice Configuration models
from app.models.practice_config import (
    ConfiguracionPractica,
)

# Challenge models
from app.models.challenge import (
    DesafioGrupal,
    GrupoDesafio,
    DesafioIndividual,
    EstudianteDesafioIndividual,
)

# Error / Buggy Model
from app.models.error import (
    ErrorComun,
    EstudianteError,
)

# System configuration
from app.models.config import ConfiguracionSistema

# ML model persistence
from app.models.ml_model import ModeloML

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
    "EstadisticaEstudiante",
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
    # Group
    "Grupo",
    "EstudianteGrupo",
    # Hint (old video-pista system)
    "VideoPista",
    # Narrative
    "Narrativa",
    # Practice Configuration
    "ConfiguracionPractica",
    # Challenges
    "DesafioGrupal",
    "GrupoDesafio",
    "DesafioIndividual",
    "EstudianteDesafioIndividual",
    # Error / Buggy Model
    "ErrorComun",
    "EstudianteError",
    # ML model persistence
    "ModeloML",
    # Hints and Videos
    "NivelPista",
    "TipoError",
    "FuenteVideo",
    "PistaGenerica",
    "UsoPista",
    "VideoEducativo",
    "VideoGuardado",
    "VideoTemporal",
    "GeneracionLLM",
]

# Hints and Videos models
from app.models.hints_videos import (
    NivelPista,
    TipoError,
    FuenteVideo,
    PistaGenerica,
    UsoPista,
    VideoEducativo,
    VideoGuardado,
    VideoTemporal,
    GeneracionLLM,
)

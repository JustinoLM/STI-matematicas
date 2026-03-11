from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.models.user import Usuario, Estudiante, Profesor, TipoUsuario
from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.problem_service import ProblemService
from app.services.adaptive_service import AdaptiveService
from app.repositories.practice_repository import PracticeRepository
from app.services.practice_service import PracticeService
from app.repositories.gamification_repository import GamificationRepository
from app.services.gamification_service import GamificationService
from app.repositories.hints_videos_repository import HintsVideosRepository
from app.repositories.enunciados_repository import EnunciadoTematicoRepository
from app.repositories.mensajes_repository import MensajesRepository
from app.services.llm_service import LLMService
from app.services.hints_service import HintsService
from app.services.enunciados_service import EnunciadosService
from app.services.mensajes_service import MensajesService
from app.services.videos_service import VideosService
from app.services.deteccion_errores_service import DeteccionErroresService
from app.services.analisis_service import AnalisisService
from app.repositories.animaciones_repository import AnimacionesRepository



"""
Dependencies de FastAPI para inyección de dependencias.

Proporciona sesión de BD, usuario actual, y verificación de roles.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.models.user import Usuario, Estudiante, Profesor, TipoUsuario

from app.repositories.problem_repository import ProblemRepository
from app.services.problem_service import ProblemService


# OAuth2 scheme para extraer token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================
# Dependencies de Base de Datos
# ============================================

async def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    """Dependency para obtener UserRepository."""
    return UserRepository(db)


async def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """Dependency para obtener AuthService."""
    return AuthService(user_repo)


# ============================================
# Dependencies de Autenticación
# ============================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> Usuario:
    """
    Dependency que obtiene el usuario actual desde el token JWT.
    
    Uso:
        @app.get("/protected")
        async def protected_route(user: Usuario = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    return await auth_service.get_current_user(token)


async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency que verifica que el usuario esté activo.
    
    Nota: Ya se verifica en get_current_user, pero se mantiene
    por compatibilidad con FastAPI patterns.
    """
    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return current_user


# ============================================
# Dependencies de Roles Específicos
# ============================================

async def get_current_student(
    current_user: Usuario = Depends(get_current_active_user)
) -> Estudiante:
    """
    Dependency que verifica que el usuario actual sea estudiante.
    
    Uso:
        @app.get("/student-only")
        async def student_route(student: Estudiante = Depends(get_current_student)):
            return {"estudiante": student.nombre_completo}
    """
    if not isinstance(current_user, Estudiante):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para estudiantes"
        )
    return current_user


async def get_current_teacher(
    current_user: Usuario = Depends(get_current_active_user)
) -> Profesor:
    """
    Dependency que verifica que el usuario actual sea profesor.
    
    Uso:
        @app.get("/teacher-only")
        async def teacher_route(teacher: Profesor = Depends(get_current_teacher)):
            return {"profesor": teacher.nombre_completo}
    """
    if not isinstance(current_user, Profesor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para profesores"
        )
    return current_user


# ============================================
# Type Aliases para anotaciones limpias
# ============================================

# Anotaciones tipo para usar en endpoints
CurrentUser = Annotated[Usuario, Depends(get_current_active_user)]
CurrentStudent = Annotated[Estudiante, Depends(get_current_student)]
CurrentTeacher = Annotated[Profesor, Depends(get_current_teacher)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ============================================
# Dependencies de Problem Service
# ============================================

async def get_problem_repository(
    db: AsyncSession = Depends(get_db)
) -> ProblemRepository:
    return ProblemRepository(db)


async def get_problem_service(
    problem_repo: ProblemRepository = Depends(get_problem_repository)
) -> ProblemService:
    return ProblemService(problem_repo)



# Type alias para ProblemService
ProblemServiceDep = Annotated[ProblemService, Depends(get_problem_service)]


# ============================================
# Dependencies de Adaptive Service
# ============================================

async def get_adaptive_repository(
    db: AsyncSession = Depends(get_db)
) -> AdaptiveRepository:
    """Dependency para obtener AdaptiveRepository."""
    return AdaptiveRepository(db)


async def get_adaptive_service(
    adaptive_repo: AdaptiveRepository = Depends(get_adaptive_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    problem_service: ProblemService = Depends(get_problem_service)
) -> AdaptiveService:
    """Dependency para obtener AdaptiveService."""
    return AdaptiveService(adaptive_repo, problem_repo, problem_service)


# Type alias para AdaptiveService
AdaptiveServiceDep = Annotated[AdaptiveService, Depends(get_adaptive_service)]


# ============================================
# Dependencies de Practice Service
# ============================================

async def get_practice_repository(
    db: AsyncSession = Depends(get_db)
) -> PracticeRepository:
    """Dependency para obtener PracticeRepository."""
    return PracticeRepository(db)


async def get_practice_service(
    practice_repo: PracticeRepository = Depends(get_practice_repository),
    adaptive_repo: AdaptiveRepository = Depends(get_adaptive_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository)
) -> PracticeService:
    """Dependency para obtener PracticeService."""
    return PracticeService(practice_repo, adaptive_repo, problem_repo)


# Type alias para PracticeService
PracticeServiceDep = Annotated[PracticeService, Depends(get_practice_service)]


# ============================================
# Dependencies de Gamification Service
# ============================================

async def get_gamification_repository(
    db: AsyncSession = Depends(get_db)
) -> GamificationRepository:
    """Dependency para obtener GamificationRepository."""
    return GamificationRepository(db)


async def get_gamification_service(
    gamification_repo: GamificationRepository = Depends(get_gamification_repository),
    adaptive_repo: AdaptiveRepository = Depends(get_adaptive_repository)
) -> GamificationService:
    """Dependency para obtener GamificationService."""
    return GamificationService(gamification_repo, adaptive_repo)


# Type alias para GamificationService
GamificationServiceDep = Annotated[GamificationService, Depends(get_gamification_service)]


# ============================================
# Dependencies de Hints & Videos Services
# ============================================

async def get_hints_videos_repository(
    db: AsyncSession = Depends(get_db)
) -> HintsVideosRepository:
    """Dependency para obtener HintsVideosRepository."""
    return HintsVideosRepository(db)


async def get_llm_service() -> LLMService:
    """Dependency para obtener LLMService (DeepSeek API)."""
    return LLMService()


async def get_hints_service(
    hints_videos_repo: HintsVideosRepository = Depends(get_hints_videos_repository),
    gamification_repo: GamificationRepository = Depends(get_gamification_repository),
    adaptive_repo: AdaptiveRepository = Depends(get_adaptive_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> HintsService:
    """Dependency para obtener HintsService."""
    return HintsService(hints_videos_repo, gamification_repo, adaptive_repo, llm_service)


async def get_enunciados_repository(
    db: AsyncSession = Depends(get_db)
) -> EnunciadoTematicoRepository:
    """Dependency para obtener EnunciadoTematicoRepository."""
    return EnunciadoTematicoRepository(db)


async def get_enunciados_service(
    enunciados_repo: EnunciadoTematicoRepository = Depends(get_enunciados_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> EnunciadosService:
    """Dependency para obtener EnunciadosService."""
    return EnunciadosService(enunciados_repo, llm_service)


async def get_mensajes_repository(
    db: AsyncSession = Depends(get_db)
) -> MensajesRepository:
    """Dependency para obtener MensajesRepository."""
    return MensajesRepository(db)


async def get_mensajes_service(
    mensajes_repo: MensajesRepository = Depends(get_mensajes_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> MensajesService:
    """Dependency para obtener MensajesService."""
    return MensajesService(mensajes_repo, llm_service)


async def get_videos_service(
    hints_videos_repo: HintsVideosRepository = Depends(get_hints_videos_repository)
) -> VideosService:
    """Dependency para obtener VideosService."""
    return VideosService(hints_videos_repo)


async def get_deteccion_errores_service() -> DeteccionErroresService:
    """Dependency para obtener DeteccionErroresService."""
    return DeteccionErroresService()


async def get_analisis_service(
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> AnalisisService:
    """Dependency para obtener AnalisisService."""
    return AnalisisService(db, llm_service)


# Type aliases
HintsServiceDep = Annotated[HintsService, Depends(get_hints_service)]
EnunciadosServiceDep = Annotated[EnunciadosService, Depends(get_enunciados_service)]
MensajesServiceDep = Annotated[MensajesService, Depends(get_mensajes_service)]
VideosServiceDep = Annotated[VideosService, Depends(get_videos_service)]
DeteccionErroresServiceDep = Annotated[DeteccionErroresService, Depends(get_deteccion_errores_service)]
AnalisisServiceDep = Annotated[AnalisisService, Depends(get_analisis_service)]

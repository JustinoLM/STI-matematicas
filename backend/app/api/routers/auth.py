"""
Router de autenticación.

Endpoints:
- POST /login - Login con código + password
- POST /admin-login - Login del panel de administración (contraseña ADMIN_PASSWORD)
- POST /admin/students, /admin/teachers, /admin/bulk/* - Requieren token de administrador
- GET /me - Obtener usuario actual
- POST /change-password - Cambiar contraseña
"""

import hmac
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_admin_token
from app.api.dependencies import (
    require_admin,
    get_current_active_user,
    get_current_student,
    get_current_teacher,
    AuthServiceDep,
    CurrentUser,
    CurrentStudent,
    CurrentTeacher
)
from app.schemas.auth import (
    LoginRequest,
    CreateStudentRequest,
    CreateTeacherRequest,
    TokenResponse,
    StudentResponse,
    TeacherResponse,
    ChangePasswordRequest,
    MessageResponse,
    UserBase,
    BulkImportStudentsRequest,
    BulkImportTeachersRequest,
    BulkImportResult,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthServiceDep
):
    """
    Login con código único + password.
    
    - **codigo**: Código de estudiante (ej: EST2024001) o profesor (ej: PROF001)
    - **password**: Contraseña del usuario
    
    Retorna token JWT + información básica del usuario.
    """
    return await auth_service.login(
        codigo=login_data.codigo,
        password=login_data.password
    )


@router.get("/me", response_model=UserBase)
async def get_current_user_info(
    current_user: CurrentUser
):
    """
    Obtiene información del usuario autenticado actual.
    
    Requiere token JWT válido en header Authorization.
    """
    return UserBase.model_validate(current_user)


@router.get("/me/student", response_model=StudentResponse)
async def get_current_student_info(
    current_student: CurrentStudent
):
    """
    Obtiene información completa del estudiante autenticado.
    
    Solo accesible por estudiantes.
    """
    return StudentResponse.model_validate(current_student)


@router.get("/me/teacher", response_model=TeacherResponse)
async def get_current_teacher_info(
    current_teacher: CurrentTeacher
):
    """
    Obtiene información completa del profesor autenticado.
    
    Solo accesible por profesores.
    """
    return TeacherResponse.model_validate(current_teacher)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    auth_service: AuthServiceDep
):
    """
    Cambia la contraseña del usuario actual.
    
    Requiere:
    - **password_actual**: Contraseña actual (para verificación)
    - **password_nueva**: Nueva contraseña
    """
    await auth_service.change_password(
        user_id=current_user.id,
        current_password=password_data.password_actual,
        new_password=password_data.password_nueva
    )
    
    return MessageResponse(message="Contraseña actualizada exitosamente")


# ============================================
# Login del panel de administración
# ============================================

_ADMIN_MAX_FALLOS = 5
_ADMIN_VENTANA_SEG = 15 * 60
_admin_fallos: dict[str, list[float]] = {}


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/admin-login", response_model=AdminTokenResponse)
async def admin_login(data: AdminLoginRequest, request: Request):
    """
    Verifica la contraseña del panel de administración (ADMIN_PASSWORD) y
    devuelve un token con role="admin". Limita a 5 intentos fallidos por IP
    cada 15 minutos (en memoria del proceso).
    """
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El acceso de administrador no está configurado",
        )

    ip = request.client.host if request.client else "desconocida"
    ahora = time.monotonic()
    fallos = [t for t in _admin_fallos.get(ip, []) if ahora - t < _ADMIN_VENTANA_SEG]
    if len(fallos) >= _ADMIN_MAX_FALLOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos.",
        )

    if not hmac.compare_digest(
        data.password.encode("utf-8"), settings.ADMIN_PASSWORD.encode("utf-8")
    ):
        fallos.append(ahora)
        _admin_fallos[ip] = fallos
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta",
        )

    _admin_fallos.pop(ip, None)
    return AdminTokenResponse(access_token=create_admin_token())


# ============================================
# Endpoints de Administración
# ============================================
# Todos los endpoints /admin/* exigen un token con role="admin"
# (obtenido en POST /admin-login).

@router.post("/admin/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_student(
    student_data: CreateStudentRequest,
    auth_service: AuthServiceDep
):
    """
    Crea un nuevo estudiante.
    
    Requiere token de administrador.

    El admin proporciona:
    - Código único del estudiante
    - Nombre completo
    - Contraseña temporal (el estudiante puede cambiarla después)
    """
    return await auth_service.create_student(student_data)


@router.post("/admin/teachers", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_teacher(
    teacher_data: CreateTeacherRequest,
    auth_service: AuthServiceDep
):
    """
    Crea un nuevo profesor.

    Requiere token de administrador.
    """
    return await auth_service.create_teacher(teacher_data)


@router.post("/admin/bulk/students", response_model=BulkImportResult, dependencies=[Depends(require_admin)])
async def bulk_import_students(
    data: BulkImportStudentsRequest,
    auth_service: AuthServiceDep
):
    """
    Importación masiva de estudiantes desde un JSON (generado por el frontend al parsear CSV/Excel).
    Continúa aunque alguna fila falle — devuelve resumen de éxitos y errores.
    """
    return await auth_service.bulk_import_students(data)


@router.post("/admin/bulk/teachers", response_model=BulkImportResult, dependencies=[Depends(require_admin)])
async def bulk_import_teachers(
    data: BulkImportTeachersRequest,
    auth_service: AuthServiceDep
):
    """
    Importación masiva de profesores desde un JSON (generado por el frontend al parsear CSV/Excel).
    """
    return await auth_service.bulk_import_teachers(data)

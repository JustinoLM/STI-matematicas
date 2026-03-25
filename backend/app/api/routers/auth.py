"""
Router de autenticación.

Endpoints:
- POST /login - Login con código + password
- POST /admin/students - Crear estudiante (solo admin por ahora)
- POST /admin/teachers - Crear profesor (solo admin por ahora)
- GET /me - Obtener usuario actual
- POST /change-password - Cambiar contraseña
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import (
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
# Endpoints de Administración
# ============================================
# NOTA: Por ahora sin protección de admin.
# En producción, agregar dependency que verifique rol de admin.

@router.post("/admin/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: CreateStudentRequest,
    auth_service: AuthServiceDep
):
    """
    Crea un nuevo estudiante.
    
    **NOTA:** En producción, este endpoint debe estar protegido por rol de administrador.
    Por ahora está abierto para facilitar testing y desarrollo.
    
    El admin proporciona:
    - Código único del estudiante
    - Nombre completo
    - Contraseña temporal (el estudiante puede cambiarla después)
    """
    return await auth_service.create_student(student_data)


@router.post("/admin/teachers", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    teacher_data: CreateTeacherRequest,
    auth_service: AuthServiceDep
):
    """
    Crea un nuevo profesor.

    **NOTA:** En producción, este endpoint debe estar protegido por rol de administrador.
    Por ahora está abierto para facilitar testing y desarrollo.
    """
    return await auth_service.create_teacher(teacher_data)


@router.post("/admin/bulk/students", response_model=BulkImportResult)
async def bulk_import_students(
    data: BulkImportStudentsRequest,
    auth_service: AuthServiceDep
):
    """
    Importación masiva de estudiantes desde un JSON (generado por el frontend al parsear CSV/Excel).
    Continúa aunque alguna fila falle — devuelve resumen de éxitos y errores.
    """
    return await auth_service.bulk_import_students(data)


@router.post("/admin/bulk/teachers", response_model=BulkImportResult)
async def bulk_import_teachers(
    data: BulkImportTeachersRequest,
    auth_service: AuthServiceDep
):
    """
    Importación masiva de profesores desde un JSON (generado por el frontend al parsear CSV/Excel).
    """
    return await auth_service.bulk_import_teachers(data)

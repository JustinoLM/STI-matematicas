"""
Service de autenticación basado en códigos únicos.

Login: codigo + password (sin email)
Creación de usuarios: solo admin
"""

from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status

from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.models.user import Usuario, Estudiante, Profesor
from app.schemas.auth import (
    CreateStudentRequest,
    CreateTeacherRequest,
    TokenResponse,
    UserBase,
    StudentResponse,
    TeacherResponse,
    BulkImportStudentsRequest,
    BulkImportTeachersRequest,
    BulkImportResult,
    BulkImportError,
)


class AuthService:
    """Service para operaciones de autenticación."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def login(self, codigo: str, password: str) -> TokenResponse:
        """
        Autentica un usuario con código y contraseña.
        
        Args:
            codigo: Código de estudiante o profesor
            password: Contraseña
            
        Raises:
            HTTPException: Si credenciales son inválidas
        """
        # Buscar todos los estudiantes con ese código (puede haber varios en distintas orgs)
        estudiantes = await self.user_repo.get_all_students_by_codigo(codigo)
        user = None

        if estudiantes:
            # Elegir el estudiante cuya contraseña coincida (desambiguación multi-org)
            for est in estudiantes:
                if est.activo and verify_password(password, est.password_hash):
                    user = est
                    break
            # Si ninguno coincide pero hay estudiantes, reportar credenciales inválidas
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Código o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # No es estudiante — buscar como profesor
            user = await self.user_repo.get_teacher_by_codigo(codigo)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Código o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not user.activo:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario inactivo. Contacta al administrador."
                )
            if not verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Código o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Actualizar último acceso
        await self.user_repo.update_last_access(user.id)
        
        # Generar token
        access_token = self._create_token_for_user(user)
        
        # Extraer nombre y código según tipo de usuario
        if isinstance(user, Estudiante):
            nombre_completo = user.nombre_completo
            codigo = user.codigo_estudiante
        elif isinstance(user, Profesor):
            nombre_completo = user.nombre_completo
            codigo = user.codigo_profesor
        else:
            nombre_completo = "Usuario"
            codigo = f"user_{user.id}"

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserBase.model_validate(user),
            nombre_completo=nombre_completo,
            codigo=codigo,
        )
    
    async def create_student(self, data: CreateStudentRequest) -> StudentResponse:
        """
        Crea un nuevo estudiante (solo admin).
        
        Raises:
            HTTPException: Si el código ya existe
        """
        # Verificar que código no exista en la misma organización
        if await self.user_repo.codigo_estudiante_exists(data.codigo_estudiante, data.organizacion_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de estudiante ya existe en esta organización"
            )
        
        # Hashear contraseña
        password_hash = get_password_hash(data.password)
        
        # Crear estudiante
        estudiante = await self.user_repo.create_student(
            codigo_estudiante=data.codigo_estudiante,
            password_hash=password_hash,
            password_plain=data.password,
            nombre_completo=data.nombre_completo,
            genero=data.genero,
            organizacion_id=data.organizacion_id,
            grado_academico=data.grado_academico,
            edad=data.edad,
        )

        return StudentResponse.model_validate(estudiante)
    
    async def create_teacher(self, data: CreateTeacherRequest) -> TeacherResponse:
        """Crea un nuevo profesor (solo admin)."""
        # Verificar que código no exista
        if await self.user_repo.codigo_profesor_exists(data.codigo_profesor):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de profesor ya existe"
            )
        
        # Hashear contraseña
        password_hash = get_password_hash(data.password)
        
        # Crear profesor
        profesor = await self.user_repo.create_teacher(
            codigo_profesor=data.codigo_profesor,
            password_hash=password_hash,
            password_plain=data.password,
            nombre_completo=data.nombre_completo,
            institucion=data.institucion,
            organizacion_id=data.organizacion_id,
            grado_academico=data.grado_academico,
        )
        
        return TeacherResponse.model_validate(profesor)
    
    async def bulk_import_students(self, data: BulkImportStudentsRequest) -> BulkImportResult:
        """Importación masiva de estudiantes. Continúa aunque alguna fila falle."""
        errores: list[BulkImportError] = []
        creados = 0
        for idx, row in enumerate(data.estudiantes, start=1):
            try:
                if await self.user_repo.codigo_estudiante_exists(row.codigo_estudiante, row.organizacion_id):
                    errores.append(BulkImportError(
                        fila=idx, codigo=row.codigo_estudiante,
                        mensaje="El código ya existe en esta organización"
                    ))
                    continue
                pw_hash = get_password_hash(row.password)
                await self.user_repo.create_student(
                    codigo_estudiante=row.codigo_estudiante,
                    password_hash=pw_hash,
                    password_plain=row.password,
                    nombre_completo=row.nombre_completo,
                    genero=row.genero,
                    organizacion_id=row.organizacion_id,
                    grado_academico=row.grado_academico,
                    edad=row.edad,
                )
                creados += 1
            except Exception as e:
                errores.append(BulkImportError(
                    fila=idx, codigo=row.codigo_estudiante,
                    mensaje=str(e)
                ))
        return BulkImportResult(total=len(data.estudiantes), creados=creados, errores=errores)

    async def bulk_import_teachers(self, data: BulkImportTeachersRequest) -> BulkImportResult:
        """Importación masiva de profesores. Continúa aunque alguna fila falle."""
        errores: list[BulkImportError] = []
        creados = 0
        for idx, row in enumerate(data.profesores, start=1):
            try:
                if await self.user_repo.codigo_profesor_exists(row.codigo_profesor):
                    errores.append(BulkImportError(
                        fila=idx, codigo=row.codigo_profesor,
                        mensaje="El código ya existe"
                    ))
                    continue
                pw_hash = get_password_hash(row.password)
                await self.user_repo.create_teacher(
                    codigo_profesor=row.codigo_profesor,
                    password_hash=pw_hash,
                    password_plain=row.password,
                    nombre_completo=row.nombre_completo,
                    institucion=row.institucion,
                    organizacion_id=row.organizacion_id,
                    grado_academico=row.grado_academico,
                )
                creados += 1
            except Exception as e:
                errores.append(BulkImportError(
                    fila=idx, codigo=row.codigo_profesor,
                    mensaje=str(e)
                ))
        return BulkImportResult(total=len(data.profesores), creados=creados, errores=errores)

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Cambia la contraseña de un usuario.
        
        Raises:
            HTTPException: Si la contraseña actual es incorrecta
        """
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Verificar contraseña actual
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
        
        # Actualizar contraseña
        new_password_hash = get_password_hash(new_password)
        await self.user_repo.update_password(user_id, new_password_hash)
    
    async def get_current_user(self, token: str) -> Usuario:
        """
        Obtiene el usuario actual desde el token JWT.
        
        Raises:
            HTTPException: Si token es inválido o usuario no existe
        """
        # Decodificar token
        payload = decode_access_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extraer user_id del payload
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buscar usuario
        user = await self.user_repo.get_by_id(int(user_id))
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar que esté activo
        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )
        
        return user
    
    def _create_token_for_user(self, user: Usuario) -> str:
        """Crea un JWT token para un usuario."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Obtener código según tipo de usuario
        if isinstance(user, Estudiante):
            codigo = user.codigo_estudiante
        elif isinstance(user, Profesor):
            codigo = user.codigo_profesor
        else:
            codigo = f"user_{user.id}"
        
        token_data = {
            "sub": str(user.id),
            "codigo": codigo,
            "tipo_usuario": user.tipo_usuario.value,
        }
        
        return create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )

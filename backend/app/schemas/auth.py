"""
Schemas Pydantic para autenticación basada en códigos.

Login: codigo + password (sin email)
Usuarios creados por administrador (no registro público).
"""

from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime

from app.models.user import TipoUsuario, Genero


# ============================================
# Schemas de Request (Input)
# ============================================

class LoginRequest(BaseModel):
    """
    Request para login.

    Estudiantes: codigo_estudiante + password
    Profesores: codigo_profesor + password
    """
    codigo: str = Field(min_length=5, max_length=50, description="Código de estudiante o profesor")
    password: str = Field(min_length=6, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "codigo": "EST001",
                "password": "password123"
            }
        }


class CreateStudentRequest(BaseModel):
    """Request para crear estudiante (solo admin)."""
    codigo_estudiante: str = Field(min_length=5, max_length=50)
    nombre_completo: str = Field(min_length=3, max_length=255)
    genero: Genero = Genero.MASCULINO
    password: str = Field(min_length=6, max_length=100)
    organizacion_id: Optional[int] = None
    grado_academico: Optional[str] = Field(None, max_length=50)
    anio_nacimiento: Optional[int] = Field(None, ge=2000, le=2030)
    mes_nacimiento: Optional[int] = Field(None, ge=1, le=12)

    class Config:
        json_schema_extra = {
            "example": {
                "codigo_estudiante": "EST001",
                "nombre_completo": "Juan Pérez",
                "genero": "masculino",
                "password": "temp123",
                "organizacion_id": 1,
                "grado_academico": "5to grado",
                "anio_nacimiento": 2014,
                "mes_nacimiento": 3,
            }
        }


class CreateTeacherRequest(BaseModel):
    """Request para crear profesor (solo admin)."""
    codigo_profesor: str = Field(min_length=5, max_length=50)
    nombre_completo: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=100)
    institucion: Optional[str] = Field(None, max_length=255)
    organizacion_id: Optional[int] = None
    grado_academico: Optional[str] = Field(None, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "codigo_profesor": "PROF001",
                "nombre_completo": "María Gómez",
                "password": "temp123",
                "institucion": "Escuela Primaria Central",
                "organizacion_id": 1,
            }
        }


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña."""
    password_actual: str = Field(min_length=6, max_length=100)
    password_nueva: str = Field(min_length=6, max_length=100)

    @validator('password_nueva')
    def passwords_different(cls, v, values):
        """Valida que la nueva contraseña sea diferente."""
        if 'password_actual' in values and v == values['password_actual']:
            raise ValueError('La nueva contraseña debe ser diferente a la actual')
        return v


# ============================================
# Schemas de Response (Output)
# ============================================

class UserBase(BaseModel):
    """Schema base para usuarios."""
    id: int
    tipo_usuario: TipoUsuario
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime]
    activo: bool

    class Config:
        from_attributes = True


class StudentResponse(UserBase):
    """Response para estudiante."""
    codigo_estudiante: str
    nombre_completo: str
    genero: Genero
    narrativa_seleccionada_id: Optional[int]
    grado_academico: Optional[str] = None
    anio_nacimiento: Optional[int] = None
    mes_nacimiento: Optional[int] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "tipo_usuario": "estudiante",
                "fecha_creacion": "2024-01-15T10:30:00",
                "ultimo_acceso": "2024-01-20T14:45:00",
                "activo": True,
                "codigo_estudiante": "EST001",
                "nombre_completo": "Juan Pérez",
                "narrativa_seleccionada_id": None,
            }
        }


class TeacherResponse(UserBase):
    """Response para profesor."""
    codigo_profesor: str
    nombre_completo: str
    institucion: Optional[str]
    grado_academico: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 2,
                "tipo_usuario": "profesor",
                "fecha_creacion": "2024-01-10T09:00:00",
                "ultimo_acceso": "2024-01-20T15:30:00",
                "activo": True,
                "codigo_profesor": "PROF001",
                "nombre_completo": "María Gómez",
                "institucion": "Escuela Primaria Central",
            }
        }


class TokenResponse(BaseModel):
    """Response con token JWT."""
    access_token: str
    token_type: str = "bearer"
    user: UserBase
    # Campos extras para el frontend (evita un segundo request al /me)
    nombre_completo: str
    codigo: str  # codigo_estudiante o codigo_profesor

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "tipo_usuario": "estudiante",
                    "fecha_creacion": "2024-01-15T10:30:00",
                    "ultimo_acceso": None,
                    "activo": True
                },
                "nombre_completo": "Juan Pérez",
                "codigo": "EST001"
            }
        }


class MessageResponse(BaseModel):
    """Response genérico con mensaje."""
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operación exitosa"
            }
        }


# ============================================
# Schemas de Importación Masiva
# ============================================

class BulkStudentRow(BaseModel):
    """Una fila del archivo de importación masiva de estudiantes."""
    codigo_estudiante: str = Field(min_length=5, max_length=50)
    nombre_completo: str = Field(min_length=3, max_length=255)
    genero: Genero = Genero.MASCULINO
    password: str = Field(min_length=6, max_length=100)
    organizacion_id: Optional[int] = None
    grado_academico: Optional[str] = Field(None, max_length=50)
    anio_nacimiento: Optional[int] = Field(None, ge=2000, le=2030)
    mes_nacimiento: Optional[int] = Field(None, ge=1, le=12)


class BulkTeacherRow(BaseModel):
    """Una fila del archivo de importación masiva de profesores."""
    codigo_profesor: str = Field(min_length=5, max_length=50)
    nombre_completo: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=100)
    institucion: Optional[str] = Field(None, max_length=255)
    organizacion_id: Optional[int] = None
    grado_academico: Optional[str] = Field(None, max_length=100)


class BulkImportStudentsRequest(BaseModel):
    """Request para importación masiva de estudiantes."""
    estudiantes: list[BulkStudentRow]


class BulkImportTeachersRequest(BaseModel):
    """Request para importación masiva de profesores."""
    profesores: list[BulkTeacherRow]


class BulkImportError(BaseModel):
    fila: int
    codigo: str
    mensaje: str


class BulkImportResult(BaseModel):
    """Resultado de una importación masiva."""
    total: int
    creados: int
    errores: list[BulkImportError]

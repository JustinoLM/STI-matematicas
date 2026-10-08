"""
Utilidades de seguridad para autenticación y autorización.

Maneja hashing de contraseñas con Argon2 y generación/validación de JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Contexto para hashing de contraseñas con Argon2
# Argon2 es más seguro que bcrypt y no tiene límite de 72 bytes
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash de una contraseña usando Argon2."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un JWT access token.
    
    Args:
        data: Datos a codificar (típicamente user_id, role)
        expires_delta: Duración del token (opcional)
    
    Returns:
        JWT token codificado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT token.
    
    Returns:
        Payload del token si es válido, None si es inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def create_admin_token() -> str:
    """
    Crea un JWT para el panel de administración.

    No corresponde a un usuario de la BD: lleva role="admin" y sub="admin",
    y expira según ADMIN_TOKEN_EXPIRE_MINUTES.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ADMIN_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": "admin", "role": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

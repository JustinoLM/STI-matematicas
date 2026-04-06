"""
Configuración centralizada de la aplicación.

Utiliza Pydantic Settings para validar y gestionar variables de entorno.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Configuración general
    PROJECT_NAME: str = "STI API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"

    # Base de datos
    DATABASE_URL: str

    @property
    def async_database_url(self) -> str:
        """Asegura que la URL use el driver asyncpg, sin importar cómo llegue."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Seguridad JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # LLM (DeepSeek API)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL_V3: str = "deepseek-chat"        # rápido, mensajes y enunciados
    DEEPSEEK_MODEL_R1: str = "deepseek-reasoner"    # razonamiento, análisis post-práctica

    # Cloudinary (almacenamiento de videos/imágenes)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Videos Configuration
    VIDEO_TEMP_LIFETIME_HOURS: int = 24
    MAX_VIDEOS_GUARDADOS: int = 10

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://tesis-sti-matematicas.vercel.app",
    ]

    # Entorno
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Configuración de Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instancia global de configuración
settings = Settings()

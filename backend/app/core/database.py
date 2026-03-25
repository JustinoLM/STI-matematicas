"""
Configuración de SQLAlchemy y gestión de sesiones de base de datos.

Este módulo maneja la conexión a PostgreSQL usando SQLAlchemy async.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Crear engine asíncrono de SQLAlchemy
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,  # Mostrar queries SQL en modo debug
    future=True,
    pool_pre_ping=True,  # Verificar conexiones antes de usar
)

# Session factory para crear nuevas sesiones
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class para modelos ORM
Base = declarative_base()


# Dependency para obtener sesión de BD en endpoints
async def get_db() -> AsyncSession:
    """
    Dependency que proporciona una sesión de base de datos.
    
    Uso en FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # usar db aquí
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

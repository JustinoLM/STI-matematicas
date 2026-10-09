"""
Configuración de pytest y fixtures.

Crea una base de datos de test limpia antes de cada test.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# URL de base de datos de test (en memoria compartida)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Engine de test con pool estático (mantiene una sola conexión)
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # IMPORTANTE: Una sola conexión compartida
    echo=False,
)

# Session de test
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """
    Crea todas las tablas antes de cada test y las elimina después.
    
    autouse=True hace que se ejecute automáticamente en todos los tests.
    """
    # Crear todas las tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Eliminar todas las tablas después del test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Override del dependency get_db para tests.
    
    IMPORTANTE: Usa commit() en vez de solo flush() para que
    los cambios persistan entre diferentes requests HTTP.
    """
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()  # COMMIT en vez de flush
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override global del dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def anyio_backend():
    """Backend for anyio."""
    return "asyncio"


def admin_headers() -> dict:
    """Cabecera Authorization con un token de administrador (para endpoints /admin)."""
    from app.core.security import create_admin_token

    return {"Authorization": f"Bearer {create_admin_token()}"}

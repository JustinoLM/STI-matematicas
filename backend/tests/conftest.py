"""
Configuración de pytest y fixtures.

Crea una base de datos de test limpia antes de cada test.

Las pruebas corren solo en PostgreSQL, el motor real del sistema. La URL sale de
TEST_DATABASE_URL o, si no está definida, se usa
postgresql+asyncpg://localhost:5432/sti_test con el usuario del sistema.
El nombre de la base debe contener "test": nunca se corre contra la base de desarrollo
ni contra la de la tesis, porque cada prueba borra todas las tablas.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://localhost:5432/sti_test"
)
_url = make_url(TEST_DATABASE_URL)
if not _url.drivername.startswith("postgresql"):
    raise RuntimeError(f"TEST_DATABASE_URL debe ser de PostgreSQL, no '{_url.drivername}'.")
_nombre_bd = _url.database or ""
if "test" not in _nombre_bd.lower():
    raise RuntimeError(
        f"TEST_DATABASE_URL apunta a la base '{_nombre_bd}', que no parece de pruebas. "
        "Las pruebas borran todas las tablas: usa una base cuyo nombre contenga 'test'."
    )

# La aplicación crea su propio engine con settings.DATABASE_URL al importarse (lo usa,
# por ejemplo, /health). Se apunta a la base de pruebas ANTES de importar app.*, para que
# ninguna prueba toque la base configurada en backend/.env.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Sin pool: cada sesión abre y cierra su conexión, así no quedan conexiones
# abiertas que bloqueen el DROP de tablas entre pruebas.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

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


@pytest.fixture(scope="session", autouse=True)
async def cerrar_engines():
    """
    Cierra las conexiones al terminar la sesión de pruebas (el engine de la aplicación
    puede quedar con conexiones en su pool, por ejemplo tras /health).
    """
    yield
    from app.core.database import engine as app_engine

    await test_engine.dispose()
    await app_engine.dispose()


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

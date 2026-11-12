"""
Configuración de pytest y fixtures.

El esquema se crea una vez por corrida; las pruebas con @pytest.mark.db parten de tablas vacías.

Las pruebas corren solo en PostgreSQL, el motor real del sistema. La URL sale de
TEST_DATABASE_URL o, si no está definida, se usa
postgresql+asyncpg://localhost:5432/sti_test con el usuario del sistema.
El nombre de la base debe contener "test": nunca se corre contra la base de desarrollo
ni contra la de la tesis, porque las pruebas borran todas las tablas.
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


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "db: la prueba usa la base de datos (se limpia antes de correrla). "
        "Ciclo rápido sin base: pytest -m 'not db'",
    )


# --- Guardia: una prueba sin @pytest.mark.db no puede abrir conexiones a la base ---------
# Se activa mientras corre una prueba sin el marcador; si en ese lapso algún engine (el de
# pruebas o el de la aplicación) entrega una conexión, la prueba falla con un mensaje claro.
# Así ninguna prueba que use la base puede saltarse la limpieza sin que se note.
_guardia = {"activa": False, "violaciones": 0}


def _al_entregar_conexion(*_args) -> None:
    if _guardia["activa"]:
        _guardia["violaciones"] += 1


def _instalar_guardia() -> None:
    from sqlalchemy import event

    from app.core.database import engine as app_engine

    for eng in (test_engine, app_engine):
        event.listen(eng.sync_engine, "checkout", _al_entregar_conexion)


_instalar_guardia()

# Reinicia las secuencias usadas, como lo hacía antes el drop_all/create_all por prueba.
_REINICIAR_SECUENCIAS = """
DO $$
DECLARE s record;
BEGIN
  FOR s IN SELECT sequencename FROM pg_sequences
           WHERE schemaname = current_schema() AND last_value IS NOT NULL LOOP
    EXECUTE format('ALTER SEQUENCE %I RESTART', s.sequencename);
  END LOOP;
END $$
"""


async def _vaciar_tablas() -> None:
    """Borra todas las filas (en orden inverso de dependencias) y reinicia las secuencias."""
    from sqlalchemy import text

    async with test_engine.begin() as conn:
        for tabla in reversed(Base.metadata.sorted_tables):
            await conn.execute(tabla.delete())
        await conn.execute(text(_REINICIAR_SECUENCIAS))


@pytest.fixture(scope="session", autouse=True)
async def esquema_de_pruebas():
    """
    Crea el esquema UNA vez por corrida (borrando antes el que hubiera, para recoger cambios
    de modelos) y lo elimina al final. Cierra también las conexiones de los engines (el de la
    aplicación puede quedar con conexiones en su pool, por ejemplo tras /health).
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    from app.core.database import engine as app_engine

    await app_engine.dispose()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(scope="function", autouse=True)
async def setup_database(request):
    """
    Pruebas con @pytest.mark.db: parten de tablas vacías (se vacían ANTES de cada una, así
    el aislamiento no depende de cómo terminó la anterior; vale también para las que hacen
    commit o abren varias sesiones).
    Pruebas sin el marcador: no tocan la base, y la guardia lo verifica.
    """
    if request.node.get_closest_marker("db"):
        await _vaciar_tablas()
        yield
        return

    _guardia["activa"], _guardia["violaciones"] = True, 0
    try:
        yield
    finally:
        _guardia["activa"] = False
    if _guardia["violaciones"]:
        pytest.fail(
            "La prueba abrió conexiones a la base sin @pytest.mark.db. "
            "Márcala (o su módulo con pytestmark = pytest.mark.db) para que parta de tablas limpias."
        )


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

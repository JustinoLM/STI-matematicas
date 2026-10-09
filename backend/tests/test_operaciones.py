"""
Operación en producción: documentación de la API, health check con base de datos, CORS,
registro de peticiones (JSON), scheduler con un solo ejecutor y cierre ordenado.
"""

import asyncio
import json
import logging

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from httpx import AsyncClient

from app import main as main_mod
from app.core.config import settings
from app.core.logging_config import JsonFormatter
from app.main import app, urls_documentacion
from app.services import scheduler_service
from tests.conftest import TestSessionLocal, test_engine

# ─── Documentación y CORS ────────────────────────────────────────────────────

def test_en_produccion_se_desactivan_docs_redoc_y_openapi():
    assert urls_documentacion("production") == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    dev = urls_documentacion("development")
    assert dev == {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


def test_los_valores_por_defecto_son_seguros():
    assert type(settings).model_fields["ENVIRONMENT"].default == "production"
    assert type(settings).model_fields["DEBUG"].default is False


def test_cors_toma_los_origenes_de_la_configuracion():
    assert main_mod.cors_origins == list(settings.BACKEND_CORS_ORIGINS)


# ─── Health check ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_consulta_la_base_de_datos(monkeypatch):
    monkeypatch.setattr(main_mod, "AsyncSessionLocal", TestSessionLocal)
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy" and r.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_health_responde_503_si_la_base_no_contesta(monkeypatch):
    class _SesionRota:
        async def __aenter__(self):
            raise ConnectionError("sin base de datos")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(main_mod, "AsyncSessionLocal", lambda: _SesionRota())
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "unhealthy" and r.json()["database"] == "unavailable"


# ─── Registros ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cada_peticion_se_registra_con_estado_duracion_e_id(caplog):
    caplog.set_level(logging.INFO, logger="sti.http")
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/?secreto=123", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    reg = [x for x in caplog.records if x.name == "sti.http"][-1]
    assert (reg.method, reg.path, reg.status, reg.request_id) == ("GET", "/", 200, "abc123")
    assert reg.duration_ms >= 0
    assert "secreto" not in reg.getMessage()   # la query string no se registra


def test_el_formato_json_incluye_los_campos_propios():
    logger = logging.getLogger("prueba.json")
    registro = logger.makeRecord("prueba.json", logging.INFO, __file__, 1, "hola %s", ("mundo",), None,
                                 extra={"status": 200, "path": "/x"})
    datos = json.loads(JsonFormatter().format(registro))
    assert datos["message"] == "hola mundo" and datos["level"] == "INFO"
    assert datos["status"] == 200 and datos["path"] == "/x" and "ts" in datos


# ─── Scheduler ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sin_postgresql_el_proceso_siempre_es_el_ejecutor(monkeypatch):
    monkeypatch.setattr(scheduler_service, "engine", test_engine)   # SQLite en memoria
    assert await scheduler_service._adquirir_bloqueo() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("es_lider,esperados", [
    (True, {"ml_entrenamiento", "sesiones_huerfanas"}),
    (False, {"ml_recarga"}),
])
async def test_solo_el_proceso_con_bloqueo_registra_los_jobs_de_ml_y_sesiones(monkeypatch, es_lider, esperados):
    nuevo = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr(scheduler_service, "_scheduler", nuevo)

    async def _bloqueo():
        return es_lider

    async def _sin_trabajo():
        return None

    monkeypatch.setattr(scheduler_service, "_adquirir_bloqueo", _bloqueo)
    monkeypatch.setattr(scheduler_service, "job_entrenar_ml", _sin_trabajo)
    await scheduler_service.start_scheduler()
    try:
        assert {j.id for j in nuevo.get_jobs()} == esperados
    finally:
        await scheduler_service.stop_scheduler()
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_al_cerrar_se_espera_a_los_jobs_en_curso():
    terminados = []

    async def lento():
        await asyncio.sleep(0.2)
        terminados.append(True)

    tarea = asyncio.ensure_future(scheduler_service._esperable(lento)())
    await asyncio.sleep(0.02)
    tarea.cancel()                      # APScheduler cancela la tarea al apagarse
    await scheduler_service.stop_scheduler()
    assert terminados == [True]         # pero el trabajo real alcanzó a terminar

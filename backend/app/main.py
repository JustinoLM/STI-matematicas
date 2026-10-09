"""
Entry point principal de la aplicación FastAPI.
"""

import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routers import (
    adaptive,
    admin_exports,
    admin_import,
    admin_organizations,
    analisis,
    animaciones,
    auth,
    challenges,
    enunciados,
    gamification,
    hints,
    mensajes,
    practices,
    regla_de_tres,
    stats,
    teachers,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging_config import configurar_logging
from app.services.ml_service import ml_service
from app.services.scheduler_service import start_scheduler, stop_scheduler

configurar_logging(
    formato=settings.LOG_FORMAT or ("text" if settings.ENVIRONMENT == "development" else "json"),
    nivel=settings.LOG_LEVEL,
)
logger = logging.getLogger("sti")


def urls_documentacion(entorno: str) -> dict:
    """
    URLs de la documentación interactiva. En producción se desactivan las tres
    (`/docs`, `/redoc` y también `/openapi.json`) para no exponer la descripción de la API.
    """
    if entorno == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


# Crear instancia de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST del Sistema de Tutoría Inteligente",
    version="0.1.0",
    **urls_documentacion(settings.ENVIRONMENT),
)

# Configurar CORS: orígenes tomados de BACKEND_CORS_ORIGINS (variable de entorno JSON
# o valor por defecto de config.py)
cors_origins = list(settings.BACKEND_CORS_ORIGINS)
cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ── Registro de peticiones ───────────────────────────────────────────────────
# Una línea por petición (método, ruta sin query string, estado, duración e id).
# Sustituye al registro de acceso de Uvicorn.
@app.middleware("http")
async def registrar_peticion(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    inicio = time.perf_counter()
    estado = 500
    try:
        response = await call_next(request)
        estado = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logging.getLogger("sti.http").info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            estado,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": estado,
                "duration_ms": round((time.perf_counter() - inicio) * 1000, 1),
            },
        )


# Registrar routers
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(adaptive.router, prefix="/api/adaptive", tags=["Sistema Adaptativo"])
app.include_router(practices.router, prefix="/api/practices", tags=["Prácticas e Intentos"])
app.include_router(gamification.router, prefix="/api/gamification", tags=["Gamificación"])
app.include_router(hints.router, prefix="/api", tags=["Pistas"])
app.include_router(teachers.router, prefix="/api/teachers", tags=["Profesores"])
app.include_router(admin_organizations.router, prefix="/api", tags=["Admin - Organizaciones"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["Desafíos"])
app.include_router(enunciados.router, prefix="/api/enunciados", tags=["Enunciados Temáticos"])
app.include_router(mensajes.router, prefix="/api/mensajes", tags=["Mensajes Motivacionales"])
app.include_router(analisis.router, prefix="/api/analisis", tags=["Análisis Post-Práctica"])
app.include_router(animaciones.router, prefix="/api/animaciones", tags=["Animaciones Guardadas"])
app.include_router(stats.router, prefix="/api/stats", tags=["Estadísticas de Grupo"])
app.include_router(admin_exports.router, prefix="/api", tags=["Admin - Exportaciones"])
app.include_router(regla_de_tres.router, prefix="/api/regla-de-tres", tags=["Regla de Tres"])
app.include_router(admin_import.router, prefix="/api", tags=["Admin - Importación"])


# ── Handler global para excepciones no-HTTP ──────────────────────────────────
# Starlette en algunas versiones no añade headers CORS a respuestas 500 que
# vienen de excepciones Python no capturadas (IndexError, TypeError, etc.).
# Este handler garantiza que CORS siempre esté presente, incluso en 500s.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin in cors_origins:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    # Log del error (con traza) para diagnosticarlo desde los logs del despliegue
    logger.error(
        "Error no controlado: %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers=cors_headers,
    )


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Endpoint básico de health check."""
    return {
        "message": "STI API - Sistema de Tutoría Inteligente",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check detallado: ejecuta `SELECT 1` en la base de datos.
    Responde 503 si la base no contesta en 5 segundos, para que el despliegue lo detecte.
    """
    try:
        async with AsyncSessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5)
    except Exception:
        logger.exception("Health check: la base de datos no responde")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "unavailable",
                "environment": settings.ENVIRONMENT,
            },
        )
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
    }


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Ejecutado al iniciar la aplicación."""
    logger.info(
        "Iniciando STI Backend (entorno=%s, debug=%s, docs=%s)",
        settings.ENVIRONMENT,
        settings.DEBUG,
        app.docs_url or "desactivados",
    )

    # Cargar modelos ML desde PostgreSQL (sobreviven reinicios del servidor)
    try:
        async with AsyncSessionLocal() as session:
            await ml_service.load_all_from_db(session)
    except Exception:
        logger.exception("No se pudieron cargar modelos ML desde la BD")

    await start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutado al cerrar la aplicación."""
    logger.info("Cerrando STI Backend")
    await stop_scheduler()

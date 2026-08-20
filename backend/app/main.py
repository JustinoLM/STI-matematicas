"""
Entry point principal de la aplicación FastAPI.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routers import auth, problems, adaptive, practices, gamification, hints_videos, teachers, admin_organizations, challenges, enunciados, mensajes, analisis, animaciones, stats, admin_exports, regla_de_tres, admin_import
from app.core.database import AsyncSessionLocal
from app.services.ml_service import ml_service
from app.services.scheduler_service import start_scheduler, stop_scheduler

# En producción se ocultan los docs para no exponer la API pública
_docs_url = None if settings.ENVIRONMENT == "production" else "/docs"
_redoc_url = None if settings.ENVIRONMENT == "production" else "/redoc"

# Crear instancia de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST del Sistema de Tutoría Inteligente",
    version="0.1.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

# Configurar CORS
# En desarrollo se permiten todos los orígenes localhost para evitar
# problemas con puertos dinámicos de Vite (5173, 5174, etc.)
cors_origins = [
    "https://tesis-sti-matematicas.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]
cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(problems.router, prefix="/api/problems", tags=["Problemas"])
app.include_router(adaptive.router, prefix="/api/adaptive", tags=["Sistema Adaptativo"])
app.include_router(practices.router, prefix="/api/practices", tags=["Prácticas e Intentos"])
app.include_router(gamification.router, prefix="/api/gamification", tags=["Gamificación"])
app.include_router(hints_videos.router, prefix="/api", tags=["Pistas y Videos"])
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
    # Log del error para poder diagnosticarlo desde los logs de Railway
    import traceback
    print(f"[ERROR 500] {request.method} {request.url}")
    print(traceback.format_exc())
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
    """Endpoint detallado de health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
    }


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Ejecutado al iniciar la aplicación."""
    print("=" * 60)
    print("🚀 INICIANDO STI BACKEND")
    print("=" * 60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug: {settings.DEBUG}")
    print(f"API Docs: http://localhost:8000/docs")
    print("=" * 60)

    # Cargar modelos ML desde PostgreSQL (sobreviven reinicios del servidor)
    try:
        async with AsyncSessionLocal() as session:
            await ml_service.load_all_from_db(session)
    except Exception as e:
        print(f"⚠️  No se pudieron cargar modelos ML desde BD: {e}")

    await start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutado al cerrar la aplicación."""
    print("👋 Cerrando STI Backend...")
    await stop_scheduler()

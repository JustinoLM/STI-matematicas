"""
Scheduler de tareas en background.

Dos jobs:
  1. ML automático cada 3 días — entrena K-Means y reclasifica estudiantes.
  2. Cierre de sesiones huérfanas cada 30 min — sesiones en_progreso con
     más de 90 minutos de inactividad se marcan como ABANDONADA.
"""

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.adaptive import EstadoSesion, SesionPractica
from app.models.config import ConfiguracionSistema
from app.services.ml_service import ml_service

# ─── Constantes ───────────────────────────────────────────────────────────────

CLAVE_ULTIMO_ENTRENAMIENTO = "ml_ultimo_entrenamiento"
INTERVALO_ENTRENAMIENTO_DIAS = 1
HORA_ENTRENAMIENTO_UTC = 3  # el job diario corre a las 03:00 UTC (22:00 hora de Panamá)
TIMEOUT_SESION_MINUTOS = 90

# ─── Job 1: Entrenamiento ML ──────────────────────────────────────────────────


async def job_entrenar_ml() -> None:
    """
    Se ejecuta todos los días a las 03:00 UTC (y una vez al arrancar el servidor).
    Si pasó al menos INTERVALO_ENTRENAMIENTO_DIAS desde el último entrenamiento,
    entrena el K-means de cada organización y la regresión logística global,
    guarda los modelos en la BD y reclasifica a todos los estudiantes.
    """
    print("⏰ [Scheduler] Verificando si es necesario entrenar ML...")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConfiguracionSistema).where(
                ConfiguracionSistema.clave == CLAVE_ULTIMO_ENTRENAMIENTO
            )
        )
        config = result.scalar_one_or_none()

        if config and config.valor:
            ultimo = datetime.fromisoformat(config.valor)
            dias_pasados = (datetime.utcnow() - ultimo).days
            if dias_pasados < INTERVALO_ENTRENAMIENTO_DIAS:
                print(
                    f"   ↳ Último entrenamiento hace {dias_pasados} día(s). "
                    f"Próximo en {INTERVALO_ENTRENAMIENTO_DIAS - dias_pasados} día(s)."
                )
                return

        resultado = await ml_service.entrenar_y_clasificar(db)

        if not resultado["orgs_entrenadas"] and not resultado["prediccion_entrenada"]:
            print(
                f"   ↳ Datos insuficientes: {resultado['perfiles_validos']}/"
                f"{resultado['total_perfiles']} perfiles válidos (se necesitan ≥10 por "
                f"organización) y {resultado['ejemplos_prediccion']} ejemplos para la predicción."
            )
            return

        ahora = datetime.utcnow()
        if config:
            config.valor = ahora.isoformat()
            config.actualizado_en = ahora
        else:
            db.add(ConfiguracionSistema(
                clave=CLAVE_ULTIMO_ENTRENAMIENTO,
                valor=ahora.isoformat(),
                actualizado_en=ahora,
            ))
        await db.commit()

        print(
            f"✅ [Scheduler] ML entrenado: {resultado['orgs_entrenadas']} org(s), "
            f"predicción {'sí' if resultado['prediccion_entrenada'] else 'no'}, "
            f"{resultado['reclasificados']} estudiantes reclasificados."
        )


# ─── Job 2: Cierre de sesiones huérfanas ─────────────────────────────────────


async def job_cerrar_sesiones_huerfanas() -> None:
    """
    Cierra sesiones de práctica (iniciadas o en progreso) que llevan más de 90
    minutos sin actividad.

    Las marca como ABANDONADA con fecha_fin = ahora. No penaliza al estudiante
    — simplemente libera la sesión para que pueda iniciar una nueva.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=TIMEOUT_SESION_MINUTOS)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SesionPractica).where(
                SesionPractica.estado.in_([EstadoSesion.INICIADA, EstadoSesion.EN_PROGRESO]),
                SesionPractica.fecha_ultima_actividad < cutoff,
            )
        )
        sesiones = list(result.scalars().all())

        if not sesiones:
            return

        ahora = datetime.utcnow()
        for sesion in sesiones:
            sesion.estado = EstadoSesion.ABANDONADA
            sesion.fecha_fin = ahora

        await db.commit()

        print(
            f"⏰ [Scheduler] {len(sesiones)} sesión(es) huérfana(s) cerradas "
            f"(inactivas >{TIMEOUT_SESION_MINUTOS} min)."
        )


# ─── Scheduler ────────────────────────────────────────────────────────────────

_scheduler = AsyncIOScheduler(timezone="UTC")


async def start_scheduler() -> None:
    """
    Inicia el scheduler y registra los jobs.
    También ejecuta una verificación inmediata de ML al arrancar
    (catch-up si el servidor estuvo apagado a las 03:00 UTC).
    """
    # Job 1: Entrenamiento ML diario a hora fija (03:00 UTC)
    _scheduler.add_job(
        job_entrenar_ml,
        trigger="cron",
        hour=HORA_ENTRENAMIENTO_UTC,
        minute=0,
        id="ml_entrenamiento",
        replace_existing=True,
        misfire_grace_time=3600,  # Tolerancia de 1 hora si el job se retrasa
    )

    # Job 2: Cierre de sesiones huérfanas cada 30 minutos
    _scheduler.add_job(
        job_cerrar_sesiones_huerfanas,
        trigger="interval",
        minutes=30,
        id="sesiones_huerfanas",
        replace_existing=True,
        misfire_grace_time=300,
    )

    _scheduler.start()
    print(
        f"✅ [Scheduler] Iniciado — ML diario {HORA_ENTRENAMIENTO_UTC:02d}:00 UTC, "
        "sesiones huérfanas cada 30 min."
    )

    # Verificación inmediata de ML (catch-up tras reinicio)
    asyncio.create_task(job_entrenar_ml())


async def stop_scheduler() -> None:
    """Detiene el scheduler limpiamente al apagar el servidor."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("👋 [Scheduler] Detenido.")

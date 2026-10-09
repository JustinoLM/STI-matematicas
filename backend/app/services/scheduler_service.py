"""
Scheduler de tareas en background.

Jobs:
  1. ML automático diario — entrena K-Means y reclasifica estudiantes.
  2. Cierre de sesiones huérfanas cada 30 min — sesiones en_progreso con
     más de 90 minutos de inactividad se marcan como ABANDONADA.
  3. Recarga de modelos ML desde la BD cada 15 min (solo en procesos que no entrenan).

Con varios workers de Uvicorn solo un proceso (el que obtiene el bloqueo consultivo de
PostgreSQL) ejecuta los jobs 1 y 2; los demás recargan los modelos que ese proceso guarda.
"""

import asyncio
import functools
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal, engine
from app.models.adaptive import EstadoSesion, SesionPractica
from app.models.config import ConfiguracionSistema
from app.services.ml_service import ml_service

# ─── Constantes ───────────────────────────────────────────────────────────────

CLAVE_ULTIMO_ENTRENAMIENTO = "ml_ultimo_entrenamiento"
INTERVALO_ENTRENAMIENTO_DIAS = 1
HORA_ENTRENAMIENTO_UTC = 3  # el job diario corre a las 03:00 UTC (22:00 hora de Panamá)
TIMEOUT_SESION_MINUTOS = 90
INTERVALO_RECARGA_MODELOS_MINUTOS = 15
TIMEOUT_CIERRE_SEGUNDOS = 60       # espera máxima a los jobs en curso al apagar
CLAVE_BLOQUEO_SCHEDULER = 727401   # clave del bloqueo consultivo de PostgreSQL

logger = logging.getLogger(__name__)

# ─── Job 1: Entrenamiento ML ──────────────────────────────────────────────────


async def job_entrenar_ml() -> None:
    """
    Se ejecuta todos los días a las 03:00 UTC (y una vez al arrancar el servidor).
    Si pasó al menos INTERVALO_ENTRENAMIENTO_DIAS desde el último entrenamiento,
    entrena el K-means de cada organización y la regresión logística global,
    guarda los modelos en la BD y reclasifica a todos los estudiantes.
    """
    logger.info("Verificando si es necesario entrenar ML...")

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
                logger.info(
                    f"Último entrenamiento hace {dias_pasados} día(s). "
                    f"Próximo en {INTERVALO_ENTRENAMIENTO_DIAS - dias_pasados} día(s)."
                )
                return

        resultado = await ml_service.entrenar_y_clasificar(db)

        if not resultado["orgs_entrenadas"] and not resultado["prediccion_entrenada"]:
            logger.warning(
                f"Datos insuficientes: {resultado['perfiles_validos']}/"
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

        logger.info(
            f"ML entrenado: {resultado['orgs_entrenadas']} org(s), "
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

        logger.info(
            f"{len(sesiones)} sesión(es) huérfana(s) cerradas "
            f"(inactivas >{TIMEOUT_SESION_MINUTOS} min)."
        )


# ─── Scheduler ────────────────────────────────────────────────────────────────

_scheduler = AsyncIOScheduler(timezone="UTC")

# Trabajos en ejecución (para esperarlos al apagar) y conexión que sostiene el bloqueo
_en_curso: set[asyncio.Future] = set()
_conexion_bloqueo = None


def _esperable(func):
    """
    Envuelve un job para que sobreviva al cierre del scheduler: APScheduler cancela las
    tareas pendientes al apagarse; aquí el trabajo real corre aparte (shield) y
    `stop_scheduler` espera a que termine.
    """

    @functools.wraps(func)
    async def envoltorio() -> None:
        tarea = asyncio.ensure_future(func())
        _en_curso.add(tarea)
        tarea.add_done_callback(_en_curso.discard)
        await asyncio.shield(tarea)

    return envoltorio


async def job_recargar_modelos() -> None:
    """Recarga los modelos ML guardados en la BD (los entrena otro proceso)."""
    async with AsyncSessionLocal() as db:
        await ml_service.load_all_from_db(db)


async def _adquirir_bloqueo() -> bool:
    """
    Intenta ser el proceso que ejecuta los jobs programados.

    En PostgreSQL usa un bloqueo consultivo de sesión (`pg_try_advisory_lock`) sostenido por
    una conexión dedicada durante toda la vida del proceso. Con otro motor (pruebas con
    SQLite) no hay otros procesos y siempre devuelve True.
    """
    global _conexion_bloqueo
    if engine.dialect.name != "postgresql":
        return True
    conexion = await engine.connect()
    try:
        obtenido = (
            await conexion.execute(
                text("SELECT pg_try_advisory_lock(:clave)"), {"clave": CLAVE_BLOQUEO_SCHEDULER}
            )
        ).scalar()
    except Exception:
        await conexion.close()
        raise
    if obtenido:
        _conexion_bloqueo = conexion
        return True
    await conexion.close()
    return False


async def _liberar_bloqueo() -> None:
    global _conexion_bloqueo
    if _conexion_bloqueo is not None:
        try:
            await _conexion_bloqueo.execute(
                text("SELECT pg_advisory_unlock(:clave)"), {"clave": CLAVE_BLOQUEO_SCHEDULER}
            )
        finally:
            await _conexion_bloqueo.close()
            _conexion_bloqueo = None


async def start_scheduler() -> None:
    """
    Inicia el scheduler. El proceso que obtiene el bloqueo registra los jobs de ML diario y
    de sesiones huérfanas (y lanza la verificación inmediata de ML tras un reinicio); los
    demás solo recargan periódicamente los modelos de ML desde la BD.
    """
    try:
        es_lider = await _adquirir_bloqueo()
    except Exception:
        # Sin bloqueo no se puede garantizar un único ejecutor: se prefiere no duplicar jobs
        logger.exception("No se pudo consultar el bloqueo del scheduler; este proceso no ejecutará jobs")
        es_lider = False

    if es_lider:
        # Job 1: Entrenamiento ML diario a hora fija (03:00 UTC)
        _scheduler.add_job(
            _esperable(job_entrenar_ml),
            trigger="cron",
            hour=HORA_ENTRENAMIENTO_UTC,
            minute=0,
            id="ml_entrenamiento",
            replace_existing=True,
            misfire_grace_time=3600,  # Tolerancia de 1 hora si el job se retrasa
        )

        # Job 2: Cierre de sesiones huérfanas cada 30 minutos
        _scheduler.add_job(
            _esperable(job_cerrar_sesiones_huerfanas),
            trigger="interval",
            minutes=30,
            id="sesiones_huerfanas",
            replace_existing=True,
            misfire_grace_time=300,
        )
    else:
        # Job 3: este proceso no entrena; mantiene al día los modelos que otro guarda en la BD
        _scheduler.add_job(
            job_recargar_modelos,
            trigger="interval",
            minutes=INTERVALO_RECARGA_MODELOS_MINUTOS,
            id="ml_recarga",
            replace_existing=True,
            misfire_grace_time=300,
        )

    _scheduler.start()
    if es_lider:
        logger.info(
            "Scheduler iniciado: ML diario %02d:00 UTC, sesiones huérfanas cada 30 min",
            HORA_ENTRENAMIENTO_UTC,
        )
        # Verificación inmediata de ML (catch-up si el servidor estuvo apagado a las 03:00 UTC)
        asyncio.ensure_future(_esperable(job_entrenar_ml)())
    else:
        logger.info(
            "Scheduler iniciado sin jobs de ML/sesiones (otro proceso los ejecuta); "
            "recarga de modelos cada %d min",
            INTERVALO_RECARGA_MODELOS_MINUTOS,
        )


async def stop_scheduler() -> None:
    """
    Detiene el scheduler al apagar el servidor: no admite jobs nuevos, espera hasta
    TIMEOUT_CIERRE_SEGUNDOS a los que estén en curso y libera el bloqueo.
    """
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
    if _en_curso:
        logger.info("Esperando %d job(s) en curso antes de cerrar", len(_en_curso))
        _, pendientes = await asyncio.wait(set(_en_curso), timeout=TIMEOUT_CIERRE_SEGUNDOS)
        if pendientes:
            logger.warning("%d job(s) no terminaron en %ds", len(pendientes), TIMEOUT_CIERRE_SEGUNDOS)
    await _liberar_bloqueo()
    logger.info("Scheduler detenido")

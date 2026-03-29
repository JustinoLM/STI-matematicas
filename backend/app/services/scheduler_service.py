"""
Scheduler de tareas en background.

Dos jobs:
  1. ML automático cada 3 días — entrena K-Means y reclasifica estudiantes.
  2. Cierre de sesiones huérfanas cada 30 min — sesiones en_progreso con
     más de 90 minutos de inactividad se marcan como ABANDONADA.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.adaptive import PerfilEstudiante, SesionPractica, EstadoSesion
from app.models.config import ConfiguracionSistema
from app.models.user import Estudiante
from app.services.ml_service import ml_service

# ─── Constantes ───────────────────────────────────────────────────────────────

CLAVE_ULTIMO_ENTRENAMIENTO = "ml_ultimo_entrenamiento"
INTERVALO_ENTRENAMIENTO_DIAS = 3
TIMEOUT_SESION_MINUTOS = 90

# ─── Job 1: Entrenamiento ML ──────────────────────────────────────────────────


async def job_entrenar_ml() -> None:
    """
    Verifica si pasaron ≥3 días desde el último entrenamiento y, si es así,
    entrena el modelo K-Means y reclasifica a todos los estudiantes.
    """
    print("⏰ [Scheduler] Verificando si es necesario entrenar ML...")

    async with AsyncSessionLocal() as db:
        # Leer última fecha de entrenamiento
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

        # Cargar todos los perfiles
        perfiles_result = await db.execute(select(PerfilEstudiante))
        perfiles = list(perfiles_result.scalars().all())

        # Obtener org_id de cada estudiante
        est_result = await db.execute(
            select(Estudiante.id, Estudiante.organizacion_id).where(
                Estudiante.organizacion_id.isnot(None)
            )
        )
        org_map: dict[int, int] = {row.id: row.organizacion_id for row in est_result}

        # Agrupar perfiles por organización
        perfiles_por_org: dict[int, list] = defaultdict(list)
        for p in perfiles:
            org_id = org_map.get(p.estudiante_id)
            if org_id:
                perfiles_por_org[org_id].append(p)

        # Entrenar un modelo por organización
        orgs_entrenadas = 0
        for org_id, org_perfiles in perfiles_por_org.items():
            await asyncio.to_thread(ml_service.entrenar_clustering, org_perfiles, org_id)
            if ml_service.has_model_for_org(org_id):
                orgs_entrenadas += 1

        if orgs_entrenadas == 0:
            validos = sum(1 for p in perfiles if ml_service._tiene_datos_suficientes(p))
            print(
                f"   ↳ No hay suficientes perfiles para entrenar "
                f"({validos}/{len(perfiles)} válidos, se necesitan ≥10 por organización)."
            )
            return

        # Reclasificar todos usando el modelo de su organización
        ahora = datetime.utcnow()
        for perfil in perfiles:
            org_id = org_map.get(perfil.estudiante_id)
            perfil_ml, confianza = ml_service.predecir_perfil(perfil, org_id)
            perfil.perfil_aprendizaje = perfil_ml
            perfil.confianza_perfil = round(confianza, 2)
            perfil.fecha_ultima_clasificacion = ahora
            perfil.umbral_promocion_personalizado = ml_service.ajustar_umbral_segun_perfil(perfil)

        # Persistir fecha de entrenamiento
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

        validos = sum(1 for p in perfiles if ml_service._tiene_datos_suficientes(p))
        print(
            f"✅ [Scheduler] ML entrenado: {orgs_entrenadas} org(s), "
            f"{validos} perfiles válidos, {len(perfiles)} estudiantes reclasificados."
        )


# ─── Job 2: Cierre de sesiones huérfanas ─────────────────────────────────────


async def job_cerrar_sesiones_huerfanas() -> None:
    """
    Cierra sesiones de práctica que llevan más de 90 minutos sin actividad.

    Las marca como ABANDONADA con fecha_fin = ahora. No penaliza al estudiante
    — simplemente libera la sesión para que pueda iniciar una nueva.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=TIMEOUT_SESION_MINUTOS)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SesionPractica).where(
                SesionPractica.estado == EstadoSesion.EN_PROGRESO,
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
    (catch-up si el servidor estuvo caído por más de 3 días).
    """
    # Job 1: Revisión de entrenamiento ML cada 24 horas
    _scheduler.add_job(
        job_entrenar_ml,
        trigger="interval",
        hours=24,
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
    print("✅ [Scheduler] Iniciado — ML cada 24h (verif.), sesiones cada 30 min.")

    # Verificación inmediata de ML (catch-up tras reinicio)
    asyncio.create_task(job_entrenar_ml())


async def stop_scheduler() -> None:
    """Detiene el scheduler limpiamente al apagar el servidor."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("👋 [Scheduler] Detenido.")

"""
Router de administración de organizaciones.

Endpoints (todos bajo /admin/organizations — sin auth por ahora):
- POST   /admin/organizations               Crear organización
- GET    /admin/organizations               Listar todas
- GET    /admin/organizations/{id}          Detalle con miembros
- PUT    /admin/organizations/{id}/professors/{prof_id}   Asignar/quitar org a profesor
- PUT    /admin/organizations/{id}/students/{est_id}      Asignar/quitar org a estudiante
"""

import asyncio
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete, update as sa_update, cast, Date
from sqlalchemy.orm import selectinload

from pydantic import BaseModel

from app.api.dependencies import DBSession
from app.models.organization import Organizacion
from app.models.user import Profesor, Estudiante
from app.models.group import Grupo, EstudianteGrupo
from app.models.adaptive import PerfilEstudiante, SesionPractica, EstadoSesion
from app.repositories.gamification_repository import GamificationRepository
from app.services.ml_service import ml_service
from app.schemas.organization import (
    CreateOrganizacionRequest,
    OrganizacionResponse,
    OrganizacionListResponse,
    OrganizacionDetalleResponse,
    MiembroResponse,
    AsignarOrganizacionRequest,
)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_org_or_404(org_id: int, db: AsyncSession) -> Organizacion:
    result = await db.execute(select(Organizacion).where(Organizacion.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    return org


async def _contar_miembros(org_id: int, db: AsyncSession) -> tuple[int, int]:
    """Retorna (total_profesores, total_estudiantes) para una org."""
    profs = await db.execute(
        select(func.count()).select_from(Profesor).where(Profesor.organizacion_id == org_id)
    )
    ests = await db.execute(
        select(func.count()).select_from(Estudiante).where(Estudiante.organizacion_id == org_id)
    )
    return profs.scalar_one(), ests.scalar_one()


def _to_response(org: Organizacion, total_profs: int = 0, total_ests: int = 0) -> OrganizacionResponse:
    return OrganizacionResponse(
        id=org.id,
        nombre=org.nombre,
        codigo=org.codigo,
        descripcion=org.descripcion,
        ciudad=org.ciudad,
        pais=org.pais,
        fecha_creacion=org.fecha_creacion,
        activa=bool(org.activa),
        post_test_activo=bool(org.post_test_activo),
        total_profesores=total_profs,
        total_estudiantes=total_ests,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/admin/organizations", response_model=OrganizacionResponse, status_code=status.HTTP_201_CREATED)
async def crear_organizacion(data: CreateOrganizacionRequest, db: DBSession):
    """Crea una nueva organización / colegio."""
    # Verificar unicidad de código y nombre
    existing = await db.execute(
        select(Organizacion).where(
            (Organizacion.codigo == data.codigo.upper()) |
            (Organizacion.nombre == data.nombre)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una organización con ese código o nombre")

    org = Organizacion(
        nombre=data.nombre.strip(),
        codigo=data.codigo.strip().upper(),
        descripcion=data.descripcion,
        ciudad=data.ciudad,
        pais=data.pais or "Panamá",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return _to_response(org)


@router.get("/admin/organizations", response_model=OrganizacionListResponse)
async def listar_organizaciones(db: DBSession):
    """Lista todas las organizaciones con conteo de miembros."""
    result = await db.execute(select(Organizacion).order_by(Organizacion.nombre))
    orgs = result.scalars().all()

    items = []
    for org in orgs:
        profs, ests = await _contar_miembros(org.id, db)
        items.append(_to_response(org, profs, ests))

    return OrganizacionListResponse(total=len(items), organizaciones=items)


@router.get("/admin/organizations/{org_id}", response_model=OrganizacionDetalleResponse)
async def detalle_organizacion(org_id: int, db: DBSession):
    """Detalle de una organización con lista de miembros."""
    org = await _get_org_or_404(org_id, db)

    profs_result = await db.execute(
        select(Profesor).where(Profesor.organizacion_id == org_id)
    )
    profesores = profs_result.scalars().all()

    ests_result = await db.execute(
        select(Estudiante).where(Estudiante.organizacion_id == org_id)
    )
    estudiantes = ests_result.scalars().all()

    return OrganizacionDetalleResponse(
        id=org.id,
        nombre=org.nombre,
        codigo=org.codigo,
        descripcion=org.descripcion,
        ciudad=org.ciudad,
        pais=org.pais,
        fecha_creacion=org.fecha_creacion,
        activa=bool(org.activa),
        total_profesores=len(profesores),
        total_estudiantes=len(estudiantes),
        profesores=[
            MiembroResponse(
                id=p.id,
                codigo=p.codigo_profesor,
                nombre_completo=p.nombre_completo,
                tipo="profesor",
            )
            for p in profesores
        ],
        estudiantes=[
            MiembroResponse(
                id=e.id,
                codigo=e.codigo_estudiante,
                nombre_completo=e.nombre_completo,
                tipo="estudiante",
            )
            for e in estudiantes
        ],
    )


@router.put("/admin/organizations/{org_id}/professors/{prof_id}", response_model=dict)
async def asignar_org_a_profesor(org_id: int, prof_id: int, db: DBSession):
    """Asigna el profesor a la organización (o quita asignación si org_id=0)."""
    # Verificar que la org existe
    await _get_org_or_404(org_id, db)

    result = await db.execute(select(Profesor).where(Profesor.id == prof_id))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    prof.organizacion_id = org_id
    await db.commit()
    return {"success": True, "mensaje": f"Profesor asignado a organización {org_id}"}


@router.delete("/admin/organizations/{org_id}/professors/{prof_id}", response_model=dict)
async def quitar_org_a_profesor(org_id: int, prof_id: int, db: DBSession):
    """Quita al profesor de la organización."""
    result = await db.execute(select(Profesor).where(Profesor.id == prof_id))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    prof.organizacion_id = None
    await db.commit()
    return {"success": True, "mensaje": "Profesor removido de la organización"}


@router.put("/admin/organizations/{org_id}/students/{est_id}", response_model=dict)
async def asignar_org_a_estudiante(org_id: int, est_id: int, db: DBSession):
    """Asigna el estudiante a la organización."""
    await _get_org_or_404(org_id, db)

    result = await db.execute(select(Estudiante).where(Estudiante.id == est_id))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    est.organizacion_id = org_id
    await db.commit()
    return {"success": True, "mensaje": f"Estudiante asignado a organización {org_id}"}


@router.delete("/admin/organizations/{org_id}/students/{est_id}", response_model=dict)
async def quitar_org_a_estudiante(org_id: int, est_id: int, db: DBSession):
    """Quita al estudiante de la organización."""
    result = await db.execute(select(Estudiante).where(Estudiante.id == est_id))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    est.organizacion_id = None
    await db.commit()
    return {"success": True, "mensaje": "Estudiante removido de la organización"}


@router.delete("/admin/organizations/{org_id}", response_model=dict)
async def eliminar_organizacion(org_id: int, db: DBSession):
    """
    Elimina una organización.
    Desvincula a todos sus miembros (organizacion_id → None) antes de borrar.
    """
    org = await _get_org_or_404(org_id, db)

    # Desvincular profesores y estudiantes
    profs = await db.execute(select(Profesor).where(Profesor.organizacion_id == org_id))
    for p in profs.scalars().all():
        p.organizacion_id = None

    ests = await db.execute(select(Estudiante).where(Estudiante.organizacion_id == org_id))
    for e in ests.scalars().all():
        e.organizacion_id = None

    await db.delete(org)
    await db.commit()
    return {"success": True, "mensaje": f"Organización '{org.nombre}' eliminada"}


@router.delete("/admin/professors/{prof_id}", response_model=dict)
async def eliminar_profesor(prof_id: int, db: DBSession):
    """
    Elimina un profesor. Cascade manual:
    elimina sus grupos (y las relaciones estudiante-grupo de esos grupos).
    """
    result = await db.execute(select(Profesor).where(Profesor.id == prof_id))
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    nombre = prof.nombre_completo

    # 1) Obtener grupos del profesor y eliminar sus relaciones estudiante-grupo
    grupos_result = await db.execute(select(Grupo).where(Grupo.profesor_id == prof_id))
    grupos = grupos_result.scalars().all()
    for grupo in grupos:
        await db.execute(sa_delete(EstudianteGrupo).where(EstudianteGrupo.grupo_id == grupo.id))
        await db.delete(grupo)
    await db.flush()

    # 2) Eliminar el profesor
    await db.delete(prof)
    await db.commit()
    return {"success": True, "mensaje": f"Profesor '{nombre}' eliminado"}


@router.delete("/admin/students/{est_id}", response_model=dict)
async def eliminar_estudiante(est_id: int, db: DBSession):
    """
    Elimina un estudiante. Cascade manual:
    lo saca de todos los grupos antes de borrar.
    """
    result = await db.execute(select(Estudiante).where(Estudiante.id == est_id))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    nombre = est.nombre_completo

    # 1) Sacar de todos los grupos
    await db.execute(sa_delete(EstudianteGrupo).where(EstudianteGrupo.estudiante_id == est_id))
    await db.flush()

    # 2) Eliminar el estudiante
    await db.delete(est)
    await db.commit()
    return {"success": True, "mensaje": f"Estudiante '{nombre}' eliminado"}


@router.get("/admin/users", response_model=dict)
async def listar_todos_usuarios(db: DBSession):
    """Lista todos los profesores y estudiantes para la asignación en AdminPage."""
    profs_result = await db.execute(select(Profesor).order_by(Profesor.nombre_completo))
    ests_result = await db.execute(select(Estudiante).order_by(Estudiante.nombre_completo))

    profesores = profs_result.scalars().all()
    estudiantes = ests_result.scalars().all()

    return {
        "profesores": [
            {
                "id": p.id,
                "codigo": p.codigo_profesor,
                "nombre_completo": p.nombre_completo,
                "organizacion_id": p.organizacion_id,
                "institucion": p.institucion,
                "password_plain": p.password_plain,
                "activo": bool(p.activo),
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                "ultimo_acceso": p.ultimo_acceso.isoformat() if p.ultimo_acceso else None,
                # Secciones que enseña el profesor (para filtrado de estudiantes)
                "secciones_asignadas": p.secciones_asignadas or [],
            }
            for p in profesores
        ],
        "estudiantes": [
            {
                "id": e.id,
                "codigo": e.codigo_estudiante,
                "nombre_completo": e.nombre_completo,
                "organizacion_id": e.organizacion_id,
                "grado_academico": e.grado_academico,
                "password_plain": e.password_plain,
                "activo": bool(e.activo),
                "fecha_creacion": e.fecha_creacion.isoformat() if e.fecha_creacion else None,
                "ultimo_acceso": e.ultimo_acceso.isoformat() if e.ultimo_acceso else None,
                "puntos_totales": e.puntos_totales,
            }
            for e in estudiantes
        ],
    }


# ─── Admin: Secciones por profesor ───────────────────────────────────────────

class SeccionesProfesorRequest(BaseModel):
    secciones: list[str]  # Ej: ["6A", "6B"]


@router.get("/admin/organizations/{org_id}/grados", response_model=list)
async def listar_grados_org(org_id: int, db: DBSession):
    """
    Devuelve los valores únicos de `grado_academico` de los estudiantes
    de la organización, ordenados alfabéticamente.
    Sirve para poblar los checkboxes en la UI del admin.
    """
    await _get_org_or_404(org_id, db)
    result = await db.execute(
        select(Estudiante.grado_academico)
        .where(
            Estudiante.organizacion_id == org_id,
            Estudiante.grado_academico.is_not(None),
            Estudiante.grado_academico != "",
        )
        .distinct()
        .order_by(Estudiante.grado_academico)
    )
    return [row[0] for row in result.all()]


@router.patch("/admin/professors/{prof_id}/secciones", response_model=dict)
async def actualizar_secciones_profesor(
    prof_id: int,
    payload: SeccionesProfesorRequest,
    db: DBSession,
):
    """
    Actualiza las secciones (grados) que enseña el profesor.
    Pasar lista vacía [] para eliminar el filtro (ve todos los estudiantes de la org).
    """
    result = await db.execute(select(Profesor).where(Profesor.id == prof_id))
    profesor = result.scalar_one_or_none()
    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    # Normalizar: quitar duplicados y ordenar
    secciones_limpias = sorted(set(s.strip() for s in payload.secciones if s.strip()))
    profesor.secciones_asignadas = secciones_limpias if secciones_limpias else None
    await db.commit()

    return {
        "success": True,
        "profesor_id": prof_id,
        "secciones_asignadas": profesor.secciones_asignadas or [],
        "mensaje": (
            f"Secciones actualizadas: {', '.join(secciones_limpias)}"
            if secciones_limpias
            else "Filtro de secciones eliminado (ve todos los estudiantes de la org)"
        ),
    }


# ─── Admin: Post-Test ─────────────────────────────────────────────────────────

@router.post("/admin/organizations/{org_id}/post-test/activate", response_model=dict)
async def activar_post_test(org_id: int, db: DBSession):
    """
    Activa el post-test final para todos los estudiantes de la organización.
    Mientras esté activo, los estudiantes verán una pantalla de post-test
    en lugar de la práctica normal hasta completarlo.
    """
    org = await _get_org_or_404(org_id, db)
    if org.post_test_activo:
        return {"success": True, "mensaje": "El post-test ya estaba activo", "activo": True}
    org.post_test_activo = True
    await db.commit()
    return {"success": True, "mensaje": f"Post-test activado para '{org.nombre}'", "activo": True}


@router.delete("/admin/organizations/{org_id}/post-test/activate", response_model=dict)
async def desactivar_post_test(org_id: int, db: DBSession):
    """
    Desactiva el post-test final para la organización.
    """
    org = await _get_org_or_404(org_id, db)
    org.post_test_activo = False
    await db.commit()
    return {"success": True, "mensaje": f"Post-test desactivado para '{org.nombre}'", "activo": False}


# ─── Admin: agregar puntos ────────────────────────────────────────────────────

class AgregarPuntosRequest(BaseModel):
    estudiante_id: int
    puntos: int


@router.post("/admin/gamification/add-points", response_model=dict)
async def admin_agregar_puntos(payload: AgregarPuntosRequest, db: DBSession):
    """Agrega puntos a un estudiante sin autenticación (solo para testing/admin)."""
    if payload.puntos <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser positiva")

    result = await db.execute(select(Estudiante).where(Estudiante.id == payload.estudiante_id))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    repo = GamificationRepository(db)
    nuevo_saldo = await repo.agregar_puntos(
        estudiante_id=payload.estudiante_id,
        cantidad=payload.puntos,
        concepto="Ajuste manual (admin)",
    )
    return {
        "success": True,
        "nombre": est.nombre_completo,
        "puntos_agregados": payload.puntos,
        "nuevo_saldo": nuevo_saldo,
    }


# ─── Admin: Machine Learning ───────────────────────────────────────────────────

@router.get("/admin/ml/estado", response_model=dict)
async def estado_ml(db: DBSession):
    """
    Devuelve el estado actual de los modelos de Machine Learning por organización.
    """
    orgs_result = await db.execute(select(Organizacion.id, Organizacion.nombre))
    orgs = orgs_result.all()

    orgs_con_modelo = [
        {"id": org.id, "nombre": org.nombre}
        for org in orgs
        if ml_service.has_model_for_org(org.id)
    ]

    return {
        "orgs_con_modelo": orgs_con_modelo,
        "total_orgs_entrenadas": len(orgs_con_modelo),
        "prediccion_entrenado": ml_service.prediccion_model is not None,
        "umbrales_por_perfil": {
            perfil.value: umbral
            for perfil, umbral in ml_service.UMBRALES_POR_PERFIL.items()
        },
    }


@router.post("/admin/ml/entrenar", response_model=dict)
async def entrenar_modelos_ml(db: DBSession):
    """
    Entrena (o re-entrena) el modelo de clustering K-Means por organización.

    Cada org obtiene su propio modelo entrenado solo con sus estudiantes.
    Requiere mínimo 10 estudiantes con datos suficientes (≥3 sesiones) por org.
    """
    from collections import defaultdict

    # 1. Cargar todos los perfiles y el org_id de cada estudiante
    result = await db.execute(select(PerfilEstudiante))
    perfiles: list[PerfilEstudiante] = list(result.scalars().all())

    est_result = await db.execute(
        select(Estudiante.id, Estudiante.organizacion_id).where(
            Estudiante.organizacion_id.isnot(None)
        )
    )
    org_map: dict[int, int] = {row.id: row.organizacion_id for row in est_result}

    # 2. Agrupar por organización
    perfiles_por_org: dict[int, list] = defaultdict(list)
    for p in perfiles:
        oid = org_map.get(p.estudiante_id)
        if oid:
            perfiles_por_org[oid].append(p)

    # 3. Entrenar un modelo por organización y persistir en BD
    orgs_entrenadas = 0
    for org_id, org_perfiles in perfiles_por_org.items():
        await asyncio.to_thread(ml_service.entrenar_clustering, org_perfiles, org_id)
        if ml_service.has_model_for_org(org_id):
            orgs_entrenadas += 1
            # Persistir en PostgreSQL para sobrevivir reinicios
            n_validos = sum(
                1 for p in org_perfiles if ml_service._tiene_datos_suficientes(p)
            )
            await ml_service.save_org_model_to_db(org_id, db, perfiles_entrenados=n_validos)

    if orgs_entrenadas == 0:
        perfiles_validos = sum(1 for p in perfiles if ml_service._tiene_datos_suficientes(p))
        return {
            "success": False,
            "mensaje": (
                "No hay suficientes perfiles para entrenar ninguna organización. "
                f"Se necesitan ≥10 por org. Válidos totales: {perfiles_validos}/{len(perfiles)}."
            ),
            "total_perfiles": len(perfiles),
            "perfiles_validos": perfiles_validos,
        }

    # 4. Reclasificar todos usando el modelo de su organización
    reclasificados = 0
    ahora = datetime.utcnow()
    for perfil in perfiles:
        org_id = org_map.get(perfil.estudiante_id)
        perfil_ml, confianza = ml_service.predecir_perfil(perfil, org_id)
        perfil.perfil_aprendizaje = perfil_ml
        perfil.confianza_perfil = round(confianza, 2)
        perfil.fecha_ultima_clasificacion = ahora
        perfil.umbral_promocion_personalizado = ml_service.ajustar_umbral_segun_perfil(perfil)
        reclasificados += 1

    await db.commit()

    perfiles_validos = sum(1 for p in perfiles if ml_service._tiene_datos_suficientes(p))
    return {
        "success": True,
        "mensaje": (
            f"{orgs_entrenadas} organización(es) entrenadas. "
            f"{reclasificados} estudiantes reclasificados."
        ),
        "orgs_entrenadas": orgs_entrenadas,
        "total_perfiles": len(perfiles),
        "perfiles_validos": perfiles_validos,
        "reclasificados": reclasificados,
    }


# ─── Admin: Estadísticas del sistema ──────────────────────────────────────────

@router.get("/admin/sistema/stats", response_model=dict)
async def sistema_stats(db: DBSession):
    """
    Estadísticas globales del sistema para el tab de Sistema en el panel admin.
    """
    today = date.today()
    hace_7_dias = today - timedelta(days=7)

    # Totales de usuarios y estructura
    total_est = await db.scalar(select(func.count()).select_from(Estudiante))
    total_prof = await db.scalar(select(func.count()).select_from(Profesor))
    total_grupos = await db.scalar(select(func.count()).select_from(Grupo))
    total_orgs = await db.scalar(select(func.count()).select_from(Organizacion))

    # Sesiones de práctica
    sesiones_hoy = await db.scalar(
        select(func.count()).select_from(SesionPractica)
        .where(cast(SesionPractica.fecha_inicio, Date) == today)
    )
    sesiones_semana = await db.scalar(
        select(func.count()).select_from(SesionPractica)
        .where(cast(SesionPractica.fecha_inicio, Date) >= hace_7_dias)
    )
    sesiones_activas = await db.scalar(
        select(func.count()).select_from(SesionPractica)
        .where(SesionPractica.estado == EstadoSesion.EN_PROGRESO)
    )
    total_sesiones = await db.scalar(
        select(func.count()).select_from(SesionPractica)
    )

    # Perfiles ML clasificados (no NO_CLASIFICADO)
    from app.models.adaptive import PerfilAprendizaje
    perfiles_clasificados = await db.scalar(
        select(func.count()).select_from(PerfilEstudiante)
        .where(PerfilEstudiante.perfil_aprendizaje != PerfilAprendizaje.NO_CLASIFICADO)
    )

    return {
        "total_estudiantes": total_est or 0,
        "total_profesores": total_prof or 0,
        "total_grupos": total_grupos or 0,
        "total_organizaciones": total_orgs or 0,
        "sesiones_hoy": sesiones_hoy or 0,
        "sesiones_semana": sesiones_semana or 0,
        "sesiones_activas": sesiones_activas or 0,
        "total_sesiones": total_sesiones or 0,
        "perfiles_clasificados": perfiles_clasificados or 0,
    }

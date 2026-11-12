"""Router de profesores - APIs completas."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_adaptive_service,
    get_current_teacher,
    get_practice_service,
)
from app.core.database import get_db
from app.models.adaptive import PerfilEstudiante
from app.models.organization import Organizacion
from app.models.user import Estudiante, Profesor
from app.schemas.teacher import (
    AlertaEstudianteResponse,
    ConfiguracionPracticaCreate,
    ConfiguracionPracticaResponse,
    DesafioGrupalCreate,
    DesafioGrupalDetalle,
    EstadisticasGrupo,
    GrupoDetalle,
    GrupoResumen,
)
from app.services.adaptive_service import AdaptiveService
from app.services.practice_service import PracticeService
from app.services.school_service import SchoolService
from app.services.teacher_service import TeacherService

router = APIRouter()


# ==================== PERFIL PROPIO ====================

@router.get("/me")
async def obtener_perfil_profesor(
    profesor: Profesor = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Retorna datos básicos del profesor autenticado, incluyendo su organización."""
    organizacion_nombre: Optional[str] = None
    if profesor.organizacion_id:
        org_result = await db.execute(
            select(Organizacion).where(Organizacion.id == profesor.organizacion_id)
        )
        org = org_result.scalar_one_or_none()
        if org:
            organizacion_nombre = org.nombre

    return {
        "id": profesor.id,
        "codigo_profesor": profesor.codigo_profesor,
        "nombre_completo": profesor.nombre_completo,
        "institucion": profesor.institucion,
        "grado_academico": profesor.grado_academico,
        "organizacion_nombre": organizacion_nombre,
    }


async def get_teacher_service(db: AsyncSession = Depends(get_db)) -> TeacherService:
    """Dependency para TeacherService."""
    return TeacherService(db)


# ==================== GRUPOS ====================

@router.get("/groups", response_model=List[GrupoResumen])
async def listar_grupos(
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service),
    anio_lectivo_id: Optional[int] = Query(None, description="Solo los grupos de este salón (año lectivo)"),
):
    """Lista los grupos de los salones del profesor (para crearlos: POST /salones/{id}/grupos)."""
    return await service.get_grupos(profesor.id, anio_lectivo_id)


@router.get("/groups/{group_id}", response_model=GrupoDetalle)
async def obtener_grupo(
    group_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Obtiene detalle de un grupo."""
    grupo = await service.get_grupo_detalle(group_id, profesor.id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return grupo


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_grupo(
    group_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Desactiva un grupo. Solo su profesor, y solo con el año lectivo activo."""
    try:
        await service.eliminar_grupo(group_id, profesor.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/groups/{group_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def agregar_estudiante(
    group_id: int,
    student_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Agrega al grupo un estudiante del mismo salón."""
    try:
        await service.agregar_estudiante(group_id, student_id, profesor.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/groups/{group_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_estudiante(
    group_id: int,
    student_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Remueve estudiante de grupo."""
    try:
        await service.remover_estudiante(group_id, student_id, profesor.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== CONFIGURACIÓN ====================

@router.post("/configuration", response_model=ConfiguracionPracticaResponse, status_code=status.HTTP_201_CREATED)
async def crear_configuracion(
    data: ConfiguracionPracticaCreate,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Aplica una configuración de práctica (decimales) a un salón (año lectivo activo)."""
    try:
        return await service.crear_configuracion(profesor.id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== DESAFÍOS GRUPALES ====================

@router.post("/challenges", response_model=DesafioGrupalDetalle, status_code=status.HTTP_201_CREATED)
async def crear_desafio(
    data: DesafioGrupalCreate,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Crea desafío grupal."""
    return await service.crear_desafio_grupal(profesor.id, data)


@router.get("/challenges", response_model=List[DesafioGrupalDetalle])
async def listar_desafios(
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Lista desafíos del profesor."""
    return await service.get_desafios(profesor.id)


@router.delete("/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_desafio(
    challenge_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Elimina desafío (soft delete)."""
    try:
        await service.eliminar_desafio(challenge_id, profesor.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== MONITOREO ====================

@router.get("/groups/{group_id}/statistics", response_model=EstadisticasGrupo)
async def obtener_estadisticas(
    group_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Obtiene estadísticas del grupo."""
    stats = await service.get_estadisticas_grupo(group_id, profesor.id)
    if not stats:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return stats


@router.get("/alerts", response_model=List[AlertaEstudianteResponse])
async def listar_alertas(
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Lista alertas de los estudiantes de los salones activos del profesor."""
    return await service.get_alertas(profesor.id)


# ==================== BÚSQUEDA & ESTUDIANTES ====================

@router.get("/students", response_model=List[dict])
async def listar_estudiantes_de_mis_salones(
    profesor: Profesor = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Filtrar por nombre o código"),
):
    """
    Lista los estudiantes de los salones activos del profesor, con su salón y grado.
    Para buscar estudiantes de la organización y asignarlos a un salón:
    GET /teachers/salones/{anio_lectivo_id}/candidatos.
    """
    school = SchoolService(db)
    ids = await school.ids_estudiantes_del_profesor(profesor.id)
    if not ids:
        return []

    result = await db.execute(
        select(Estudiante, PerfilEstudiante)
        .outerjoin(PerfilEstudiante, Estudiante.id == PerfilEstudiante.estudiante_id)
        .where(Estudiante.id.in_(ids))
        .order_by(Estudiante.nombre_completo)
    )
    salones = await school.salones_de_estudiantes(ids)

    datos = []
    for e, perfil in result.all():
        if q:
            q_lower = q.lower()
            if q_lower not in e.nombre_completo.lower() and q_lower not in e.codigo_estudiante.lower():
                continue
        salon = salones.get(e.id, {})
        datos.append({
            "id": e.id,
            "codigo_estudiante": e.codigo_estudiante,
            "nombre_completo": e.nombre_completo,
            "salon_nombre": salon.get("salon_nombre"),
            "grado": salon.get("grado"),
            "anio_lectivo_id": salon.get("anio_lectivo_id"),
            "activo": bool(e.activo),
            "nivel_actual": perfil.nivel_actual if perfil else 1,
            "precision_ultimos_15": round(float(perfil.precision_ultimos_15 or 0) * 100, 1) if perfil else 0.0,
        })

    return datos


async def _estudiante_de_mi_organizacion(
    db: AsyncSession, profesor: Profesor, student_id: int
) -> Estudiante:
    """
    Devuelve el estudiante solo si pertenece a la organización del profesor.
    Un profesor sin organización asignada no ve a ningún estudiante.
    Responde 404 también cuando el estudiante existe en otra organización, para no
    revelar su existencia.
    """
    if profesor.organizacion_id is not None:
        result = await db.execute(
            select(Estudiante).where(
                Estudiante.id == student_id,
                Estudiante.organizacion_id == profesor.organizacion_id,
            )
        )
        estudiante = result.scalar_one_or_none()
        if estudiante:
            return estudiante
    raise HTTPException(status_code=404, detail="Estudiante no encontrado en tu organización")


@router.get("/students/{student_id}/profile")
async def obtener_perfil_estudiante(
    student_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    adaptive_service: AdaptiveService = Depends(get_adaptive_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene el perfil adaptativo de un estudiante de la organización del profesor.
    Retorna los mismos datos que GET /adaptive/profile pero accesible para profesores,
    con el nombre del estudiante añadido.
    """
    estudiante = await _estudiante_de_mi_organizacion(db, profesor, student_id)

    perfil = await adaptive_service.get_perfil(student_id)
    perfil_dict = perfil.model_dump()
    perfil_dict["nombre_estudiante"] = estudiante.nombre_completo
    return perfil_dict


@router.get("/students/{student_id}/stats")
async def obtener_stats_estudiante(
    student_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    practice_service: PracticeService = Depends(get_practice_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene las estadísticas globales de práctica de un estudiante.
    Retorna los mismos datos que GET /practices/stats pero accesible para profesores.
    """
    await _estudiante_de_mi_organizacion(db, profesor, student_id)
    return await practice_service.get_global_stats(student_id)

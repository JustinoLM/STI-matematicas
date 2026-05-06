"""Router de profesores - APIs completas."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.dependencies import (
    get_current_teacher,
    get_adaptive_service,
    get_practice_service,
)
from app.models.user import Profesor, Estudiante
from app.models.adaptive import PerfilEstudiante
from app.models.organization import Organizacion
from app.services.adaptive_service import AdaptiveService
from app.services.practice_service import PracticeService
from app.services.teacher_service import TeacherService
from app.schemas.teacher import (
    GrupoCreate, GrupoUpdate, GrupoDetalle, GrupoResumen,
    ConfiguracionPracticaCreate, ConfiguracionPracticaResponse,
    DesafioGrupalCreate, DesafioGrupalDetalle, DesafioGrupalResumen,
    EstadisticasGrupo, ProgresoEstudiante, AlertaEstudianteResponse,
    BuscarEstudianteRequest, EstudianteSearchResult
)
from pydantic import BaseModel

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


class BulkAddStudentsRequest(BaseModel):
    codigos: List[str]


class BulkAddError(BaseModel):
    fila: int
    codigo: str
    mensaje: str


class BulkAddResult(BaseModel):
    total: int
    agregados: int
    errores: List[BulkAddError]


async def get_teacher_service(db: AsyncSession = Depends(get_db)) -> TeacherService:
    """Dependency para TeacherService."""
    return TeacherService(db)


# ==================== IMPORTACIÓN MASIVA A GRUPO ====================

@router.post("/groups/{group_id}/students/bulk", response_model=BulkAddResult)
async def bulk_add_students_to_group(
    group_id: int,
    data: BulkAddStudentsRequest,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Añade una lista de estudiantes (por código) a un grupo en bulk.
    Los estudiantes deben pertenecer a la misma organización del profesor.
    Continúa aunque alguna fila falle — devuelve resumen de éxitos y errores.
    """
    from sqlalchemy import select as sa_select
    from app.models.user import Estudiante

    errores: List[BulkAddError] = []
    agregados = 0

    for i, codigo in enumerate(data.codigos, start=1):
        codigo = codigo.strip().upper()
        if not codigo:
            errores.append(BulkAddError(fila=i, codigo=codigo, mensaje="Código vacío"))
            continue
        try:
            # Buscar estudiante en la organización del profesor
            result = await db.execute(
                sa_select(Estudiante).where(
                    Estudiante.codigo_estudiante == codigo,
                    Estudiante.organizacion_id == profesor.organizacion_id,
                )
            )
            est = result.scalar_one_or_none()
            if not est:
                errores.append(BulkAddError(
                    fila=i, codigo=codigo,
                    mensaje="Estudiante no encontrado en tu organización"
                ))
                continue
            await service.agregar_estudiante(group_id, est.id, profesor.id)
            agregados += 1
        except ValueError as e:
            errores.append(BulkAddError(fila=i, codigo=codigo, mensaje=str(e)))
        except Exception:
            errores.append(BulkAddError(
                fila=i, codigo=codigo, mensaje="Error inesperado al agregar"
            ))

    return BulkAddResult(total=len(data.codigos), agregados=agregados, errores=errores)


# ==================== GRUPOS ====================

@router.post("/groups", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def crear_grupo(
    data: GrupoCreate,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Crea un nuevo grupo."""
    return await service.crear_grupo(profesor.id, data)


@router.get("/groups", response_model=List[GrupoResumen])
async def listar_grupos(
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Lista grupos del profesor con resumen."""
    return await service.get_grupos(profesor.id)


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
    """Elimina un grupo y sus relaciones. Solo el dueño puede eliminarlo."""
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
    """Agrega estudiante a grupo."""
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
    """Crea configuración de práctica para un grupo."""
    try:
        return await service.crear_configuracion(profesor.id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/groups/{group_id}/configuration", response_model=ConfiguracionPracticaResponse)
async def obtener_configuracion(
    group_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Obtiene configuración activa de un grupo."""
    config = await service.get_configuracion_activa(group_id, profesor.id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return config


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
    """Lista alertas activas de todos los grupos."""
    return await service.get_alertas(profesor.id)


# ==================== BÚSQUEDA & ESTUDIANTES ====================

@router.get("/students", response_model=List[dict])
async def listar_estudiantes_organizacion(
    profesor: Profesor = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Filtrar por nombre o código"),
):
    """
    Lista los estudiantes de la organización del profesor.

    Filtrado por secciones:
    - Si el profesor tiene `secciones_asignadas` (ej. ["6A", "6B"]), solo devuelve
      estudiantes cuyo `grado_academico` esté en esa lista.
    - Si `secciones_asignadas` está vacío o es null, devuelve todos los estudiantes
      de la organización (comportamiento legacy).
    """
    if not profesor.organizacion_id:
        return []

    secciones: list[str] = profesor.secciones_asignadas or []

    stmt = (
        select(Estudiante, PerfilEstudiante)
        .outerjoin(PerfilEstudiante, Estudiante.id == PerfilEstudiante.estudiante_id)
        .where(Estudiante.organizacion_id == profesor.organizacion_id)
    )

    # Filtrar por sección solo si el profesor tiene secciones asignadas
    if secciones:
        stmt = stmt.where(Estudiante.grado_academico.in_(secciones))

    result = await db.execute(stmt)
    rows = result.all()

    datos = []
    for e, perfil in rows:
        # Filtro opcional de búsqueda por nombre/código
        if q:
            q_lower = q.lower()
            if q_lower not in e.nombre_completo.lower() and q_lower not in e.codigo_estudiante.lower():
                continue
        datos.append({
            "id": e.id,
            "codigo_estudiante": e.codigo_estudiante,
            "nombre_completo": e.nombre_completo,
            "grado_academico": e.grado_academico,
            "activo": bool(e.activo),
            "nivel_actual": perfil.nivel_actual if perfil else 1,
            "precision_ultimos_15": round(float(perfil.precision_ultimos_15 or 0) * 100, 1) if perfil else 0.0,
        })

    return datos


@router.post("/students/search", response_model=List[EstudianteSearchResult])
async def buscar_estudiantes(
    request: BuscarEstudianteRequest,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Busca estudiantes por nombre o código."""
    # TODO: Implementar búsqueda avanzada
    return []


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
    est_result = await db.execute(select(Estudiante).where(Estudiante.id == student_id))
    estudiante = est_result.scalar_one_or_none()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if profesor.organizacion_id and estudiante.organizacion_id != profesor.organizacion_id:
        raise HTTPException(status_code=404, detail="Estudiante no pertenece a tu organización")

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
    if profesor.organizacion_id:
        est_result = await db.execute(
            select(Estudiante).where(
                Estudiante.id == student_id,
                Estudiante.organizacion_id == profesor.organizacion_id
            )
        )
        if not est_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Estudiante no encontrado en tu organización")

    return await practice_service.get_global_stats(student_id)


# ==================== REPORTES ====================

@router.get("/groups/{group_id}/report")
async def generar_reporte(
    group_id: int,
    profesor: Profesor = Depends(get_current_teacher),
    service: TeacherService = Depends(get_teacher_service)
):
    """Genera reporte PDF del grupo."""
    # TODO: Implementar generación de PDF
    raise HTTPException(status_code=501, detail="No implementado")

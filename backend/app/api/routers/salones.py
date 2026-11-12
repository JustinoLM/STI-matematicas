"""
Salones del profesor (organización escolar).

Endpoints (prefijo /api/teachers):
- GET    /salones                                   Mis salones (activos y cerrados)
- POST   /salones                                   Crear o abrir un salón para el año actual
- GET    /salones/{anio_lectivo_id}                 Detalle: estudiantes, grupos, trimestres, configuración
- GET    /salones/{anio_lectivo_id}/candidatos      Estudiantes de la organización para asignar
- POST   /salones/{anio_lectivo_id}/estudiantes/{estudiante_id}    Asignar al salón
- DELETE /salones/{anio_lectivo_id}/estudiantes/{estudiante_id}    Quitar del salón
- POST   /salones/{anio_lectivo_id}/estudiantes/bulk               Asignar varios por código
- POST   /salones/{anio_lectivo_id}/grupos          Crear un grupo dentro del salón
- GET    /salones/{anio_lectivo_id}/configuration   Configuración de práctica (decimales)

Un año lectivo cerrado es de solo lectura: cualquier cambio responde 409 (codigo ANIO_CERRADO).
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, select

from app.api.dependencies import CurrentTeacher, DBSession
from app.models.school import ANIO_ACTIVO, AnioLectivo
from app.models.user import Estudiante
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.school import (
    BulkMatriculaError,
    BulkMatriculaRequest,
    BulkMatriculaResult,
    CandidatoSalon,
    EstudianteDelSalon,
    GrupoDelSalon,
    SalonCreate,
    SalonDetalle,
    SalonResumen,
    TrimestreOut,
)
from app.schemas.teacher import ConfiguracionPracticaResponse, GrupoCreate, GrupoDetalle
from app.services.school_service import ErrorSalon, SchoolService
from app.services.teacher_service import TeacherService

router = APIRouter()


async def _resumen(school: SchoolService, al: AnioLectivo) -> SalonResumen:
    return SalonResumen(
        anio_lectivo_id=al.id,
        salon_id=al.salon_id,
        nombre=al.salon.nombre,
        grado=al.salon.grado,
        anio=al.anio,
        estado=al.estado,
        cerrado=al.estado != ANIO_ACTIVO,
        cantidad_estudiantes=len(await school.ids_estudiantes_del_anio(al.id)),
        cantidad_grupos=len(await school.grupos_del_anio(al.id)),
    )


async def _detalle(db, school: SchoolService, al: AnioLectivo) -> SalonDetalle:
    await db.refresh(al, attribute_names=["salon", "profesor"])
    estudiantes = [
        EstudianteDelSalon(
            estudiante_id=e.id,
            codigo_estudiante=e.codigo_estudiante,
            nombre_completo=e.nombre_completo,
            nivel_actual=perfil.nivel_actual if perfil else 1,
            precision_ultimos_15=round(float(perfil.precision_ultimos_15 or 0) * 100, 1) if perfil else 0.0,
            fecha_ingreso=m.fecha_ingreso,
        )
        for e, m, perfil in await school.estudiantes_del_anio(al.id)
    ]
    grupos = [
        GrupoDelSalon(id=g.id, nombre=g.nombre, estudiantes_ids=[r.estudiante_id for r in g.estudiantes if r.activo])
        for g in await school.grupos_del_anio(al.id)
    ]
    trimestres = await school.trimestres(al.salon.organizacion_id, al.anio, crear=al.estado == ANIO_ACTIVO)
    config = await TeacherRepository(db).get_configuracion_activa(al.id)
    resumen = await _resumen(school, al)
    return SalonDetalle(
        **resumen.model_dump(),
        profesor_nombre=al.profesor.nombre_completo,
        trimestres=[TrimestreOut.model_validate(t) for t in trimestres],
        estudiantes=estudiantes,
        grupos=grupos,
        configuracion=ConfiguracionPracticaResponse.model_validate(config) if config else None,
    )


@router.get("/salones", response_model=List[SalonResumen])
async def listar_mis_salones(profesor: CurrentTeacher, db: DBSession):
    """Salones del profesor: los del año en curso primero y luego el historial (solo lectura)."""
    school = SchoolService(db)
    return [await _resumen(school, al) for al in await school.anios_del_profesor(profesor.id)]


@router.post("/salones", response_model=SalonDetalle, status_code=status.HTTP_201_CREATED)
async def abrir_salon(data: SalonCreate, profesor: CurrentTeacher, db: DBSession):
    """
    Crea el salón en la organización del profesor (o reutiliza el existente con ese nombre)
    y abre su año lectivo actual con este profesor.
    """
    school = SchoolService(db)
    al = await school.abrir_salon(profesor, data.nombre, data.grado)
    await db.commit()
    return await _detalle(db, school, al)


@router.get("/salones/{anio_lectivo_id}", response_model=SalonDetalle)
async def detalle_salon(anio_lectivo_id: int, profesor: CurrentTeacher, db: DBSession):
    school = SchoolService(db)
    al = await school.anio_del_profesor(anio_lectivo_id, profesor.id)
    detalle = await _detalle(db, school, al)
    await db.commit()  # por si se crearon los trimestres por defecto
    return detalle


@router.get("/salones/{anio_lectivo_id}/candidatos", response_model=List[CandidatoSalon])
async def candidatos_salon(
    anio_lectivo_id: int,
    profesor: CurrentTeacher,
    db: DBSession,
    q: Optional[str] = Query(None, description="Filtrar por nombre o código"),
):
    """Estudiantes de la organización, indicando si ya están en algún salón activo."""
    return await SchoolService(db).candidatos(anio_lectivo_id, profesor.id, q)


@router.post("/salones/{anio_lectivo_id}/estudiantes/bulk", response_model=BulkMatriculaResult)
async def asignar_estudiantes_por_codigo(
    anio_lectivo_id: int, data: BulkMatriculaRequest, profesor: CurrentTeacher, db: DBSession
):
    """Asigna varios estudiantes por código. Sigue aunque alguna fila falle."""
    school = SchoolService(db)
    al = await school.anio_del_profesor(anio_lectivo_id, profesor.id, para_escribir=True)
    organizacion_id = al.salon.organizacion_id
    errores: List[BulkMatriculaError] = []
    agregados = 0
    for fila, codigo in enumerate(data.codigos, start=1):
        codigo = codigo.strip().upper()
        if not codigo:
            errores.append(BulkMatriculaError(fila=fila, codigo=codigo, mensaje="Código vacío"))
            continue
        estudiante_id = (await db.execute(
            select(Estudiante.id).where(and_(
                Estudiante.codigo_estudiante == codigo, Estudiante.organizacion_id == organizacion_id
            ))
        )).scalar_one_or_none()
        if estudiante_id is None:
            errores.append(BulkMatriculaError(fila=fila, codigo=codigo, mensaje="Estudiante no encontrado en tu organización"))
            continue
        try:
            await school.matricular(anio_lectivo_id, estudiante_id, profesor)
            await db.commit()
            agregados += 1
        except ErrorSalon as e:
            errores.append(BulkMatriculaError(fila=fila, codigo=codigo, mensaje=e.mensaje))
    return BulkMatriculaResult(total=len(data.codigos), agregados=agregados, errores=errores)


@router.post("/salones/{anio_lectivo_id}/estudiantes/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def asignar_estudiante(anio_lectivo_id: int, estudiante_id: int, profesor: CurrentTeacher, db: DBSession):
    """Asigna el estudiante al salón. Si ya está en otro salón activo, responde 409."""
    await SchoolService(db).matricular(anio_lectivo_id, estudiante_id, profesor)
    await db.commit()


@router.delete("/salones/{anio_lectivo_id}/estudiantes/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def quitar_estudiante(anio_lectivo_id: int, estudiante_id: int, profesor: CurrentTeacher, db: DBSession):
    """Quita al estudiante del salón y de sus grupos. Queda sin salón hasta que lo asignen."""
    await SchoolService(db).retirar(anio_lectivo_id, estudiante_id, profesor.id)
    await db.commit()


@router.post("/salones/{anio_lectivo_id}/grupos", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def crear_grupo(anio_lectivo_id: int, data: GrupoCreate, profesor: CurrentTeacher, db: DBSession):
    """Crea un grupo (subconjunto opcional de estudiantes) dentro del salón."""
    return await TeacherService(db).crear_grupo(profesor.id, anio_lectivo_id, data)


@router.get("/salones/{anio_lectivo_id}/configuration", response_model=ConfiguracionPracticaResponse)
async def obtener_configuracion(anio_lectivo_id: int, profesor: CurrentTeacher, db: DBSession):
    """Configuración de práctica activa del salón."""
    config = await TeacherService(db).get_configuracion_activa(anio_lectivo_id, profesor.id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return config

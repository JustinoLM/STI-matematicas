"""
Router del módulo de Regla de Tres.

Endpoints:
- POST /regla-de-tres/practice/start           Inicia práctica adaptativa (estudiante)
- POST /regla-de-tres/practice/{id}/submit     Envía respuesta a un problema (estudiante)
- GET  /regla-de-tres/teacher/notas            Notas de los estudiantes del profesor
- GET  /regla-de-tres/admin/notas              Notas de todos los estudiantes (admin)
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import (
    CurrentStudent,
    CurrentStudentConSalon,
    CurrentTeacher,
    DBSession,
    ReglaDeTresServiceDep,
)
from app.models.user import Estudiante
from app.schemas.regla_de_tres import (
    NotasReglaTresResponse,
    SesionReglaTresStartResponse,
    SubmitRespuestaR3Request,
    SubmitRespuestaR3Response,
)
from app.services.school_service import SchoolService

router = APIRouter()


@router.post("/practice/start", response_model=SesionReglaTresStartResponse)
async def iniciar_practica(
    current_student: CurrentStudentConSalon,
    regla_service: ReglaDeTresServiceDep,
):
    return await regla_service.iniciar_practica(estudiante_id=current_student.id)


@router.post("/practice/{sesion_id}/submit", response_model=SubmitRespuestaR3Response)
async def enviar_respuesta(
    sesion_id: int,
    request: SubmitRespuestaR3Request,
    current_student: CurrentStudent,
    regla_service: ReglaDeTresServiceDep,
):
    return await regla_service.enviar_respuesta(
        sesion_id=sesion_id,
        estudiante_id=current_student.id,
        problema_id=request.problema_id,
        respuesta=request.respuesta,
    )


@router.get("/teacher/notas", response_model=NotasReglaTresResponse)
async def obtener_notas_profesor(
    current_teacher: CurrentTeacher,
    regla_service: ReglaDeTresServiceDep,
    db: DBSession,
):
    """Notas de regla de tres de los estudiantes de los salones activos del profesor."""
    estudiante_ids = await SchoolService(db).ids_estudiantes_del_profesor(current_teacher.id)
    return await regla_service.obtener_notas(estudiante_ids)


@router.get("/admin/notas", response_model=NotasReglaTresResponse)
async def obtener_notas_admin(
    regla_service: ReglaDeTresServiceDep,
    db: DBSession,
):
    """Notas de regla de tres de todos los estudiantes (panel de administración)."""
    result = await db.execute(select(Estudiante.id))
    estudiante_ids = [row[0] for row in result.all()]
    return await regla_service.obtener_notas(estudiante_ids)

"""
Router de desafíos grupales para estudiantes.

Expone los desafíos de los equipos del estudiante autenticado en su salón activo
(sus grupos o el salón completo),
calculando el progreso en tiempo real desde SesionPractica (misma
lógica que el panel del profesor para garantizar consistencia).
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentStudent
from app.core.database import get_db
from app.models.adaptive import EstadoSesion, SesionPractica
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.group import Grupo
from app.models.user import Estudiante
from app.schemas.challenge import ContribuidorInfo, DesafioEstudianteResponse
from app.services.desafios_service import (
    NOMBRE_EQUIPO_SALON,
    calcular_progreso,
    condicion_equipos_del_estudiante,
    miembros_equipo,
)

router = APIRouter()

# Mínimo de sesiones completadas en la ventana del desafío para calificar a la recompensa
MIN_SESIONES_PARA_RECOMPENSA = 3


async def _sesiones_en_ventana(
    db: AsyncSession,
    desafio: DesafioGrupal,
    estudiante_id: int,
) -> int:
    """Cuenta cuántas sesiones completó un estudiante específico dentro de la ventana
    del desafío. Se usa para determinar si califica para la recompensa."""
    condiciones = [
        SesionPractica.estudiante_id == estudiante_id,
        SesionPractica.estado == EstadoSesion.COMPLETADA,
        SesionPractica.fecha_fin >= desafio.fecha_creacion,
    ]
    if desafio.fecha_limite:
        condiciones.append(SesionPractica.fecha_fin <= desafio.fecha_limite)

    result = await db.execute(
        select(func.count(SesionPractica.id)).where(and_(*condiciones))
    )
    return int(result.scalar() or 0)


async def _top_contribuidores(
    db: AsyncSession,
    desafio: DesafioGrupal,
    miembros_ids: List[int],
    limit: int = 5,
) -> List[ContribuidorInfo]:
    """Devuelve los N estudiantes del grupo que más sesiones completaron
    dentro de la ventana del desafío, ordenados de mayor a menor."""
    if not miembros_ids:
        return []

    condiciones = [
        SesionPractica.estudiante_id.in_(miembros_ids),
        SesionPractica.estado == EstadoSesion.COMPLETADA,
        SesionPractica.fecha_fin >= desafio.fecha_creacion,
    ]
    if desafio.fecha_limite:
        condiciones.append(SesionPractica.fecha_fin <= desafio.fecha_limite)

    result = await db.execute(
        select(
            Estudiante.nombre_completo,
            func.count(SesionPractica.id).label("sesiones"),
        )
        .join(Estudiante, Estudiante.id == SesionPractica.estudiante_id)
        .where(and_(*condiciones))
        .group_by(SesionPractica.estudiante_id, Estudiante.nombre_completo)
        .order_by(func.count(SesionPractica.id).desc())
        .limit(limit)
    )
    return [ContribuidorInfo(nombre=row[0], sesiones=row[1]) for row in result.all()]


@router.get("/mis-desafios", response_model=List[DesafioEstudianteResponse])
async def mis_desafios(
    current_student: CurrentStudent,
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve los desafíos grupales activos (no eliminados) asignados
    al grupo del estudiante autenticado, junto con el progreso real del grupo,
    la participación individual y el ranking de contribuidores.
    """

    # 1. Desafíos de los equipos del estudiante en su salón activo (grupos o salón completo)
    desafios_result = await db.execute(
        select(DesafioGrupal, GrupoDesafio)
        .join(GrupoDesafio, GrupoDesafio.desafio_id == DesafioGrupal.id)
        .where(
            and_(
                condicion_equipos_del_estudiante(current_student.id, solo_matricula_activa=True),
                DesafioGrupal.eliminado == False,  # noqa: E712
            )
        )
        .order_by(DesafioGrupal.fecha_creacion.desc())
    )
    rows = desafios_result.all()

    if not rows:
        return []

    ahora = datetime.utcnow()
    resultado: List[DesafioEstudianteResponse] = []

    for desafio, grupo_desafio in rows:
        # 2. Equipo: un grupo del salón o el salón completo
        if grupo_desafio.grupo_id is None:
            grupo_nombre = NOMBRE_EQUIPO_SALON
        else:
            grupo_nombre = (await db.execute(
                select(Grupo.nombre).where(Grupo.id == grupo_desafio.grupo_id)
            )).scalar_one()
        miembros_ids = await miembros_equipo(db, desafio, grupo_desafio.grupo_id)

        # 3. Progreso del equipo en tiempo real
        progreso = await calcular_progreso(db, desafio, miembros_ids)

        # 4. Porcentaje acotado a 100
        porcentaje = (
            round(min((progreso / desafio.objetivo_cantidad) * 100, 100), 2)
            if desafio.objetivo_cantidad > 0
            else 0.0
        )
        grupo_completado = progreso >= desafio.objetivo_cantidad

        # 5. Fecha límite
        dias_restantes: int | None = None
        esta_expirado = False
        if desafio.fecha_limite:
            delta = desafio.fecha_limite - ahora
            dias_restantes = delta.days
            esta_expirado = delta.total_seconds() < 0

        # 6. Participación individual del estudiante
        mi_sesiones = await _sesiones_en_ventana(db, desafio, current_student.id)
        califica = mi_sesiones >= MIN_SESIONES_PARA_RECOMPENSA
        faltan = max(0, MIN_SESIONES_PARA_RECOMPENSA - mi_sesiones)

        # 7. Top contribuidores del equipo
        top = await _top_contribuidores(db, desafio, miembros_ids)

        resultado.append(
            DesafioEstudianteResponse(
                id=desafio.id,
                nombre=desafio.nombre,
                descripcion=desafio.descripcion,
                tipo=desafio.tipo,
                objetivo_cantidad=desafio.objetivo_cantidad,
                parametro_adicional=desafio.parametro_adicional,
                recompensa_texto=desafio.recompensa_texto,
                recompensa_puntos=desafio.recompensa_puntos,
                fecha_creacion=desafio.fecha_creacion,
                fecha_limite=desafio.fecha_limite,
                completado=desafio.completado or grupo_completado,
                grupo_id=grupo_desafio.grupo_id,
                grupo_nombre=grupo_nombre,
                progreso_actual=progreso,
                porcentaje=porcentaje,
                grupo_completado=grupo_completado,
                dias_restantes=dias_restantes,
                esta_expirado=esta_expirado,
                # Participación individual
                mi_sesiones_en_ventana=mi_sesiones,
                califica_recompensa=califica,
                sesiones_para_calificar=faltan,
                # Top contribuidores
                top_contribuidores=top,
            )
        )

    return resultado

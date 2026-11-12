"""
Utilidades compartidas de los desafíos grupales.

Un desafío pertenece a un año lectivo de un salón y tiene uno o más equipos (GrupoDesafio):
un grupo del salón o, si grupo_id es NULL, el salón completo. El progreso se calcula siempre
desde SesionPractica, igual para el panel del profesor y para el del estudiante.
"""

from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import EstadoSesion, SesionPractica
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.group import EstudianteGrupo
from app.models.school import MATRICULA_ACTIVA, MATRICULA_CERRADA, Matricula

NOMBRE_EQUIPO_SALON = "Todo el salón"


async def miembros_equipo(db: AsyncSession, desafio: DesafioGrupal, grupo_id: Optional[int]) -> list[int]:
    """
    Estudiantes del equipo: los miembros activos del grupo o, para el salón completo, los
    matriculados en el año lectivo del desafío (activos o que cerraron el año en él).
    """
    if grupo_id is not None:
        result = await db.execute(
            select(EstudianteGrupo.estudiante_id).where(and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.activo == True,  # noqa: E712
            ))
        )
    else:
        result = await db.execute(
            select(Matricula.estudiante_id).where(and_(
                Matricula.anio_lectivo_id == desafio.anio_lectivo_id,
                Matricula.estado.in_([MATRICULA_ACTIVA, MATRICULA_CERRADA]),
            ))
        )
    return [row[0] for row in result.all()]


def condiciones_ventana(desafio: DesafioGrupal) -> list:
    """Sesiones completadas dentro de la ventana del desafío [creación, fecha límite]."""
    condiciones = [
        SesionPractica.estado == EstadoSesion.COMPLETADA,
        SesionPractica.fecha_fin >= desafio.fecha_creacion,
    ]
    if desafio.fecha_limite:
        condiciones.append(SesionPractica.fecha_fin <= desafio.fecha_limite)
    return condiciones


async def calcular_progreso(db: AsyncSession, desafio: DesafioGrupal, miembros_ids: list[int]) -> int:
    """
    Progreso real del equipo en el desafío, desde SesionPractica.

    Tipos soportados (de más fácil a más difícil):
    - problemas_resueltos    → SUM(problemas_correctos)
    - sesiones_completadas   → COUNT(sesiones)
    - practicas_sin_errores  → COUNT(sesiones donde incorrectos <= parametro_adicional)
    - problemas_rapidos      → SUM(correctos) de sesiones donde velocidad_promedio <= parametro_adicional seg
    - practicas_rapidas      → COUNT(sesiones donde tiempo_total <= parametro_adicional * 60 seg)
    """
    if not miembros_ids:
        return 0

    base_where = and_(SesionPractica.estudiante_id.in_(miembros_ids), *condiciones_ventana(desafio))

    if desafio.tipo == "problemas_resueltos":
        result = await db.execute(
            select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0))
            .where(and_(base_where, SesionPractica.problemas_correctos.isnot(None)))
        )
        return int(result.scalar() or 0)

    if desafio.tipo == "sesiones_completadas":
        result = await db.execute(select(func.count(SesionPractica.id)).where(base_where))
        return int(result.scalar() or 0)

    if desafio.tipo == "practicas_sin_errores":
        max_errores = desafio.parametro_adicional or 0
        result = await db.execute(
            select(func.count(SesionPractica.id)).where(and_(
                base_where,
                SesionPractica.problemas_incorrectos.isnot(None),
                SesionPractica.problemas_incorrectos <= max_errores,
            ))
        )
        return int(result.scalar() or 0)

    if desafio.tipo == "problemas_rapidos":
        max_seg = desafio.parametro_adicional or 999
        result = await db.execute(
            select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0)).where(and_(
                base_where,
                SesionPractica.velocidad_promedio.isnot(None),
                SesionPractica.velocidad_promedio <= max_seg,
                SesionPractica.problemas_correctos.isnot(None),
            ))
        )
        return int(result.scalar() or 0)

    if desafio.tipo == "practicas_rapidas":
        max_seg_total = (desafio.parametro_adicional or 999) * 60
        result = await db.execute(
            select(func.count(SesionPractica.id)).where(and_(
                base_where,
                SesionPractica.tiempo_total_segundos.isnot(None),
                SesionPractica.tiempo_total_segundos <= max_seg_total,
            ))
        )
        return int(result.scalar() or 0)

    return 0


def condicion_equipos_del_estudiante(estudiante_id: int, solo_matricula_activa: bool):
    """
    Condición sobre (GrupoDesafio, DesafioGrupal) para los equipos a los que pertenece el
    estudiante: sus grupos activos o el salón completo de su matrícula.

    Con solo_matricula_activa=False también cuenta el historial (años ya cerrados).
    """
    if solo_matricula_activa:
        estados = [MATRICULA_ACTIVA]
    else:
        estados = [MATRICULA_ACTIVA, MATRICULA_CERRADA]
    grupos = select(EstudianteGrupo.grupo_id).where(and_(
        EstudianteGrupo.estudiante_id == estudiante_id,
        EstudianteGrupo.activo == True,  # noqa: E712
    ))
    anios = select(Matricula.anio_lectivo_id).where(and_(
        Matricula.estudiante_id == estudiante_id,
        Matricula.estado.in_(estados),
    ))
    return and_(
        DesafioGrupal.anio_lectivo_id.in_(anios),
        or_(
            GrupoDesafio.grupo_id.in_(grupos),
            GrupoDesafio.grupo_id.is_(None),
        ),
    )

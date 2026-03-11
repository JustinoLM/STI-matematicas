"""
Router de desafíos grupales para estudiantes.

Expone los desafíos asignados al grupo del estudiante autenticado,
calculando el progreso en tiempo real desde SesionPractica (misma
lógica que el panel del profesor para garantizar consistencia).
"""

from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.api.dependencies import CurrentStudent
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.group import EstudianteGrupo, Grupo
from app.models.adaptive import SesionPractica, EstadoSesion, PerfilEstudiante
from app.models.user import Estudiante
from app.schemas.challenge import DesafioEstudianteResponse, ContribuidorInfo

router = APIRouter()

# Mínimo de sesiones completadas en la ventana del desafío para calificar a la recompensa
MIN_SESIONES_PARA_RECOMPENSA = 3


async def _calcular_progreso_estudiante(
    db: AsyncSession,
    desafio: DesafioGrupal,
    grupo_id: int,
) -> int:
    """
    Calcula el progreso real del grupo en un desafío consultando SesionPractica.

    Ventana de tiempo: [fecha_creacion, fecha_limite] (idéntica a teacher_service).
    Si no hay fecha_limite, se cuentan todas las sesiones desde la creación.

    Tipos soportados:
    - problemas_resueltos   → SUMA de problemas_correctos
    - sesiones_completadas  → COUNT de sesiones completadas
    - practicas_sin_errores → COUNT de sesiones con ≤ Y incorrectos
    - problemas_rapidos     → SUMA de correctos en sesiones con velocidad ≤ Y
    - practicas_rapidas     → COUNT de sesiones en ≤ Y minutos
    """
    # Estudiantes activos del grupo
    result = await db.execute(
        select(EstudianteGrupo.estudiante_id).where(
            and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.activo == True,
            )
        )
    )
    estudiantes_ids = [row[0] for row in result.all()]

    if not estudiantes_ids:
        return 0

    # ── Condiciones base de ventana temporal (igual que teacher_service) ──
    condiciones = [
        SesionPractica.estudiante_id.in_(estudiantes_ids),
        SesionPractica.estado == EstadoSesion.COMPLETADA,
        SesionPractica.fecha_fin >= desafio.fecha_creacion,  # solo desde creación
    ]
    # Cap al vencimiento: sesiones después del límite no cuentan
    if desafio.fecha_limite:
        condiciones.append(SesionPractica.fecha_fin <= desafio.fecha_limite)

    base_where = and_(*condiciones)

    # ── 1. Resolver X problemas ──────────────────────────────────────────
    if desafio.tipo == "problemas_resueltos":
        result = await db.execute(
            select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0))
            .where(and_(base_where, SesionPractica.problemas_correctos.isnot(None)))
        )
        return int(result.scalar() or 0)

    # ── 2. Resolver X prácticas ──────────────────────────────────────────
    elif desafio.tipo == "sesiones_completadas":
        result = await db.execute(
            select(func.count(SesionPractica.id)).where(base_where)
        )
        return int(result.scalar() or 0)

    # ── 3. Resolver X prácticas con máximo Y errores ─────────────────────
    elif desafio.tipo == "practicas_sin_errores":
        max_errores = desafio.parametro_adicional or 0
        result = await db.execute(
            select(func.count(SesionPractica.id))
            .where(and_(
                base_where,
                SesionPractica.problemas_incorrectos.isnot(None),
                SesionPractica.problemas_incorrectos <= max_errores,
            ))
        )
        return int(result.scalar() or 0)

    # ── 4. Resolver X problemas en Y o menos segundos/problema ───────────
    elif desafio.tipo == "problemas_rapidos":
        max_seg = desafio.parametro_adicional or 999
        result = await db.execute(
            select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0))
            .where(and_(
                base_where,
                SesionPractica.velocidad_promedio.isnot(None),
                SesionPractica.velocidad_promedio <= max_seg,
                SesionPractica.problemas_correctos.isnot(None),
            ))
        )
        return int(result.scalar() or 0)

    # ── 5. Resolver X prácticas en Y o menos minutos ─────────────────────
    elif desafio.tipo == "practicas_rapidas":
        max_min = desafio.parametro_adicional or 999
        max_seg_total = max_min * 60
        result = await db.execute(
            select(func.count(SesionPractica.id))
            .where(and_(
                base_where,
                SesionPractica.tiempo_total_segundos.isnot(None),
                SesionPractica.tiempo_total_segundos <= max_seg_total,
            ))
        )
        return int(result.scalar() or 0)

    # Tipo desconocido: devolver 0
    return 0


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

    # 1. Grupos activos del estudiante
    grupos_result = await db.execute(
        select(EstudianteGrupo.grupo_id).where(
            and_(
                EstudianteGrupo.estudiante_id == current_student.id,
                EstudianteGrupo.activo == True,
            )
        )
    )
    grupo_ids = [row[0] for row in grupos_result.fetchall()]

    if not grupo_ids:
        return []

    # 2. Desafíos grupales asignados a esos grupos (no eliminados)
    desafios_result = await db.execute(
        select(DesafioGrupal, GrupoDesafio, Grupo)
        .join(GrupoDesafio, GrupoDesafio.desafio_id == DesafioGrupal.id)
        .join(Grupo, Grupo.id == GrupoDesafio.grupo_id)
        .where(
            and_(
                GrupoDesafio.grupo_id.in_(grupo_ids),
                DesafioGrupal.eliminado == False,
            )
        )
        .order_by(DesafioGrupal.fecha_creacion.desc())
    )
    rows = desafios_result.all()

    if not rows:
        return []

    ahora = datetime.utcnow()
    resultado: List[DesafioEstudianteResponse] = []

    for desafio, grupo_desafio, grupo in rows:
        # 3. Progreso del grupo en tiempo real
        progreso = await _calcular_progreso_estudiante(db, desafio, grupo.id)

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

        # 7. Top contribuidores del grupo
        miembros_result = await db.execute(
            select(EstudianteGrupo.estudiante_id).where(
                and_(
                    EstudianteGrupo.grupo_id == grupo.id,
                    EstudianteGrupo.activo == True,
                )
            )
        )
        miembros_ids = [row[0] for row in miembros_result.all()]
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
                grupo_id=grupo.id,
                grupo_nombre=grupo.nombre,
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

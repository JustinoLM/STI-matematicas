"""
Carga del grafo de prerrequisitos: el del currículo, o el del año lectivo cuando el profesor editó
alguna lección (ver app/nucleo/prerrequisitos.py).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculo import LeccionCurricular, PrerrequisitoDefecto
from app.models.nucleo import NucleoPrerrequisitoAnio, NucleoPrerrequisitoEditado
from app.nucleo.prerrequisitos import combinar
from app.nucleo.reparto import Grafo


async def prerrequisitos_defecto(db: AsyncSession) -> dict[str, list[str]]:
    resultado: dict[str, list[str]] = {}
    for lec, pre in (await db.execute(
        select(PrerrequisitoDefecto.leccion_id, PrerrequisitoDefecto.prerrequisito_id)
    )).tuples():
        resultado.setdefault(lec, []).append(pre)
    return resultado


async def ediciones_del_anio(db: AsyncSession, anio_lectivo_id: int) -> tuple[set[str], dict[str, list[str]]]:
    """(lecciones editadas, sus prerrequisitos en el año)."""
    editadas = set((await db.execute(
        select(NucleoPrerrequisitoEditado.leccion_id)
        .where(NucleoPrerrequisitoEditado.anio_lectivo_id == anio_lectivo_id)
    )).scalars())
    del_anio: dict[str, list[str]] = {}
    for lec, pre in (await db.execute(
        select(NucleoPrerrequisitoAnio.leccion_id, NucleoPrerrequisitoAnio.prerrequisito_id)
        .where(NucleoPrerrequisitoAnio.anio_lectivo_id == anio_lectivo_id)
    )).tuples():
        del_anio.setdefault(lec, []).append(pre)
    return editadas, del_anio


async def prerrequisitos_efectivos(db: AsyncSession, anio_lectivo_id: Optional[int]) -> dict[str, tuple[str, ...]]:
    defecto = await prerrequisitos_defecto(db)
    if anio_lectivo_id is None:
        return {k: tuple(v) for k, v in defecto.items()}
    editadas, del_anio = await ediciones_del_anio(db, anio_lectivo_id)
    return combinar(defecto, editadas, del_anio)


async def cargar_grafo(db: AsyncSession, anio_lectivo_id: Optional[int] = None) -> Grafo:
    """Grafo para el reparto, la extensión y el refuerzo. Sin año lectivo, el del currículo."""
    orden = {
        lec: n for lec, n in (await db.execute(
            select(LeccionCurricular.id, LeccionCurricular.orden_programa)
        )).tuples()
    }
    return Grafo(await prerrequisitos_efectivos(db, anio_lectivo_id), orden)

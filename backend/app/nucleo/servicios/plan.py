"""
Plan por trimestre (fase 6b, opcional): el profesor indica en qué trimestres se habilita cada
lección y el sistema la habilita o deshabilita según la fecha.

- Una lección del plan está habilitada si el trimestre vigente (el último que empezó, según las
  fechas de la organización) está entre los suyos. Antes del T1 el plan no hace nada.
- Si el profesor la habilita o deshabilita a mano (ajuste_manual), el plan ya no la toca hasta que
  la devuelva al plan.
- Aplicar es idempotente y barato (solo mira las lecciones del plan), así que no hace falta una
  tarea programada: se aplica al abrir las pantallas del salón, cuando el estudiante entra a
  practicar y al guardar el plan.
"""

from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.tiempo import ahora_utc
from app.models.nucleo import NucleoHabilitacion, NucleoPlanTrimestre
from app.models.school import ANIO_ACTIVO, AnioLectivo
from app.nucleo.dominio import fecha_local
from app.nucleo.modos import Modo
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.seguimiento import Periodo, cambios_del_plan, trimestre_vigente
from app.nucleo.servicios.habilitacion import PISTAS_POR_DEFECTO, ServicioHabilitacion
from app.services.school_service import Conflicto, SchoolService


class ServicioPlan:
    def __init__(self, db: AsyncSession, parametros: Optional[ParametrosNucleo] = None,
                 reloj: Callable[[], datetime] = ahora_utc):
        self.db = db
        self.school = SchoolService(db)
        self._parametros = parametros
        self.reloj = reloj

    async def parametros(self) -> ParametrosNucleo:
        if self._parametros is None:
            self._parametros = await cargar_parametros(self.db)
        return self._parametros

    async def periodos(self, anio: AnioLectivo) -> list[Periodo]:
        if anio.salon is None:
            await self.db.refresh(anio, ["salon"])
        ts = await self.school.trimestres(anio.salon.organizacion_id, anio.anio)
        return [Periodo(t.numero, t.fecha_inicio, t.fecha_fin) for t in ts]

    async def vigente(self, anio: AnioLectivo) -> Optional[int]:
        hoy = fecha_local(self.reloj())
        return trimestre_vigente(await self.periodos(anio), hoy)

    async def plan(self, anio_lectivo_id: int) -> dict[str, set[int]]:
        plan: dict[str, set[int]] = {}
        for lec, t in (await self.db.execute(
            select(NucleoPlanTrimestre.leccion_id, NucleoPlanTrimestre.trimestre)
            .where(NucleoPlanTrimestre.anio_lectivo_id == anio_lectivo_id)
        )).tuples():
            plan.setdefault(lec, set()).add(t)
        return plan

    async def aplicar(self, anio_lectivo_id: int) -> list[tuple[str, bool]]:
        """Habilita y deshabilita según el trimestre vigente. Devuelve los cambios hechos."""
        plan = await self.plan(anio_lectivo_id)
        if not plan:
            return []
        anio = (await self.db.execute(
            select(AnioLectivo).where(AnioLectivo.id == anio_lectivo_id).options(selectinload(AnioLectivo.salon))
        )).scalar_one()
        if anio.estado != ANIO_ACTIVO:
            return []
        habs = {
            h.leccion_id: h for h in (await self.db.execute(
                select(NucleoHabilitacion).where(and_(
                    NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                    NucleoHabilitacion.leccion_id.in_(plan),
                ))
            )).scalars()
        }
        cambios = cambios_del_plan(
            plan, {lec: (h.habilitada, h.ajuste_manual) for lec, h in habs.items()}, await self.vigente(anio)
        )
        ahora = self.reloj()
        for lec, habilitar in cambios:
            h = habs.get(lec)
            if h is None:
                h = NucleoHabilitacion(
                    anio_lectivo_id=anio_lectivo_id, leccion_id=lec, signo=Modo.SIEMPRE.value,
                    iconos=Modo.SIEMPRE.value, pistas=dict(PISTAS_POR_DEFECTO), prioritaria=False,
                    profesor_id=anio.profesor_id, ajuste_manual=False,
                )
                self.db.add(h)
            h.habilitada = habilitar
            if not habilitar:
                h.prioritaria = False
            h.fecha_actualizacion = ahora
        if cambios:
            await self.db.flush()
        return cambios

    async def resumen(self, anio_lectivo_id: int, profesor_id: int) -> dict:
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await self.aplicar(anio_lectivo_id)
        periodos = await self.periodos(anio)
        return {
            "trimestres": [{"numero": t.numero, "inicio": t.inicio, "fin": t.fin} for t in periodos],
            "vigente": trimestre_vigente(periodos, fecha_local(self.reloj())),
            "plan": {lec: sorted(ts) for lec, ts in sorted((await self.plan(anio_lectivo_id)).items())},
        }

    async def guardar(self, anio_lectivo_id: int, profesor_id: int, plan: dict[str, list[int]]) -> dict:
        """Reemplaza el plan del año. Las lecciones deben estar incluidas en el STI."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        hab = ServicioHabilitacion(self.db)
        for lec, trimestres in plan.items():
            await hab._leccion_incluida(lec)
            if any(t not in (1, 2, 3) for t in trimestres):
                raise Conflicto("Los trimestres van del 1 al 3.")
        await self.db.execute(delete(NucleoPlanTrimestre).where(NucleoPlanTrimestre.anio_lectivo_id == anio_lectivo_id))
        for lec, trimestres in plan.items():
            for t in sorted(set(trimestres)):
                self.db.add(NucleoPlanTrimestre(anio_lectivo_id=anio_lectivo_id, leccion_id=lec, trimestre=t))
        await self.db.flush()
        return await self.resumen(anio_lectivo_id, profesor_id)

    async def devolver_al_plan(self, anio_lectivo_id: int, profesor_id: int, leccion_id: str) -> dict:
        """Quita el ajuste manual de la lección y aplica el plan."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        h = (await self.db.execute(select(NucleoHabilitacion).where(and_(
            NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id, NucleoHabilitacion.leccion_id == leccion_id,
        )))).scalar_one_or_none()
        if h is not None and h.ajuste_manual:
            h.ajuste_manual = False
            await self.db.flush()
        return await self.resumen(anio_lectivo_id, profesor_id)

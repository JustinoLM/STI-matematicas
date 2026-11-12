"""
Lo que configura el profesor en el núcleo (la interfaz es de la fase 6):

- habilitar, configurar y deshabilitar lecciones en el año lectivo de su salón;
- asignar una lección a un solo estudiante (se cierra sola al dominarla) o cancelar la asignación;
- forzar el banco de respuestas a un estudiante.

Un año lectivo cerrado es de solo lectura (AnioCerrado, 409).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculo import LeccionCurricular
from app.models.nucleo import (
    ASIGNACION_ACTIVA,
    ASIGNACION_CANCELADA,
    DOMINIO_DOMINADO,
    NucleoAjusteEstudiante,
    NucleoAsignacion,
    NucleoDominio,
    NucleoHabilitacion,
)
from app.models.school import MATRICULA_ACTIVA, AnioLectivo, Matricula
from app.nucleo.modos import Modo
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.services.school_service import Conflicto, NoEncontrado, SchoolService

PISTAS_POR_DEFECTO = {"1": True, "2": True, "3": True}


def normalizar_pistas(pistas: Optional[dict]) -> dict:
    """{"1": bool, "2": bool, "3": bool}; lo que falte queda habilitado."""
    pistas = pistas or {}
    return {n: bool(pistas.get(n, pistas.get(int(n), True))) for n in PISTAS_POR_DEFECTO}


class ServicioHabilitacion:
    def __init__(self, db: AsyncSession, parametros: Optional[ParametrosNucleo] = None):
        self.db = db
        self.school = SchoolService(db)
        self._parametros = parametros

    async def parametros(self) -> ParametrosNucleo:
        if self._parametros is None:
            self._parametros = await cargar_parametros(self.db)
        return self._parametros

    async def _leccion_incluida(self, leccion_id: str) -> LeccionCurricular:
        leccion = await self.db.get(LeccionCurricular, leccion_id)
        if leccion is None:
            raise NoEncontrado(f"La lección {leccion_id} no existe.")
        if not leccion.incluida:
            raise Conflicto(f"La lección {leccion_id} no está incluida en el STI.")
        return leccion

    async def _matricula(self, anio: AnioLectivo, estudiante_id: int, solo_activa: bool = True) -> Matricula:
        condiciones = [Matricula.anio_lectivo_id == anio.id, Matricula.estudiante_id == estudiante_id]
        if solo_activa:
            condiciones.append(Matricula.estado == MATRICULA_ACTIVA)
        m = (await self.db.execute(select(Matricula).where(and_(*condiciones)))).scalar_one_or_none()
        if m is None:
            raise NoEncontrado("El estudiante no está en este salón.")
        return m

    # ── Habilitación ────────────────────────────────────────────────────────

    async def listar(self, anio_lectivo_id: int, profesor_id: int) -> list[tuple[NucleoHabilitacion, LeccionCurricular]]:
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        filas = await self.db.execute(
            select(NucleoHabilitacion, LeccionCurricular)
            .join(LeccionCurricular, LeccionCurricular.id == NucleoHabilitacion.leccion_id)
            .where(NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id)
            .order_by(LeccionCurricular.orden_programa)
        )
        return list(filas.tuples())

    async def habilitar(
        self,
        anio_lectivo_id: int,
        profesor_id: int,
        leccion_id: str,
        *,
        signo: Modo = Modo.SIEMPRE,
        iconos: Modo = Modo.SIEMPRE,
        pistas: Optional[dict] = None,
        prioritaria: bool = False,
    ) -> NucleoHabilitacion:
        """Habilita la lección o actualiza su configuración (idempotente)."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        await self._leccion_incluida(leccion_id)
        hab = (await self.db.execute(
            select(NucleoHabilitacion).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                NucleoHabilitacion.leccion_id == leccion_id,
            ))
        )).scalar_one_or_none()

        if prioritaria and not (hab and hab.habilitada and hab.prioritaria):
            otras = await self.db.scalar(
                select(func.count()).select_from(NucleoHabilitacion).where(and_(
                    NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                    NucleoHabilitacion.prioritaria.is_(True),
                    NucleoHabilitacion.leccion_id != leccion_id,
                ))
            )
            maximo = (await self.parametros()).max_prioritarias
            if otras >= maximo:
                raise Conflicto(f"Ya hay {maximo} lecciones prioritarias; quita una antes de agregar otra.")

        if hab is None:
            hab = NucleoHabilitacion(anio_lectivo_id=anio_lectivo_id, leccion_id=leccion_id)
            self.db.add(hab)
        hab.habilitada = True
        hab.signo = Modo(signo).value
        hab.iconos = Modo(iconos).value
        hab.pistas = normalizar_pistas(pistas)
        hab.prioritaria = prioritaria
        hab.profesor_id = profesor_id
        hab.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()
        return hab

    async def deshabilitar(self, anio_lectivo_id: int, profesor_id: int, leccion_id: str) -> NucleoHabilitacion:
        """Deshabilita la lección. Conserva la configuración y el dominio de los estudiantes."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        hab = (await self.db.execute(
            select(NucleoHabilitacion).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                NucleoHabilitacion.leccion_id == leccion_id,
            ))
        )).scalar_one_or_none()
        if hab is None:
            raise NoEncontrado("La lección no está habilitada en este salón.")
        hab.habilitada = False
        hab.prioritaria = False
        hab.profesor_id = profesor_id
        hab.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()
        return hab

    # ── Asignación individual ───────────────────────────────────────────────

    async def asignar(
        self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int, leccion_id: str
    ) -> NucleoAsignacion:
        """Asigna la lección solo a ese estudiante. Si ya tiene una activa, la devuelve."""
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        await self._matricula(anio, estudiante_id)
        await self._leccion_incluida(leccion_id)
        dominio = await self.db.get(NucleoDominio, (estudiante_id, leccion_id))
        if dominio is not None and dominio.estado == DOMINIO_DOMINADO:
            raise Conflicto("El estudiante ya domina esta lección.")
        activa = (await self.db.execute(
            select(NucleoAsignacion).where(and_(
                NucleoAsignacion.estudiante_id == estudiante_id,
                NucleoAsignacion.leccion_id == leccion_id,
                NucleoAsignacion.estado == ASIGNACION_ACTIVA,
            ))
        )).scalar_one_or_none()
        if activa is not None:
            return activa
        asig = NucleoAsignacion(
            anio_lectivo_id=anio_lectivo_id, estudiante_id=estudiante_id, leccion_id=leccion_id,
            profesor_id=profesor_id, estado=ASIGNACION_ACTIVA,
        )
        self.db.add(asig)
        await self.db.flush()
        return asig

    async def asignaciones(self, anio_lectivo_id: int, profesor_id: int) -> list[NucleoAsignacion]:
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        filas = await self.db.execute(
            select(NucleoAsignacion)
            .where(NucleoAsignacion.anio_lectivo_id == anio_lectivo_id)
            .order_by(NucleoAsignacion.fecha_asignacion)
        )
        return list(filas.scalars())

    async def cancelar_asignacion(self, asignacion_id: int, profesor_id: int) -> NucleoAsignacion:
        asig = await self.db.get(NucleoAsignacion, asignacion_id)
        if asig is None:
            raise NoEncontrado("Asignación no encontrada.")
        await self.school.anio_del_profesor(asig.anio_lectivo_id, profesor_id, para_escribir=True)
        if asig.estado != ASIGNACION_ACTIVA:
            raise Conflicto("La asignación ya está cerrada.")
        asig.estado = ASIGNACION_CANCELADA
        asig.fecha_cierre = datetime.utcnow()
        await self.db.flush()
        return asig

    # ── Ajustes del estudiante ──────────────────────────────────────────────

    async def ajustar_estudiante(
        self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int, banco_forzado: bool
    ) -> NucleoAjusteEstudiante:
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        await self._matricula(anio, estudiante_id)
        ajuste = await self.db.get(NucleoAjusteEstudiante, estudiante_id)
        if ajuste is None:
            ajuste = NucleoAjusteEstudiante(estudiante_id=estudiante_id)
            self.db.add(ajuste)
        ajuste.banco_forzado = banco_forzado
        ajuste.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()
        return ajuste

    async def exigir_estudiante_del_profesor(self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int) -> None:
        """Para consultar: el estudiante estuvo en ese salón (también en años cerrados)."""
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await self._matricula(anio, estudiante_id, solo_activa=False)


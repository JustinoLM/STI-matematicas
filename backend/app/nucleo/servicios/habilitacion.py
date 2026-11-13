"""
Lo que configura el profesor en el núcleo (pantallas de la fase 6a):

- el catálogo del salón: todas las lecciones con su habilitación y sus prerrequisitos del año;
- habilitar, configurar y deshabilitar lecciones en el año lectivo de su salón (máximo
  `max_prioritarias` prioritarias a la vez);
- editar los prerrequisitos de una lección en ese año, sin formar ciclos, o volver a los del
  currículo;
- asignar una lección a un solo estudiante (se cierra sola al dominarla) o cancelar la asignación;
- forzar el banco de respuestas a un estudiante.

Un año lectivo cerrado es de solo lectura (AnioCerrado, 409).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, delete, func, select
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
    NucleoPrerrequisitoAnio,
    NucleoPrerrequisitoEditado,
)
from app.models.school import MATRICULA_ACTIVA, AnioLectivo, Matricula
from app.models.user import Estudiante
from app.nucleo.modos import Modo
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.prerrequisitos import camino_de_ciclo
from app.nucleo.registro import tiene_generador
from app.nucleo.servicios.grafo import ediciones_del_anio, prerrequisitos_efectivos
from app.services.curriculo_service import listar_lecciones
from app.services.school_service import Conflicto, NoEncontrado, SchoolService

PISTAS_POR_DEFECTO = {"1": True, "2": True, "3": True}


def normalizar_pistas(pistas: Optional[dict]) -> dict:
    """{"1": bool, "2": bool, "3": bool}; lo que falte queda habilitado."""
    pistas = pistas or {}
    return {n: bool(pistas.get(n, pistas.get(int(n), True))) for n in PISTAS_POR_DEFECTO}


class MaxPrioritarias(Conflicto):
    codigo = "MAX_PRIORITARIAS"


class PrerrequisitoInvalido(Conflicto):
    codigo = "PRERREQUISITO_INVALIDO"


class CicloPrerrequisitos(Conflicto):
    codigo = "PRERREQUISITO_CICLO"


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
                raise MaxPrioritarias(
                    f"Ya hay {maximo} lecciones prioritarias; quita la prioridad a una antes de elegir otra."
                )

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

    # ── Catálogo del salón ──────────────────────────────────────────────────

    async def catalogo(self, anio_lectivo_id: int, profesor_id: int) -> list[dict]:
        """Todas las lecciones del programa con su habilitación en el año y sus prerrequisitos
        (los que se aplican, los del currículo y si el profesor los editó)."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        lecciones = await listar_lecciones(self.db)
        orden = {lec["id"]: lec["orden_programa"] for lec in lecciones}
        habilitaciones = {
            h.leccion_id: h for h in (await self.db.execute(
                select(NucleoHabilitacion).where(NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id)
            )).scalars()
        }
        editadas, _ = await ediciones_del_anio(self.db, anio_lectivo_id)
        efectivos = await prerrequisitos_efectivos(self.db, anio_lectivo_id)
        filas = []
        for lec in lecciones:
            h = habilitaciones.get(lec["id"])
            filas.append({
                **lec,
                "prerrequisitos_programa": lec["prerrequisitos"],
                "prerrequisitos": sorted(efectivos.get(lec["id"], ()), key=lambda i: orden.get(i, 0)),
                "prerrequisitos_editados": lec["id"] in editadas,
                "tiene_generador": tiene_generador(lec["id"]),
                "habilitada": bool(h and h.habilitada),
                "signo": h.signo if h else Modo.SIEMPRE.value,
                "iconos": h.iconos if h else Modo.SIEMPRE.value,
                "pistas": normalizar_pistas(h.pistas if h else None),
                "prioritaria": bool(h and h.prioritaria),
            })
        return filas

    # ── Prerrequisitos del año lectivo ──────────────────────────────────────

    async def editar_prerrequisitos(
        self, anio_lectivo_id: int, profesor_id: int, leccion_id: str, prerrequisitos: list[str]
    ) -> list[str]:
        """Reemplaza los prerrequisitos de la lección en este año. Rechaza los que no existen, no
        están incluidos, son la misma lección o forman un ciclo."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        leccion = await self._leccion_incluida(leccion_id)
        nuevos = list(dict.fromkeys(prerrequisitos))
        titulos: dict[str, str] = {leccion.id: leccion.leccion_titulo}
        for pre_id in nuevos:
            if pre_id == leccion_id:
                raise PrerrequisitoInvalido("Una lección no puede ser prerrequisito de sí misma.")
            pre = await self.db.get(LeccionCurricular, pre_id)
            if pre is None or not pre.incluida:
                raise PrerrequisitoInvalido(f"La lección {pre_id} no existe o no está incluida en el STI.")
            titulos[pre.id] = pre.leccion_titulo

        efectivos = await prerrequisitos_efectivos(self.db, anio_lectivo_id)
        camino = camino_de_ciclo(efectivos, leccion_id, nuevos)
        if camino is not None:
            for lec_id in camino:
                if lec_id not in titulos:
                    titulos[lec_id] = (await self.db.get(LeccionCurricular, lec_id)).leccion_titulo
            cadena = " → ".join(f"«{titulos[i]}»" for i in camino)
            raise CicloPrerrequisitos(
                f"No se puede: «{titulos[camino[0]]}» ya depende de esta lección ({cadena}). "
                "Se formaría un círculo."
            )

        marca = await self.db.get(NucleoPrerrequisitoEditado, (anio_lectivo_id, leccion_id))
        if marca is None:
            marca = NucleoPrerrequisitoEditado(anio_lectivo_id=anio_lectivo_id, leccion_id=leccion_id)
            self.db.add(marca)
        marca.profesor_id = profesor_id
        marca.fecha_actualizacion = datetime.utcnow()
        await self.db.flush()
        await self.db.execute(delete(NucleoPrerrequisitoAnio).where(and_(
            NucleoPrerrequisitoAnio.anio_lectivo_id == anio_lectivo_id,
            NucleoPrerrequisitoAnio.leccion_id == leccion_id,
        )))
        for pre_id in nuevos:
            self.db.add(NucleoPrerrequisitoAnio(
                anio_lectivo_id=anio_lectivo_id, leccion_id=leccion_id, prerrequisito_id=pre_id,
            ))
        await self.db.flush()
        return nuevos

    async def restaurar_prerrequisitos(self, anio_lectivo_id: int, profesor_id: int, leccion_id: str) -> None:
        """Vuelve a los prerrequisitos del currículo (borra la edición del año).

        No puede formar un ciclo: si los del currículo lo formaran con otras ediciones del año,
        se rechaza y el profesor debe deshacer primero esa otra edición."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        marca = await self.db.get(NucleoPrerrequisitoEditado, (anio_lectivo_id, leccion_id))
        if marca is None:
            return
        efectivos = await prerrequisitos_efectivos(self.db, anio_lectivo_id)
        defecto = (await prerrequisitos_efectivos(self.db, None)).get(leccion_id, ())
        camino = camino_de_ciclo(efectivos, leccion_id, defecto)
        if camino is not None:
            titulo = (await self.db.get(LeccionCurricular, camino[0])).leccion_titulo
            raise CicloPrerrequisitos(
                "No se pueden restaurar los del programa: formarían un círculo con otro cambio que "
                f"hiciste este año. Revisa los prerrequisitos de «{titulo}»."
            )
        await self.db.delete(marca)
        await self.db.flush()

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

    async def describir(self, asignaciones: list[NucleoAsignacion]) -> list[dict]:
        """Asignaciones con el título de la lección y el nombre del estudiante."""
        ids_lec = {a.leccion_id for a in asignaciones}
        ids_est = {a.estudiante_id for a in asignaciones}
        titulos, nombres = {}, {}
        if ids_lec:
            titulos = {i: t for i, t in (await self.db.execute(
                select(LeccionCurricular.id, LeccionCurricular.leccion_titulo).where(LeccionCurricular.id.in_(ids_lec))
            )).tuples()}
        if ids_est:
            nombres = {i: n for i, n in (await self.db.execute(
                select(Estudiante.id, Estudiante.nombre_completo).where(Estudiante.id.in_(ids_est))
            )).tuples()}
        return [
            {
                "id": a.id, "anio_lectivo_id": a.anio_lectivo_id, "estudiante_id": a.estudiante_id,
                "leccion_id": a.leccion_id, "estado": a.estado, "fecha_asignacion": a.fecha_asignacion,
                "fecha_cierre": a.fecha_cierre, "leccion_titulo": titulos.get(a.leccion_id, a.leccion_id),
                "estudiante_nombre": nombres.get(a.estudiante_id, ""),
            }
            for a in asignaciones
        ]

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

    async def ajustes(self, anio_lectivo_id: int, profesor_id: int) -> list[dict]:
        """Ajustes de los estudiantes activos del salón (sin fila = sin ajustes)."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        filas = await self.db.execute(
            select(Matricula.estudiante_id, NucleoAjusteEstudiante.banco_forzado)
            .outerjoin(NucleoAjusteEstudiante, NucleoAjusteEstudiante.estudiante_id == Matricula.estudiante_id)
            .where(and_(Matricula.anio_lectivo_id == anio_lectivo_id, Matricula.estado == MATRICULA_ACTIVA))
            .order_by(Matricula.estudiante_id)
        )
        return [{"estudiante_id": e, "banco_forzado": bool(b)} for e, b in filas.tuples()]

    async def exigir_estudiante_del_profesor(self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int) -> None:
        """Para consultar: el estudiante estuvo en ese salón (también en años cerrados)."""
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await self._matricula(anio, estudiante_id, solo_activa=False)


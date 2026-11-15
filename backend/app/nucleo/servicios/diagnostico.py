"""
Diagnóstico inicial del núcleo con acceso a la base (fase 7a). El algoritmo está en
app/nucleo/diagnostico.py; aquí se decide cuándo se hace, se arma su sesión y se aplica el resultado.

- **Cuándo:** automático la primera vez que el estudiante entra a practicar en el núcleo, si tiene
  lecciones candidatas, ninguna práctica previa en el núcleo y ningún diagnóstico anterior. El
  profesor puede pedir otro desde la ficha; se hace la próxima vez que el estudiante empiece.
- **Sesión:** una NucleoSesion de tipo "diagnostico". Su plan se arma problema a problema; cada
  problema es de un intento, sin pistas, y no da experiencia ni toca el dominio.
- **Resultado:** las lecciones sabidas sin dominio confirmado pasan a "dominado provisional"; la
  práctica las confirma o las retira con la regla de siempre. Un provisional que este diagnóstico
  da por no sabido se retira.
- **Sin terminar:** queda pendiente y se retoma. El profesor puede cerrarlo con lo obtenido (se
  aplica lo ya decidido) o cancelarlo (no se aplica nada).
"""

from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import ahora_utc
from app.models.curriculo import LeccionCurricular
from app.models.nucleo import (
    ASIGNACION_ACTIVA,
    DIAGNOSTICO_AUTOMATICO,
    DIAGNOSTICO_CANCELADO,
    DIAGNOSTICO_CERRADO,
    DIAGNOSTICO_EN_CURSO,
    DIAGNOSTICO_PENDIENTE,
    DIAGNOSTICO_PROFESOR,
    DIAGNOSTICO_TERMINADO,
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    PROBLEMA_TERMINADO,
    SESION_ABANDONADA,
    SESION_ACTIVA,
    SESION_COMPLETADA,
    SESION_DIAGNOSTICO,
    ZONA_DIAGNOSTICO,
    ZONAS_FUERA_DEL_DOMINIO,
    NucleoAsignacion,
    NucleoDiagnostico,
    NucleoDominio,
    NucleoHabilitacion,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.nucleo import diagnostico as algoritmo
from app.nucleo.diagnostico import EstadoDiagnostico, Respuesta
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.registro import tiene_generador
from app.nucleo.servicios.grafo import cargar_grafo
from app.services.school_service import Conflicto, NoEncontrado

ABIERTOS = (DIAGNOSTICO_PENDIENTE, DIAGNOSTICO_EN_CURSO)


class ServicioDiagnostico:
    def __init__(self, db: AsyncSession, parametros: Optional[ParametrosNucleo] = None,
                 reloj: Callable[[], datetime] = ahora_utc):
        self.db = db
        self._parametros = parametros
        self.reloj = reloj

    async def parametros(self) -> ParametrosNucleo:
        if self._parametros is None:
            self._parametros = await cargar_parametros(self.db)
        return self._parametros

    # ── Lecturas ────────────────────────────────────────────────────────────

    async def abierto(self, estudiante_id: int) -> Optional[NucleoDiagnostico]:
        return (await self.db.execute(
            select(NucleoDiagnostico).where(and_(
                NucleoDiagnostico.estudiante_id == estudiante_id, NucleoDiagnostico.estado.in_(ABIERTOS)))
        )).scalar_one_or_none()

    async def candidatas(self, estudiante_id: int, anio_lectivo_id: int) -> tuple[list[str], list[str]]:
        """(lecciones a decidir, las que ya domina confirmadas)."""
        habilitadas = set((await self.db.execute(
            select(NucleoHabilitacion.leccion_id).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id, NucleoHabilitacion.habilitada.is_(True)))
        )).scalars())
        asignadas = set((await self.db.execute(
            select(NucleoAsignacion.leccion_id).where(and_(
                NucleoAsignacion.estudiante_id == estudiante_id, NucleoAsignacion.estado == ASIGNACION_ACTIVA))
        )).scalars())
        lecciones = sorted(lec for lec in habilitadas | asignadas if tiene_generador(lec))
        conocidas = set((await self.db.execute(
            select(NucleoDominio.leccion_id).where(and_(
                NucleoDominio.estudiante_id == estudiante_id, NucleoDominio.estado == DOMINIO_DOMINADO,
                NucleoDominio.leccion_id.in_(lecciones)))
        )).scalars()) if lecciones else set()
        return lecciones, sorted(conocidas)

    async def _corresponde_automatico(self, estudiante_id: int) -> bool:
        """Nunca tuvo diagnóstico ni practicó en el núcleo."""
        if not (await self.parametros()).diagnostico_activo:
            return False
        alguno = await self.db.scalar(select(exists().where(NucleoDiagnostico.estudiante_id == estudiante_id)))
        if alguno:
            return False
        practico = await self.db.scalar(select(exists().where(and_(
            NucleoProblemaSesion.estudiante_id == estudiante_id, NucleoProblemaSesion.estado == PROBLEMA_TERMINADO))))
        return not practico

    async def por_hacer(self, estudiante_id: int, anio_lectivo_id: int) -> Optional[NucleoDiagnostico]:
        """El diagnóstico que toca al empezar a practicar (lo crea si es el automático), o None."""
        diag = await self.abierto(estudiante_id)
        if diag is not None and diag.anio_lectivo_id != anio_lectivo_id:
            # Cambió de salón con un diagnóstico a medias: el del otro año ya no aplica
            await self._cerrar_sesion(diag, SESION_ABANDONADA)
            diag.estado, diag.fecha_fin = DIAGNOSTICO_CANCELADO, self.reloj()
            await self.db.flush()
            diag = None
        if diag is not None:
            return diag
        lecciones, _ = await self.candidatas(estudiante_id, anio_lectivo_id)
        if not lecciones or not await self._corresponde_automatico(estudiante_id):
            return None
        diag = NucleoDiagnostico(estudiante_id=estudiante_id, anio_lectivo_id=anio_lectivo_id,
                                 estado=DIAGNOSTICO_PENDIENTE, origen=DIAGNOSTICO_AUTOMATICO,
                                 fecha_creacion=self.reloj())
        self.db.add(diag)
        await self.db.flush()
        return diag

    async def tocaria(self, estudiante_id: int, anio_lectivo_id: int) -> bool:
        """¿Empezaría un diagnóstico al entrar a practicar? (sin crear nada)."""
        diag = await self.abierto(estudiante_id)
        if diag is not None and diag.anio_lectivo_id == anio_lectivo_id:
            return True
        lecciones, _ = await self.candidatas(estudiante_id, anio_lectivo_id)
        return bool(lecciones) and await self._corresponde_automatico(estudiante_id)

    async def de_la_sesion(self, sesion_id: int) -> NucleoDiagnostico:
        diag = (await self.db.execute(
            select(NucleoDiagnostico).where(NucleoDiagnostico.sesion_id == sesion_id))).scalar_one_or_none()
        if diag is None:
            raise NoEncontrado("Diagnóstico no encontrado.")
        return diag

    async def respuestas(self, sesion_id: int) -> list[Respuesta]:
        filas = await self.db.execute(
            select(NucleoProblemaSesion.leccion_id, NucleoProblemaSesion.correcto, NucleoIntento.tiempo_ms)
            .outerjoin(NucleoIntento, and_(NucleoIntento.problema_sesion_id == NucleoProblemaSesion.id,
                                           NucleoIntento.numero == 1))
            .where(and_(NucleoProblemaSesion.sesion_id == sesion_id,
                        NucleoProblemaSesion.estado == PROBLEMA_TERMINADO))
            .order_by(NucleoProblemaSesion.orden)
        )
        return [Respuesta(lec, bool(c), int(t or 0)) for lec, c, t in filas.tuples()]

    async def calcular(self, diag: NucleoDiagnostico) -> EstadoDiagnostico:
        lecciones = (diag.lecciones or {}).get("candidatas", [])
        conocidas = set((diag.lecciones or {}).get("conocidas", []))
        respuestas = await self.respuestas(diag.sesion_id) if diag.sesion_id else []
        grafo = await cargar_grafo(self.db, diag.anio_lectivo_id)
        return algoritmo.calcular(lecciones, conocidas, grafo, respuestas, await self.parametros())

    # ── Estudiante ──────────────────────────────────────────────────────────

    async def iniciar(self, diag: NucleoDiagnostico) -> Optional[NucleoSesion]:
        """Arma la sesión del diagnóstico. None si no queda nada por probar (lo da por terminado)."""
        p = await self.parametros()
        ahora = self.reloj()
        lecciones, conocidas = await self.candidatas(diag.estudiante_id, diag.anio_lectivo_id)
        if not lecciones:
            return None          # sin lecciones habilitadas queda pendiente para cuando las haya
        diag.lecciones = {"candidatas": lecciones, "conocidas": conocidas}
        diag.fecha_inicio = ahora
        estado = await self.calcular(diag)
        if estado.terminado:
            await self.finalizar(diag, estado, DIAGNOSTICO_TERMINADO)
            return None
        sesion = NucleoSesion(
            estudiante_id=diag.estudiante_id, anio_lectivo_id=diag.anio_lectivo_id, estado=SESION_ACTIVA,
            tipo=SESION_DIAGNOSTICO, plan=[], cantidad_problemas=p.diagnostico_max_problemas, progreso=0,
            fecha_inicio=ahora,
        )
        self.db.add(sesion)
        await self.db.flush()
        diag.sesion_id = sesion.id
        diag.estado = DIAGNOSTICO_EN_CURSO
        await self.db.flush()
        return sesion

    async def siguiente_leccion(self, sesion: NucleoSesion) -> Optional[str]:
        """Lección del próximo problema; si el diagnóstico terminó, lo aplica y devuelve None."""
        diag = await self.de_la_sesion(sesion.id)
        estado = await self.calcular(diag)
        if estado.terminado:
            await self.finalizar(diag, estado, DIAGNOSTICO_TERMINADO)
            return None
        sesion.plan = [*sesion.plan, {"leccion_id": estado.siguiente, "zona": ZONA_DIAGNOSTICO}]
        return estado.siguiente

    async def tras_responder(self, sesion: NucleoSesion) -> dict:
        """Después de cada problema: si ya terminó, aplica el resultado."""
        diag = await self.de_la_sesion(sesion.id)
        estado = await self.calcular(diag)
        diag.problemas, diag.tiempo_ms = estado.problemas, estado.tiempo_ms
        if estado.terminado:
            await self.finalizar(diag, estado, DIAGNOSTICO_TERMINADO)
        await self.db.flush()
        return {"terminado": estado.terminado, "avance": estado.avance(await self.parametros())}

    async def finalizar(self, diag: NucleoDiagnostico, estado: EstadoDiagnostico, estado_final: str,
                        profesor_id: Optional[int] = None) -> None:
        ahora = self.reloj()
        resultado = estado.resultado()
        if estado_final != DIAGNOSTICO_CANCELADO:
            await self._aplicar(diag.estudiante_id, resultado, ahora)
        diag.resultado = resultado
        diag.estado = estado_final
        diag.motivo_fin = estado.motivo_fin
        diag.problemas, diag.tiempo_ms = estado.problemas, estado.tiempo_ms
        diag.fecha_fin = ahora
        if profesor_id is not None:
            diag.profesor_id = profesor_id
        await self._cerrar_sesion(diag, SESION_COMPLETADA if estado_final == DIAGNOSTICO_TERMINADO else SESION_ABANDONADA)
        await self.db.flush()

    async def _cerrar_sesion(self, diag: NucleoDiagnostico, estado_sesion: str) -> None:
        if diag.sesion_id is None:
            return
        sesion = await self.db.get(NucleoSesion, diag.sesion_id)
        if sesion is not None and sesion.estado == SESION_ACTIVA:
            sesion.estado = estado_sesion
            sesion.cantidad_problemas = max(sesion.progreso, 1) if estado_sesion == SESION_COMPLETADA else sesion.cantidad_problemas
            sesion.fecha_fin = self.reloj()

    async def _aplicar(self, estudiante_id: int, resultado: list[dict], ahora: datetime) -> None:
        """Sabidas → dominado provisional (si no estaban confirmadas). Un provisional que ahora sale
        no sabido se retira: vuelve a "en progreso" si tiene práctica, o a "sin empezar"."""
        ids = [f["leccion_id"] for f in resultado]
        filas = {d.leccion_id: d for d in (await self.db.execute(
            select(NucleoDominio).where(and_(NucleoDominio.estudiante_id == estudiante_id,
                                             NucleoDominio.leccion_id.in_(ids))))).scalars()} if ids else {}
        con_practica = set((await self.db.execute(
            select(NucleoProblemaSesion.leccion_id).where(and_(
                NucleoProblemaSesion.estudiante_id == estudiante_id, NucleoProblemaSesion.leccion_id.in_(ids),
                NucleoProblemaSesion.estado == PROBLEMA_TERMINADO,
                NucleoProblemaSesion.zona.notin_(ZONAS_FUERA_DEL_DOMINIO)))
        )).scalars()) if ids else set()
        for f in resultado:
            fila = filas.get(f["leccion_id"])
            f["aplicada"] = False
            if f["decision"] == algoritmo.SABIDA and f["origen"] != algoritmo.PREVIA:
                if fila is None:
                    self.db.add(NucleoDominio(estudiante_id=estudiante_id, leccion_id=f["leccion_id"],
                                              estado=DOMINIO_PROVISIONAL, fecha_inicio=ahora))
                    f["aplicada"] = True
                elif fila.estado in (DOMINIO_EN_PROGRESO, DOMINIO_PROVISIONAL):
                    fila.estado, fila.repaso_desde = DOMINIO_PROVISIONAL, None
                    f["aplicada"] = True
            elif f["decision"] == algoritmo.NO_SABIDA and fila is not None and fila.estado == DOMINIO_PROVISIONAL:
                if f["leccion_id"] in con_practica:
                    fila.estado, fila.repaso_desde = DOMINIO_EN_PROGRESO, None
                else:
                    await self.db.delete(fila)
        await self.db.flush()

    # ── Profesor ────────────────────────────────────────────────────────────

    async def pedir(self, estudiante_id: int, anio_lectivo_id: int, profesor_id: int) -> NucleoDiagnostico:
        """Pide repetir el diagnóstico: se hace la próxima vez que el estudiante empiece."""
        if await self.abierto(estudiante_id) is not None:
            raise Conflicto("Ya tiene un diagnóstico pendiente.")
        diag = NucleoDiagnostico(estudiante_id=estudiante_id, anio_lectivo_id=anio_lectivo_id,
                                 estado=DIAGNOSTICO_PENDIENTE, origen=DIAGNOSTICO_PROFESOR,
                                 profesor_id=profesor_id, fecha_creacion=self.reloj())
        self.db.add(diag)
        await self.db.flush()
        return diag

    async def _abierto_del_anio(self, estudiante_id: int, anio_lectivo_id: int) -> NucleoDiagnostico:
        diag = await self.abierto(estudiante_id)
        if diag is None or diag.anio_lectivo_id != anio_lectivo_id:
            raise Conflicto("No tiene un diagnóstico pendiente.")
        return diag

    async def cerrar(self, estudiante_id: int, anio_lectivo_id: int, profesor_id: int) -> NucleoDiagnostico:
        """Cierra el diagnóstico a medias aplicando lo que ya se decidió."""
        diag = await self._abierto_del_anio(estudiante_id, anio_lectivo_id)
        if diag.estado == DIAGNOSTICO_PENDIENTE:
            raise Conflicto("Todavía no empezó: puedes cancelarlo.")
        await self.finalizar(diag, await self.calcular(diag), DIAGNOSTICO_CERRADO, profesor_id)
        return diag

    async def cancelar(self, estudiante_id: int, anio_lectivo_id: int, profesor_id: int) -> NucleoDiagnostico:
        diag = await self._abierto_del_anio(estudiante_id, anio_lectivo_id)
        estado = await self.calcular(diag) if diag.estado == DIAGNOSTICO_EN_CURSO else EstadoDiagnostico([])
        await self.finalizar(diag, estado, DIAGNOSTICO_CANCELADO, profesor_id)
        return diag

    async def para_la_ficha(self, estudiante_id: int, anio_lectivo_id: int) -> Optional[dict]:
        """El último diagnóstico del año lectivo, con el estado actual de cada provisional."""
        diag = (await self.db.execute(
            select(NucleoDiagnostico).where(and_(
                NucleoDiagnostico.estudiante_id == estudiante_id, NucleoDiagnostico.anio_lectivo_id == anio_lectivo_id))
            .order_by(NucleoDiagnostico.fecha_creacion.desc(), NucleoDiagnostico.id.desc()).limit(1)
        )).scalar_one_or_none()
        if diag is None:
            return None
        if diag.estado == DIAGNOSTICO_EN_CURSO:
            estado = await self.calcular(diag)
            resultado = estado.resultado()
            problemas, tiempo_ms = estado.problemas, estado.tiempo_ms
        else:
            resultado = list(diag.resultado or [])
            problemas, tiempo_ms = diag.problemas, diag.tiempo_ms
        ids = [f["leccion_id"] for f in resultado]
        actuales = dict((await self.db.execute(
            select(NucleoDominio.leccion_id, NucleoDominio.estado).where(and_(
                NucleoDominio.estudiante_id == estudiante_id, NucleoDominio.leccion_id.in_(ids)))
        )).tuples().all()) if ids else {}
        lecciones = {lec.id: lec for lec in (await self.db.execute(
            select(LeccionCurricular).where(LeccionCurricular.id.in_(ids)))).scalars()} if ids else {}
        for f in resultado:
            lec = lecciones.get(f["leccion_id"])
            f["titulo"] = lec.leccion_titulo if lec else f["leccion_id"]
            f["grado"] = lec.grado if lec else None
            f["unidad_numero"] = lec.unidad_numero if lec else None
            f["leccion_numero"] = lec.leccion_numero if lec else None
            f["seguimiento"] = None
            if f.get("aplicada"):
                actual = actuales.get(f["leccion_id"])
                f["seguimiento"] = ("confirmado" if actual == DOMINIO_DOMINADO
                                    else "por_confirmar" if actual == DOMINIO_PROVISIONAL else "retirado")
        return {
            "id": diag.id, "estado": diag.estado, "origen": diag.origen, "motivo_fin": diag.motivo_fin,
            "fecha_creacion": diag.fecha_creacion, "fecha_inicio": diag.fecha_inicio, "fecha_fin": diag.fecha_fin,
            "problemas": problemas, "minutos": round(tiempo_ms / 60000, 1), "lecciones": resultado,
        }

    async def abiertos_del_salon(self, ids: list[int], anio_lectivo_id: int) -> dict[int, str]:
        """estudiante → "pendiente" o "en_curso" (para la vista por estudiante)."""
        if not ids:
            return {}
        return dict((await self.db.execute(
            select(NucleoDiagnostico.estudiante_id, NucleoDiagnostico.estado).where(and_(
                NucleoDiagnostico.estudiante_id.in_(ids), NucleoDiagnostico.anio_lectivo_id == anio_lectivo_id,
                NucleoDiagnostico.estado.in_(ABIERTOS)))
        )).tuples().all())

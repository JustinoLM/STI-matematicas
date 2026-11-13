"""
Práctica del estudiante en el núcleo: sesión, problemas, respuestas, pistas, dominio,
extensión, refuerzo y experiencia.

Flujo:
1. iniciar_sesion: arma el plan con el reparto (o devuelve la sesión activa).
2. siguiente: genera el problema del turno (o devuelve el que está pendiente).
3. responder: corrige, registra el intento y sus eventos. Al terminar el problema (acierto o
   intentos agotados) actualiza el dominio o la extensión, la experiencia y la asignación.
4. pista: registra el nivel usado (el nivel 3 hace que el problema no cuente como acierto).

Todo el tiempo sale de `reloj` (UTC sin zona), así las pruebas pueden simular días distintos.
"""

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculo import LeccionCurricular
from app.models.nucleo import (
    ASIGNACION_ACTIVA,
    ASIGNACION_CERRADA,
    PROBLEMA_PENDIENTE,
    PROBLEMA_TERMINADO,
    SESION_ABANDONADA,
    SESION_ACTIVA,
    SESION_COMPLETADA,
    XP_ACIERTO,
    XP_LECCION_DOMINADA,
    XP_PRACTICA,
    ZONA_EXTENSION,
    NucleoAjusteEstudiante,
    NucleoAsignacion,
    NucleoDominio,
    NucleoEvento,
    NucleoExperiencia,
    NucleoExtension,
    NucleoHabilitacion,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.nucleo import dominio as reglas_dominio
from app.nucleo.dominio import EV_DOMINADA, EstadoDominio, Resultado
from app.nucleo.modos import ConfigModosLeccion, Modo, resolver_modos
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.problema import problema_a_dict, problema_desde_dict, solucion
from app.nucleo.registro import obtener_generador, tiene_generador
from app.nucleo.reparto import (
    Candidata,
    Grafo,
    ItemPlan,
    SinLecciones,
    candidatos_extension,
    candidatos_refuerzo,
    repartir,
)
from app.nucleo.servicios import Prohibido, RespuestaInvalida, SaldoInsuficiente
from app.nucleo.servicios.grafo import cargar_grafo
from app.nucleo.servicios.habilitacion import PISTAS_POR_DEFECTO
from app.nucleo.validacion import RespuestaMalFormada
from app.services.school_service import Conflicto, NoEncontrado, SchoolService

_INTENTOS_GENERAR_DISTINTO = 20


@dataclass
class Contexto:
    estudiante_id: int
    anio_lectivo_id: int
    grado: int


@dataclass
class Foto:
    """Lo que el reparto necesita saber del estudiante."""
    candidatas: list[Candidata]
    habilitaciones: dict[str, NucleoHabilitacion]
    asignadas: set[str]
    dominios: dict[str, NucleoDominio]
    resultados: dict[str, list[Resultado]]
    grafo: Grafo


def estado_de(fila: Optional[NucleoDominio]) -> EstadoDominio:
    if fila is None:
        return EstadoDominio()
    return EstadoDominio(
        estado=fila.estado, fecha_dominio=fila.fecha_dominio,
        ultima_practica=fila.ultima_practica, repaso_desde=fila.repaso_desde,
    )


class ServicioPractica:
    def __init__(
        self,
        db: AsyncSession,
        parametros: Optional[ParametrosNucleo] = None,
        rng: Optional[random.Random] = None,
        reloj: Callable[[], datetime] = datetime.utcnow,
    ):
        self.db = db
        self.school = SchoolService(db)
        self._parametros = parametros
        self.rng = rng or random.Random()
        self.reloj = reloj

    async def parametros(self) -> ParametrosNucleo:
        if self._parametros is None:
            self._parametros = await cargar_parametros(self.db)
        return self._parametros

    # ── Lecturas ────────────────────────────────────────────────────────────

    async def contexto(self, estudiante_id: int) -> Contexto:
        m = await self.school.exigir_salon(estudiante_id)
        return Contexto(estudiante_id, m.anio_lectivo_id, m.anio_lectivo.salon.grado)

    async def grafo(self, anio_lectivo_id: Optional[int] = None) -> Grafo:
        """El del año lectivo (con las ediciones del profesor) o, sin año, el del currículo."""
        return await cargar_grafo(self.db, anio_lectivo_id)

    async def resultados(self, estudiante_id: int, leccion_id: Optional[str] = None) -> dict[str, list[Resultado]]:
        """Resultados que cuentan para el dominio (sin extensión), en orden cronológico."""
        condiciones = [
            NucleoProblemaSesion.estudiante_id == estudiante_id,
            NucleoProblemaSesion.estado == PROBLEMA_TERMINADO,
            NucleoProblemaSesion.zona != ZONA_EXTENSION,
        ]
        if leccion_id is not None:
            condiciones.append(NucleoProblemaSesion.leccion_id == leccion_id)
        filas = await self.db.execute(
            select(NucleoProblemaSesion.leccion_id, NucleoProblemaSesion.acierto, NucleoProblemaSesion.fecha_fin)
            .where(and_(*condiciones))
            .order_by(NucleoProblemaSesion.fecha_fin, NucleoProblemaSesion.id)
        )
        por_leccion: dict[str, list[Resultado]] = {}
        for lec, acierto, fecha in filas.tuples():
            por_leccion.setdefault(lec, []).append(Resultado(bool(acierto), fecha))
        return por_leccion

    async def foto(self, estudiante_id: int, anio_lectivo_id: int) -> Foto:
        p = await self.parametros()
        ahora = self.reloj()
        habilitaciones = {
            h.leccion_id: h for h in (await self.db.execute(
                select(NucleoHabilitacion).where(and_(
                    NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                    NucleoHabilitacion.habilitada.is_(True),
                ))
            )).scalars()
        }
        asignadas = set((await self.db.execute(
            select(NucleoAsignacion.leccion_id).where(and_(
                NucleoAsignacion.estudiante_id == estudiante_id,
                NucleoAsignacion.estado == ASIGNACION_ACTIVA,
            ))
        )).scalars())
        dominios = {
            d.leccion_id: d for d in (await self.db.execute(
                select(NucleoDominio).where(NucleoDominio.estudiante_id == estudiante_id)
            )).scalars()
        }
        resultados = await self.resultados(estudiante_id)
        grafo = await self.grafo(anio_lectivo_id)

        candidatas = []
        for leccion_id in sorted(set(habilitaciones) | asignadas):
            if not tiene_generador(leccion_id):
                continue
            estado = estado_de(dominios.get(leccion_id))
            recientes = reglas_dominio.recientes(resultados.get(leccion_id, []), p)
            hab = habilitaciones.get(leccion_id)
            candidatas.append(Candidata(
                leccion_id=leccion_id,
                orden=grafo.orden.get(leccion_id, 0),
                estado=estado.estado,
                prioritaria=bool(hab and hab.prioritaria),
                precision=reglas_dominio.precision(recientes),
                resultados=len(recientes),
                repaso_pendiente=reglas_dominio.repaso_pendiente(estado, ahora, p),
                ultima_practica=estado.ultima_practica,
            ))
        return Foto(candidatas, habilitaciones, asignadas, dominios, resultados, grafo)

    async def planificar(self, estudiante_id: int, anio_lectivo_id: int) -> list[ItemPlan]:
        p = await self.parametros()
        ahora = self.reloj()
        foto = await self.foto(estudiante_id, anio_lectivo_id)
        estados = {k: v.estado for k, v in foto.dominios.items()}
        pausadas = set((await self.db.execute(
            select(NucleoExtension.leccion_id).where(and_(
                NucleoExtension.estudiante_id == estudiante_id,
                NucleoExtension.pausada_hasta > ahora,
            ))
        )).scalars())
        extension = candidatos_extension(foto.candidatas, estados, pausadas, tiene_generador, foto.grafo)
        refuerzo = candidatos_refuerzo(foto.candidatas, estados, tiene_generador, foto.grafo, p)
        return repartir(foto.candidatas, extension, refuerzo, foto.grafo, p, self.rng)

    # ── Sesión ──────────────────────────────────────────────────────────────

    async def iniciar_sesion(self, estudiante_id: int) -> NucleoSesion:
        """Sesión nueva con su plan, o la activa si ya hay una."""
        ctx = await self.contexto(estudiante_id)
        activa = await self.sesion_activa(estudiante_id)
        if activa is not None:
            return activa
        try:
            plan = await self.planificar(estudiante_id, ctx.anio_lectivo_id)
        except SinLecciones:
            raise Conflicto("Tu profesor todavía no habilitó lecciones para practicar.") from None
        sesion = NucleoSesion(
            estudiante_id=estudiante_id,
            anio_lectivo_id=ctx.anio_lectivo_id,
            estado=SESION_ACTIVA,
            plan=[{"leccion_id": it.leccion_id, "zona": it.zona} for it in plan],
            cantidad_problemas=len(plan),
            progreso=0,
            fecha_inicio=self.reloj(),
        )
        self.db.add(sesion)
        await self.db.flush()
        return sesion

    async def sesion_activa(self, estudiante_id: int) -> Optional[NucleoSesion]:
        return (await self.db.execute(
            select(NucleoSesion).where(and_(
                NucleoSesion.estudiante_id == estudiante_id, NucleoSesion.estado == SESION_ACTIVA,
            ))
        )).scalar_one_or_none()

    async def estado(self, estudiante_id: int) -> dict:
        """¿Practica en el núcleo? Sí, si tiene salón y alguna lección habilitada o asignada con
        generador, o una sesión a medias. Sirve para decidir a qué práctica lleva "Practicar"."""
        activa = await self.sesion_activa(estudiante_id)
        matricula = await self.school.matricula_activa(estudiante_id)
        disponible = activa is not None
        if not disponible and matricula is not None:
            habilitadas = (await self.db.execute(
                select(NucleoHabilitacion.leccion_id).where(and_(
                    NucleoHabilitacion.anio_lectivo_id == matricula.anio_lectivo_id,
                    NucleoHabilitacion.habilitada.is_(True),
                ))
            )).scalars()
            asignadas = (await self.db.execute(
                select(NucleoAsignacion.leccion_id).where(and_(
                    NucleoAsignacion.estudiante_id == estudiante_id,
                    NucleoAsignacion.estado == ASIGNACION_ACTIVA,
                ))
            )).scalars()
            disponible = any(tiene_generador(lec) for lec in [*habilitadas, *asignadas])
        sesion = None
        if activa is not None:
            minutos = max(int((self.reloj() - activa.fecha_inicio).total_seconds() // 60), 0)
            sesion = {
                "sesion_id": activa.id, "estado": activa.estado,
                "cantidad_problemas": activa.cantidad_problemas, "progreso": activa.progreso,
                "fecha_inicio": activa.fecha_inicio, "minutos_transcurridos": minutos,
            }
        return {"disponible": disponible, "sesion_activa": sesion}

    async def descartar(self, estudiante_id: int, sesion_id: int) -> NucleoSesion:
        """Abandona la sesión activa. El problema que quedó pendiente no se termina, así que no
        cuenta para el dominio ni da experiencia; los intentos ya hechos quedan registrados."""
        sesion = await self.sesion_del_estudiante(sesion_id, estudiante_id)
        if sesion.estado != SESION_ACTIVA:
            raise Conflicto("Esta sesión ya terminó.")
        sesion.estado = SESION_ABANDONADA
        sesion.fecha_fin = self.reloj()
        await self.db.flush()
        return sesion

    async def sesion_del_estudiante(self, sesion_id: int, estudiante_id: int) -> NucleoSesion:
        sesion = await self.db.get(NucleoSesion, sesion_id)
        if sesion is None or sesion.estudiante_id != estudiante_id:
            raise NoEncontrado("Sesión no encontrada.")
        return sesion

    async def _config_leccion(self, anio_lectivo_id: int, leccion_id: str) -> Optional[NucleoHabilitacion]:
        return (await self.db.execute(
            select(NucleoHabilitacion).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id,
                NucleoHabilitacion.leccion_id == leccion_id,
                NucleoHabilitacion.habilitada.is_(True),
            ))
        )).scalar_one_or_none()

    async def pistas_habilitadas(self, sesion: NucleoSesion, leccion_id: str) -> dict[str, bool]:
        hab = await self._config_leccion(sesion.anio_lectivo_id, leccion_id)
        return dict(hab.pistas) if hab else dict(PISTAS_POR_DEFECTO)

    async def siguiente(self, estudiante_id: int, sesion_id: int) -> Optional[NucleoProblemaSesion]:
        """Problema del turno; None si la sesión terminó."""
        sesion = await self.sesion_del_estudiante(sesion_id, estudiante_id)
        if sesion.estado != SESION_ACTIVA:
            return None
        pendiente = (await self.db.execute(
            select(NucleoProblemaSesion).where(and_(
                NucleoProblemaSesion.sesion_id == sesion.id,
                NucleoProblemaSesion.orden == sesion.progreso,
            ))
        )).scalar_one_or_none()
        if pendiente is not None:
            return pendiente

        item = sesion.plan[sesion.progreso]
        leccion_id = item["leccion_id"]
        p = await self.parametros()
        generador = obtener_generador(leccion_id)
        hab = await self._config_leccion(sesion.anio_lectivo_id, leccion_id)
        config = ConfigModosLeccion(Modo(hab.signo), Modo(hab.iconos)) if hab else ConfigModosLeccion()
        ajuste = await self.db.get(NucleoAjusteEstudiante, estudiante_id)
        grado = (await self.contexto(estudiante_id)).grado

        # Evita repetir un problema de la misma lección en la sesión
        vistos = {
            json.dumps(ps.problema["segmentos"] if "segmentos" in ps.problema else ps.problema.get("numeros"))
            for ps in (await self.db.execute(
                select(NucleoProblemaSesion).where(and_(
                    NucleoProblemaSesion.sesion_id == sesion.id,
                    NucleoProblemaSesion.leccion_id == leccion_id,
                ))
            )).scalars()
        }
        for _ in range(_INTENTOS_GENERAR_DISTINTO):
            modos = resolver_modos(
                config,
                grado_estudiante=grado,
                banco_forzado=bool(ajuste and ajuste.banco_forzado),
                admite_signo_oculto=generador.admite_signo_oculto,
                admite_iconos=generador.admite_iconos,
                banco_en_grados_intermedios=generador.banco_en_grados_intermedios,
                parametros=p,
                rng=self.rng,
            )
            problema = problema_a_dict(generador.crear(self.rng, modos))
            clave = json.dumps(problema.get("segmentos", problema.get("numeros")))
            if clave not in vistos:
                break

        ps = NucleoProblemaSesion(
            sesion_id=sesion.id, estudiante_id=estudiante_id, orden=sesion.progreso,
            leccion_id=leccion_id, zona=item["zona"], problema=problema,
            estado=PROBLEMA_PENDIENTE, intentos=0, pista_max_nivel=0, fecha_creacion=self.reloj(),
        )
        self.db.add(ps)
        await self.db.flush()
        return ps

    async def _problema_del_turno(self, estudiante_id: int, sesion_id: int, problema_sesion_id: int):
        sesion = await self.sesion_del_estudiante(sesion_id, estudiante_id)
        ps = await self.db.get(NucleoProblemaSesion, problema_sesion_id)
        if ps is None or ps.sesion_id != sesion.id:
            raise NoEncontrado("Problema no encontrado en esta sesión.")
        if sesion.estado != SESION_ACTIVA or ps.estado != PROBLEMA_PENDIENTE or ps.orden != sesion.progreso:
            raise Conflicto("Este problema ya no está en curso.")
        return sesion, ps

    # ── Respuesta ───────────────────────────────────────────────────────────

    async def responder(
        self,
        estudiante_id: int,
        sesion_id: int,
        problema_sesion_id: int,
        respuestas: Any,
        tiempo_ms: int,
        uso_voz: bool = False,
        eventos: Optional[list[dict]] = None,
    ) -> dict:
        p = await self.parametros()
        ahora = self.reloj()
        sesion, ps = await self._problema_del_turno(estudiante_id, sesion_id, problema_sesion_id)
        generador = obtener_generador(ps.leccion_id)
        problema = problema_desde_dict(ps.problema)
        try:
            resultado = generador.corregir(problema, respuestas)
        except RespuestaMalFormada as e:
            raise RespuestaInvalida(str(e)) from None

        numero = ps.intentos + 1
        intento = NucleoIntento(
            problema_sesion_id=ps.id, estudiante_id=estudiante_id, numero=numero,
            respuestas=respuestas, correcto=resultado.correcto,
            errores={h: r.error for h, r in resultado.huecos.items() if not r.correcto},
            pista_max_nivel=ps.pista_max_nivel, tiempo_ms=tiempo_ms, uso_voz=uso_voz,
            modo_respuesta=problema.modos.respuesta.value, fecha=ahora,
        )
        self.db.add(intento)
        await self.db.flush()
        for ev in eventos or []:
            self.db.add(NucleoEvento(
                problema_sesion_id=ps.id, intento_id=intento.id, tipo=ev["tipo"],
                valor=ev.get("valor"), ms=ev.get("ms"), fecha=ahora,
            ))
        ps.intentos = numero

        terminado = resultado.correcto or numero >= p.intentos_por_problema
        respuesta: dict[str, Any] = {
            "correcto": resultado.correcto,
            "huecos": {h: r.correcto for h, r in resultado.huecos.items()},
            "intentos_restantes": max(p.intentos_por_problema - numero, 0),
            "problema_terminado": terminado,
            "solucion": None,
            "experiencia_ganada": 0,
            "evento_dominio": None,
            "sesion_completada": False,
        }
        if terminado:
            await self._terminar_problema(sesion, ps, resultado.correcto, numero, ahora, respuesta)
            if not resultado.correcto:
                respuesta["solucion"] = solucion(problema)
        await self.db.flush()
        return respuesta

    async def _terminar_problema(
        self, sesion: NucleoSesion, ps: NucleoProblemaSesion, correcto: bool, numero: int,
        ahora: datetime, respuesta: dict,
    ) -> None:
        p = await self.parametros()
        ps.estado = PROBLEMA_TERMINADO
        ps.fecha_fin = ahora
        ps.correcto = correcto
        ps.acierto = correcto and numero == 1 and ps.pista_max_nivel < 3
        sesion.progreso += 1
        if sesion.progreso >= sesion.cantidad_problemas:
            sesion.estado = SESION_COMPLETADA
            sesion.fecha_fin = ahora
            respuesta["sesion_completada"] = True
        await self.db.flush()

        xp = self._experiencia(ps, XP_PRACTICA, p.xp_practica, ahora)
        if correcto and numero == 1:
            xp += self._experiencia(ps, XP_ACIERTO, p.xp_acierto, ahora)

        if ps.zona == ZONA_EXTENSION:
            await self._actualizar_extension(ps, ahora)
        else:
            evento = await self._actualizar_dominio(ps.estudiante_id, ps.leccion_id, ahora)
            respuesta["evento_dominio"] = evento
            if evento == EV_DOMINADA:
                xp += await self._bono_dominio(ps, ahora)
                await self._cerrar_asignaciones(ps.estudiante_id, ps.leccion_id, ahora)
        respuesta["experiencia_ganada"] = xp

    def _experiencia(self, ps: NucleoProblemaSesion, tipo: str, cantidad: int, ahora: datetime,
                     primera_vez: Optional[bool] = None) -> int:
        self.db.add(NucleoExperiencia(
            estudiante_id=ps.estudiante_id, tipo=tipo, cantidad=cantidad, leccion_id=ps.leccion_id,
            problema_sesion_id=ps.id, primera_vez=primera_vez, fecha=ahora,
        ))
        return cantidad

    async def _bono_dominio(self, ps: NucleoProblemaSesion, ahora: datetime) -> int:
        """El evento se registra cada vez que se domina la lección; `primera_vez` permite a la
        fase 7 decidir si el bono se da una sola vez."""
        anteriores = await self.db.scalar(
            select(func.count()).select_from(NucleoExperiencia).where(and_(
                NucleoExperiencia.estudiante_id == ps.estudiante_id,
                NucleoExperiencia.leccion_id == ps.leccion_id,
                NucleoExperiencia.tipo == XP_LECCION_DOMINADA,
            ))
        )
        p = await self.parametros()
        return self._experiencia(ps, XP_LECCION_DOMINADA, p.xp_bono_dominio, ahora, primera_vez=anteriores == 0)

    async def _actualizar_dominio(self, estudiante_id: int, leccion_id: str, ahora: datetime) -> Optional[str]:
        p = await self.parametros()
        fila = await self.db.get(NucleoDominio, (estudiante_id, leccion_id))
        resultados = (await self.resultados(estudiante_id, leccion_id)).get(leccion_id, [])
        nuevo, evento = reglas_dominio.evaluar(estado_de(fila), resultados, p)
        if fila is None:
            fila = NucleoDominio(estudiante_id=estudiante_id, leccion_id=leccion_id, fecha_inicio=ahora)
            self.db.add(fila)
        fila.estado = nuevo.estado
        fila.fecha_dominio = nuevo.fecha_dominio
        fila.ultima_practica = nuevo.ultima_practica
        fila.repaso_desde = nuevo.repaso_desde
        return evento

    async def _cerrar_asignaciones(self, estudiante_id: int, leccion_id: str, ahora: datetime) -> None:
        for asig in (await self.db.execute(
            select(NucleoAsignacion).where(and_(
                NucleoAsignacion.estudiante_id == estudiante_id,
                NucleoAsignacion.leccion_id == leccion_id,
                NucleoAsignacion.estado == ASIGNACION_ACTIVA,
            ))
        )).scalars():
            asig.estado = ASIGNACION_CERRADA
            asig.fecha_cierre = ahora

    async def _actualizar_extension(self, ps: NucleoProblemaSesion, ahora: datetime) -> None:
        """Fallar en la extensión no baja el dominio; tras varios fallos se pausa sin aviso."""
        if ps.acierto:
            return
        p = await self.parametros()
        ext = await self.db.get(NucleoExtension, (ps.estudiante_id, ps.leccion_id))
        if ext is None:
            ext = NucleoExtension(estudiante_id=ps.estudiante_id, leccion_id=ps.leccion_id)
            self.db.add(ext)
        fallos = await self.db.scalar(
            select(func.count()).select_from(NucleoProblemaSesion).where(and_(
                NucleoProblemaSesion.estudiante_id == ps.estudiante_id,
                NucleoProblemaSesion.leccion_id == ps.leccion_id,
                NucleoProblemaSesion.zona == ZONA_EXTENSION,
                NucleoProblemaSesion.estado == PROBLEMA_TERMINADO,
                NucleoProblemaSesion.acierto.is_(False),
                NucleoProblemaSesion.fecha_fin > (ext.contar_desde or datetime.min),
            ))
        )
        if fallos >= p.fallos_pausa_extension:
            ext.pausada_hasta = ahora + timedelta(days=p.dias_pausa_extension)
            ext.contar_desde = ahora

    # ── Pistas ──────────────────────────────────────────────────────────────

    async def pista(self, estudiante_id: int, sesion_id: int, problema_sesion_id: int, nivel: int) -> dict:
        p = await self.parametros()
        sesion, ps = await self._problema_del_turno(estudiante_id, sesion_id, problema_sesion_id)
        if nivel not in (1, 2, 3):
            raise RespuestaInvalida("El nivel de pista es 1, 2 o 3.")
        if not (await self.pistas_habilitadas(sesion, ps.leccion_id)).get(str(nivel), True):
            raise Prohibido(f"Tu profesor deshabilitó la pista de nivel {nivel}.")
        gasto = 0
        if nivel == 3 and p.costo_pista_nivel_3 > 0 and ps.pista_max_nivel < 3:
            from app.repositories.gamification_repository import GamificationRepository
            try:
                await GamificationRepository(self.db).gastar_puntos(
                    estudiante_id=estudiante_id, cantidad=p.costo_pista_nivel_3,
                    concepto=f"Pista nivel 3 (núcleo) - problema {ps.id}",
                )
            except ValueError:
                raise SaldoInsuficiente(f"Necesitas {p.costo_pista_nivel_3} puntos para esta pista.") from None
            gasto = p.costo_pista_nivel_3
        texto = obtener_generador(ps.leccion_id).texto_pista(problema_desde_dict(ps.problema), nivel)
        ps.pista_max_nivel = max(ps.pista_max_nivel, nivel)
        self.db.add(NucleoEvento(problema_sesion_id=ps.id, tipo="pista", valor={"nivel": nivel},
                                 fecha=self.reloj()))
        await self.db.flush()
        return {"nivel": nivel, "texto": texto, "puntos_gastados": gasto}

    # ── Dominio del estudiante ──────────────────────────────────────────────

    async def resumen_dominio(self, estudiante_id: int, anio_lectivo_id: Optional[int] = None) -> dict:
        """Dominio de cada lección candidata o ya practicada, y la experiencia acumulada."""
        p = await self.parametros()
        ahora = self.reloj()
        if anio_lectivo_id is None:
            anio_lectivo_id = (await self.contexto(estudiante_id)).anio_lectivo_id
        foto = await self.foto(estudiante_id, anio_lectivo_id)
        ids = set(foto.habilitaciones) | foto.asignadas | set(foto.dominios)
        lecciones = {
            lec.id: lec for lec in (await self.db.execute(
                select(LeccionCurricular).where(LeccionCurricular.id.in_(ids))
            )).scalars()
        }
        filas = []
        for leccion_id in sorted(ids, key=lambda i: foto.grafo.orden.get(i, 0)):
            estado = estado_de(foto.dominios.get(leccion_id))
            recientes = reglas_dominio.recientes(foto.resultados.get(leccion_id, []), p)
            hab = foto.habilitaciones.get(leccion_id)
            lec = lecciones[leccion_id]
            filas.append({
                "leccion_id": leccion_id,
                "titulo": lec.leccion_titulo,
                "grado": lec.grado,
                "estado": estado.estado,
                "aciertos_recientes": sum(r.acierto for r in recientes),
                "problemas_recientes": len(recientes),
                "fecha_dominio": estado.fecha_dominio,
                "ultima_practica": estado.ultima_practica,
                "repaso_pendiente": reglas_dominio.repaso_pendiente(estado, ahora, p),
                "habilitada": hab is not None,
                "prioritaria": bool(hab and hab.prioritaria),
                "asignada": leccion_id in foto.asignadas,
                "tiene_generador": tiene_generador(leccion_id),
            })
        experiencia = await self.db.scalar(
            select(func.coalesce(func.sum(NucleoExperiencia.cantidad), 0))
            .where(NucleoExperiencia.estudiante_id == estudiante_id)
        )
        return {
            "estudiante_id": estudiante_id,
            "ventana_dominio": p.ventana_dominio,
            "umbral_dominio": p.umbral_dominio,
            "experiencia_total": int(experiencia),
            "lecciones": filas,
        }


"""
Seguimiento del profesor (fase 6b) con acceso a la base: arma la "foto del salón" con un número
fijo de consultas (no una por estudiante y lección) y delega el cálculo en app/nucleo/seguimiento.py.

- seguimiento(): tabla por lección y por estudiante, hoy o en un trimestre.
- alertas(): alertas de dificultad y excelencia del salón; ocultar() las esconde unos días.
- ficha(): dominio por lección y camino, errores frecuentes, asignaciones, ajustes, sesiones
  recientes, diagnóstico inicial y años anteriores del estudiante.
- diagnostico(): el profesor pide repetirlo, lo cierra con lo obtenido o lo cancela (fase 7a).

Los problemas del diagnóstico no entran en los resultados (ni dominio, ni acierto, ni periodo).
"""

from datetime import datetime, timedelta
from typing import Callable, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import ahora_utc
from app.models.curriculo import CaminoCurricular, LeccionCamino, LeccionCurricular
from app.models.nucleo import (
    ASIGNACION_ACTIVA,
    PROBLEMA_TERMINADO,
    TIPOS_ALERTA,
    XP_LECCION_DOMINADA,
    ZONA_DIAGNOSTICO,
    ZONA_EXTENSION,
    ZONA_REFUERZO,
    NucleoAjusteEstudiante,
    NucleoAlertaOculta,
    NucleoAsignacion,
    NucleoDominio,
    NucleoExperiencia,
    NucleoHabilitacion,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.models.school import MATRICULA_ACTIVA, AnioLectivo, Matricula, Salon
from app.models.user import Estudiante
from app.nucleo import dominio as reglas
from app.nucleo import seguimiento as calc
from app.nucleo.dominio import Resultado
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.registro import GENERADORES, tiene_generador
from app.nucleo.servicios.diagnostico import ServicioDiagnostico
from app.nucleo.servicios.grafo import prerrequisitos_efectivos
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.plan import ServicioPlan
from app.nucleo.servicios.practica import estado_de
from app.services.school_service import Conflicto, NoEncontrado, SchoolService


def descripciones_de_errores() -> dict[str, str]:
    """Código de regla → descripción para docentes, de todos los generadores registrados."""
    return {r.codigo: r.descripcion for g in GENERADORES.values() for r in g.reglas_error()}


class ServicioSeguimiento:
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

    def _plan(self) -> ServicioPlan:
        return ServicioPlan(self.db, self._parametros, self.reloj)

    def _diag(self) -> ServicioDiagnostico:
        return ServicioDiagnostico(self.db, self._parametros, self.reloj)

    # ── Foto del salón (consultas fijas) ────────────────────────────────────

    async def _lecciones(self) -> dict[str, calc.LeccionFoto]:
        caminos: dict[str, list[str]] = {}
        for lec, cam in (await self.db.execute(
            select(LeccionCamino.leccion_id, LeccionCamino.camino_id)
            .join(CaminoCurricular, CaminoCurricular.id == LeccionCamino.camino_id)
            .order_by(CaminoCurricular.orden)
        )).tuples():
            caminos.setdefault(lec, []).append(cam)
        return {
            lec.id: calc.LeccionFoto(
                id=lec.id, titulo=lec.leccion_titulo, grado=lec.grado, unidad_numero=lec.unidad_numero,
                unidad_titulo=lec.unidad_titulo, leccion_numero=lec.leccion_numero, orden=lec.orden_programa,
                caminos=tuple(caminos.get(lec.id, ())),
            )
            for lec in (await self.db.execute(select(LeccionCurricular))).scalars()
        }

    async def _resultados(self, ids: list[int], desde_refuerzo: datetime):
        resultados: dict[tuple[int, str], list[Resultado]] = {}
        extension: dict[tuple[int, str], list[Resultado]] = {}
        refuerzo: dict[tuple[int, str], int] = {}
        if not ids:
            return resultados, extension, refuerzo
        filas = await self.db.execute(
            select(NucleoProblemaSesion.estudiante_id, NucleoProblemaSesion.leccion_id, NucleoProblemaSesion.zona,
                   NucleoProblemaSesion.acierto, NucleoProblemaSesion.fecha_fin)
            .where(and_(NucleoProblemaSesion.estudiante_id.in_(ids),
                        NucleoProblemaSesion.estado == PROBLEMA_TERMINADO))
            .order_by(NucleoProblemaSesion.fecha_fin, NucleoProblemaSesion.id)
        )
        for est, lec, zona, acierto, fecha in filas.tuples():
            if zona == ZONA_DIAGNOSTICO:
                continue
            r = Resultado(bool(acierto), fecha)
            if zona == ZONA_EXTENSION:
                extension.setdefault((est, lec), []).append(r)
                continue
            resultados.setdefault((est, lec), []).append(r)
            if zona == ZONA_REFUERZO and fecha is not None and fecha >= desde_refuerzo:
                refuerzo[(est, lec)] = refuerzo.get((est, lec), 0) + 1
        return resultados, extension, refuerzo

    async def foto(self, anio_lectivo_id: int) -> calc.FotoSalon:
        p = await self.parametros()
        estudiantes = [
            calc.EstudianteFoto(i, n, c) for i, n, c in (await self.db.execute(
                select(Estudiante.id, Estudiante.nombre_completo, Estudiante.codigo_estudiante)
                .join(Matricula, Matricula.estudiante_id == Estudiante.id)
                .where(and_(Matricula.anio_lectivo_id == anio_lectivo_id, Matricula.estado == MATRICULA_ACTIVA))
                .order_by(Estudiante.nombre_completo)
            )).tuples()
        ]
        ids = [e.id for e in estudiantes]
        habs = list((await self.db.execute(
            select(NucleoHabilitacion).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id, NucleoHabilitacion.habilitada.is_(True)))
        )).scalars())
        asignadas: dict[int, set[str]] = {}
        for est, lec in (await self.db.execute(
            select(NucleoAsignacion.estudiante_id, NucleoAsignacion.leccion_id).where(and_(
                NucleoAsignacion.anio_lectivo_id == anio_lectivo_id, NucleoAsignacion.estado == ASIGNACION_ACTIVA))
        )).tuples():
            asignadas.setdefault(est, set()).add(lec)
        dominios = {
            (d.estudiante_id, d.leccion_id): estado_de(d) for d in (await self.db.execute(
                select(NucleoDominio).where(NucleoDominio.estudiante_id.in_(ids))
            )).scalars()
        } if ids else {}
        resultados, extension, refuerzo = await self._resultados(
            ids, self.reloj() - timedelta(days=p.alerta_dificultad_dias_refuerzo))
        ocultas = {
            (o.estudiante_id, o.leccion_id, o.tipo): o.fecha for o in (await self.db.execute(
                select(NucleoAlertaOculta).where(NucleoAlertaOculta.anio_lectivo_id == anio_lectivo_id)
            )).scalars()
        }
        return calc.FotoSalon(
            estudiantes=estudiantes, lecciones=await self._lecciones(),
            habilitadas={h.leccion_id for h in habs}, prioritarias={h.leccion_id for h in habs if h.prioritaria},
            asignadas=asignadas, dominios=dominios, resultados=resultados, extension=extension,
            refuerzo_reciente=refuerzo, prerrequisitos=await prerrequisitos_efectivos(self.db, anio_lectivo_id),
            ocultas=ocultas,
        )

    async def _periodo(self, anio: AnioLectivo, trimestre: Optional[int]) -> Optional[calc.Periodo]:
        if trimestre is None:
            return None
        for t in await self._plan().periodos(anio):
            if t.numero == trimestre:
                return t
        raise NoEncontrado("Trimestre no encontrado.")

    # ── Tabla del salón ─────────────────────────────────────────────────────

    async def seguimiento(self, anio_lectivo_id: int, profesor_id: int, trimestre: Optional[int] = None) -> dict:
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await self._plan().aplicar(anio_lectivo_id)
        p = await self.parametros()
        ahora = self.reloj()
        foto = await self.foto(anio_lectivo_id)
        alertas = calc.alertas(foto, ahora, p, tiene_generador)
        respuesta = {
            "trimestre": trimestre,
            "estudiantes": [{"id": e.id, "nombre": e.nombre, "codigo": e.codigo} for e in foto.estudiantes],
            "por_leccion": calc.tabla_por_leccion(foto, ahora, p),
            "por_estudiante": calc.tabla_por_estudiante(foto, alertas, ahora, p),
            "diagnosticos": {
                str(k): v for k, v in (await self._diag().abiertos_del_salon(
                    [e.id for e in foto.estudiantes], anio_lectivo_id)).items()
            },
            "alertas_dificultad": sum(a["tipo"] == "dificultad" for a in alertas),
            "alertas_excelencia": sum(a["tipo"] == "excelencia" for a in alertas),
            "periodo": None,
        }
        periodo = await self._periodo(anio, trimestre)
        if periodo is not None:
            ids = [e.id for e in foto.estudiantes]
            dominadas = (await self.db.execute(
                select(NucleoExperiencia.estudiante_id, NucleoExperiencia.leccion_id, NucleoExperiencia.fecha)
                .where(and_(NucleoExperiencia.estudiante_id.in_(ids), NucleoExperiencia.tipo == XP_LECCION_DOMINADA))
            )).tuples() if ids else []
            respuesta["periodo"] = {
                "numero": periodo.numero, "inicio": periodo.inicio, "fin": periodo.fin,
                "por_leccion": calc.tabla_del_periodo(foto, periodo, list(dominadas), p),
            }
        return respuesta

    # ── Alertas ─────────────────────────────────────────────────────────────

    async def alertas(self, anio_lectivo_id: int, profesor_id: int, incluir_ocultas: bool = False) -> list[dict]:
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await self._plan().aplicar(anio_lectivo_id)
        foto = await self.foto(anio_lectivo_id)
        salon = await self.db.get(Salon, anio.salon_id)
        return [
            {**a, "anio_lectivo_id": anio_lectivo_id, "salon_nombre": salon.nombre}
            for a in calc.alertas(foto, self.reloj(), await self.parametros(), tiene_generador, incluir_ocultas)
        ]

    async def alertas_del_profesor(self, profesor_id: int) -> list[dict]:
        """Las de todos los salones activos del profesor (para la página general de alertas)."""
        resultado = []
        for anio in await self.school.anios_del_profesor(profesor_id):
            if anio.estado == "activo":
                resultado.extend(await self.alertas(anio.id, profesor_id))
        return resultado

    async def ocultar(self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int, leccion_id: str, tipo: str) -> None:
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        if tipo not in TIPOS_ALERTA:
            raise Conflicto("Tipo de alerta desconocido.")
        await ServicioHabilitacion(self.db).exigir_estudiante_del_profesor(anio_lectivo_id, profesor_id, estudiante_id)
        oculta = await self.db.get(NucleoAlertaOculta, (anio_lectivo_id, estudiante_id, leccion_id, tipo))
        if oculta is None:
            oculta = NucleoAlertaOculta(anio_lectivo_id=anio_lectivo_id, estudiante_id=estudiante_id,
                                        leccion_id=leccion_id, tipo=tipo)
            self.db.add(oculta)
        oculta.fecha = self.reloj()
        await self.db.flush()

    # ── Ficha del estudiante ────────────────────────────────────────────────

    async def ficha(self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int,
                    trimestre: Optional[int] = None) -> dict:
        anio = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        await ServicioHabilitacion(self.db).exigir_estudiante_del_profesor(anio_lectivo_id, profesor_id, estudiante_id)
        p = await self.parametros()
        ahora = self.reloj()
        periodo = await self._periodo(anio, trimestre)
        est = await self.db.get(Estudiante, estudiante_id)
        salon = await self.db.get(Salon, anio.salon_id)
        lecciones = await self._lecciones()

        habs = {h.leccion_id: h for h in (await self.db.execute(
            select(NucleoHabilitacion).where(and_(
                NucleoHabilitacion.anio_lectivo_id == anio_lectivo_id, NucleoHabilitacion.habilitada.is_(True)))
        )).scalars()}
        asignaciones = list((await self.db.execute(
            select(NucleoAsignacion).where(and_(
                NucleoAsignacion.anio_lectivo_id == anio_lectivo_id, NucleoAsignacion.estudiante_id == estudiante_id))
            .order_by(NucleoAsignacion.fecha_asignacion.desc())
        )).scalars())
        activas = {a.leccion_id for a in asignaciones if a.estado == ASIGNACION_ACTIVA}
        dominios = {d.leccion_id: estado_de(d) for d in (await self.db.execute(
            select(NucleoDominio).where(NucleoDominio.estudiante_id == estudiante_id))).scalars()}
        resultados, extension, _ = await self._resultados([estudiante_id], ahora)

        def en_periodo(rs):
            return [r for r in rs if periodo is None or periodo.contiene(r.fecha, p)]

        ids = set(habs) | activas | set(dominios) | {lec for _, lec in extension}
        ids = sorted((i for i in ids if i in lecciones), key=lambda i: lecciones[i].orden)
        estados = {i: calc.estado_visible(dominios.get(i), ahora, p) for i in ids}
        filas = []
        for i in ids:
            todos = resultados.get((estudiante_id, i), [])
            rec = reglas.recientes(todos, p)
            ext = extension.get((estudiante_id, i), [])
            del_periodo = en_periodo(todos)
            filas.append({
                "leccion_id": i, "titulo": lecciones[i].titulo, "grado": lecciones[i].grado,
                "unidad_numero": lecciones[i].unidad_numero, "leccion_numero": lecciones[i].leccion_numero,
                "caminos": list(lecciones[i].caminos), "estado": estados[i],
                "habilitada": i in habs, "prioritaria": bool(habs.get(i) and habs[i].prioritaria),
                "asignada": i in activas,
                "aciertos_recientes": sum(r.acierto for r in rec), "problemas_recientes": len(rec),
                "problemas_periodo": len(del_periodo), "aciertos_periodo": sum(r.acierto for r in del_periodo),
                "extension_problemas": len(ext), "extension_aciertos": sum(r.acierto for r in ext),
                "ultima_practica": dominios[i].ultima_practica if i in dominios else None,
            })

        # Errores clasificados del periodo (o del año lectivo)
        consulta = (
            select(NucleoIntento.errores, NucleoIntento.fecha)
            .join(NucleoProblemaSesion, NucleoProblemaSesion.id == NucleoIntento.problema_sesion_id)
            .join(NucleoSesion, NucleoSesion.id == NucleoProblemaSesion.sesion_id)
            .where(and_(NucleoIntento.estudiante_id == estudiante_id, NucleoIntento.correcto.is_(False),
                        NucleoSesion.anio_lectivo_id == anio_lectivo_id,
                        NucleoProblemaSesion.zona != ZONA_DIAGNOSTICO))
        )
        codigos = [
            c for errores, fecha in (await self.db.execute(consulta)).tuples()
            if periodo is None or periodo.contiene(fecha, p)
            for c in (errores or {}).values()
        ]
        nombres_camino = dict((await self.db.execute(
            select(CaminoCurricular.id, CaminoCurricular.nombre))).tuples().all())
        errores = calc.errores_frecuentes(codigos, descripciones_de_errores())
        for e in errores:
            e["camino_nombre"] = nombres_camino.get(e["camino"]) if e["camino"] else None

        por_camino = calc.dominio_por_camino([lecciones[i] for i in ids if i in habs or i in activas], estados)
        for c in por_camino:
            c["nombre"] = nombres_camino.get(c["camino"], c["camino"])

        # Sesiones recientes del año lectivo (con sus aciertos, en una consulta)
        sesiones = (await self.db.execute(
            select(NucleoSesion, func.count(NucleoProblemaSesion.id).filter(and_(
                NucleoProblemaSesion.acierto.is_(True), NucleoProblemaSesion.zona != ZONA_DIAGNOSTICO)))
            .outerjoin(NucleoProblemaSesion, NucleoProblemaSesion.sesion_id == NucleoSesion.id)
            .where(and_(NucleoSesion.estudiante_id == estudiante_id, NucleoSesion.anio_lectivo_id == anio_lectivo_id))
            .group_by(NucleoSesion.id).order_by(NucleoSesion.fecha_inicio.desc()).limit(8)
        )).tuples().all()

        ajuste = await self.db.get(NucleoAjusteEstudiante, estudiante_id)
        return {
            "estudiante": {"id": est.id, "nombre": est.nombre_completo, "codigo": est.codigo_estudiante},
            "salon": {"anio_lectivo_id": anio_lectivo_id, "nombre": salon.nombre, "grado": salon.grado,
                      "anio": anio.anio, "cerrado": anio.estado != "activo"},
            "trimestre": trimestre,
            "periodo": {"numero": periodo.numero, "inicio": periodo.inicio, "fin": periodo.fin} if periodo else None,
            "banco_forzado": bool(ajuste and ajuste.banco_forzado),
            "lecciones": filas,
            "por_camino": por_camino,
            "errores": errores,
            "asignaciones": (await ServicioHabilitacion(self.db).describir(asignaciones))[:10],
            "sesiones": [
                {"id": s.id, "estado": s.estado, "tipo": s.tipo, "fecha_inicio": s.fecha_inicio, "fecha_fin": s.fecha_fin,
                 "problemas": s.progreso, "cantidad_problemas": s.cantidad_problemas, "aciertos": int(aciertos)}
                for s, aciertos in sesiones
            ],
            "diagnostico": await self._diag().para_la_ficha(estudiante_id, anio_lectivo_id),
            "anios_anteriores": await self._anios_anteriores(estudiante_id, anio_lectivo_id),
        }

    # ── Diagnóstico ─────────────────────────────────────────────────────────

    async def diagnostico(self, anio_lectivo_id: int, profesor_id: int, estudiante_id: int, accion: str) -> dict:
        """pedir / cerrar / cancelar. Devuelve el diagnóstico como lo muestra la ficha."""
        await self.school.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        await ServicioHabilitacion(self.db).exigir_estudiante_del_profesor(anio_lectivo_id, profesor_id, estudiante_id)
        servicio = self._diag()
        if accion == "pedir":
            await servicio.pedir(estudiante_id, anio_lectivo_id, profesor_id)
        elif accion == "cerrar":
            await servicio.cerrar(estudiante_id, anio_lectivo_id, profesor_id)
        elif accion == "cancelar":
            await servicio.cancelar(estudiante_id, anio_lectivo_id, profesor_id)
        else:
            raise Conflicto("Acción desconocida.")
        return await servicio.para_la_ficha(estudiante_id, anio_lectivo_id)

    async def _anios_anteriores(self, estudiante_id: int, anio_actual_id: int) -> list[dict]:
        """Resumen de solo lectura de los otros años lectivos del estudiante (2 consultas)."""
        anios = (await self.db.execute(
            select(AnioLectivo.id, AnioLectivo.anio, Salon.nombre, Salon.grado)
            .join(Matricula, Matricula.anio_lectivo_id == AnioLectivo.id)
            .join(Salon, Salon.id == AnioLectivo.salon_id)
            .where(and_(Matricula.estudiante_id == estudiante_id, AnioLectivo.id != anio_actual_id))
            .order_by(AnioLectivo.anio.desc())
        )).tuples().all()
        if not anios:
            return []
        ids = [a[0] for a in anios]
        stats = {
            aid: (n, ac) for aid, n, ac in (await self.db.execute(
                select(NucleoSesion.anio_lectivo_id, func.count(NucleoProblemaSesion.id),
                       func.count(NucleoProblemaSesion.id).filter(NucleoProblemaSesion.acierto.is_(True)))
                .join(NucleoProblemaSesion, NucleoProblemaSesion.sesion_id == NucleoSesion.id)
                .where(and_(NucleoSesion.estudiante_id == estudiante_id, NucleoSesion.anio_lectivo_id.in_(ids),
                            NucleoProblemaSesion.estado == PROBLEMA_TERMINADO,
                            NucleoProblemaSesion.zona != ZONA_DIAGNOSTICO))
                .group_by(NucleoSesion.anio_lectivo_id)
            )).tuples()
        }
        dominadas: dict[int, set[str]] = {}
        for aid, lec in (await self.db.execute(
            select(NucleoSesion.anio_lectivo_id, NucleoExperiencia.leccion_id)
            .join(NucleoProblemaSesion, NucleoProblemaSesion.id == NucleoExperiencia.problema_sesion_id)
            .join(NucleoSesion, NucleoSesion.id == NucleoProblemaSesion.sesion_id)
            .where(and_(NucleoExperiencia.estudiante_id == estudiante_id,
                        NucleoExperiencia.tipo == XP_LECCION_DOMINADA, NucleoSesion.anio_lectivo_id.in_(ids)))
        )).tuples():
            dominadas.setdefault(aid, set()).add(lec)
        return [
            {"anio_lectivo_id": aid, "anio": a, "salon": nombre, "grado": grado,
             "problemas": stats.get(aid, (0, 0))[0], "aciertos": stats.get(aid, (0, 0))[1],
             "lecciones_dominadas": len(dominadas.get(aid, ()))}
            for aid, a, nombre, grado in anios
        ]

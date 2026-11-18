"""
Motivación del núcleo con acceso a la base (fase 7b): nivel de jugador, medallas, mapa del camino y
barras de progreso. Las reglas están en app/nucleo/motivacion.py.

- La experiencia es la suma de nucleo_experiencia (nunca baja). El nivel se calcula, no se guarda.
- Las medallas ganadas se guardan en nucleo_medalla (una sola vez). `otorgar_medallas` compara el
  catálogo con lo ya ganado e inserta lo que falte; se llama al dominar una lección y al consultar
  las medallas (así también reciben las suyas quienes dominaron lecciones antes de esta fase).
- `practica_en_nucleo` decide si la tienda usa el nivel de jugador (pregunta abierta 14).
"""

from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import ahora_utc
from app.models.curriculo import CaminoCurricular, LeccionCamino, LeccionCurricular
from app.models.nucleo import (
    ASIGNACION_ACTIVA,
    DOMINIO_DOMINADO,
    DOMINIO_PROVISIONAL,
    PROBLEMA_TERMINADO,
    XP_LECCION_DOMINADA,
    ZONAS_FUERA_DEL_DOMINIO,
    NucleoAsignacion,
    NucleoDominio,
    NucleoExperiencia,
    NucleoHabilitacion,
    NucleoMedalla,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.nucleo import dominio as reglas
from app.nucleo import motivacion as M
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros
from app.nucleo.registro import tiene_generador
from app.services.school_service import SchoolService


def medalla_a_dict(m: M.Medalla, fila: Optional[NucleoMedalla] = None) -> dict:
    return {
        "tipo": m.tipo, "clave": m.clave, "grado_medalla": m.grado_medalla, "titulo": m.titulo,
        "descripcion": m.descripcion, "meta": m.meta, "logradas": min(m.logradas, m.meta),
        "obtenida": fila is not None, "fecha": fila.fecha if fila else None,
    }


class ServicioMotivacion:
    def __init__(self, db: AsyncSession, parametros: Optional[ParametrosNucleo] = None,
                 reloj: Callable[[], datetime] = ahora_utc):
        self.db = db
        self._parametros = parametros
        self.reloj = reloj
        self.school = SchoolService(db)

    async def parametros(self) -> ParametrosNucleo:
        if self._parametros is None:
            self._parametros = await cargar_parametros(self.db)
        return self._parametros

    # ── Experiencia y nivel ─────────────────────────────────────────────────

    async def experiencia(self, estudiante_id: int) -> int:
        return int(await self.db.scalar(
            select(func.coalesce(func.sum(NucleoExperiencia.cantidad), 0))
            .where(NucleoExperiencia.estudiante_id == estudiante_id)
        ))

    async def nivel(self, estudiante_id: int) -> M.Nivel:
        return M.nivel_de(await self.experiencia(estudiante_id), await self.parametros())

    async def practica_en_nucleo(self, estudiante_id: int) -> bool:
        """Tiene salón y lecciones del núcleo (habilitadas o asignadas con generador), o ya practicó
        en el núcleo. Es la misma condición que /nucleo/estado, sin efectos."""
        if await self.db.scalar(select(exists().where(NucleoSesion.estudiante_id == estudiante_id))):
            return True
        matricula = await self.school.matricula_activa(estudiante_id)
        if matricula is None:
            return False
        habilitadas = (await self.db.execute(select(NucleoHabilitacion.leccion_id).where(and_(
            NucleoHabilitacion.anio_lectivo_id == matricula.anio_lectivo_id, NucleoHabilitacion.habilitada.is_(True))
        ))).scalars()
        asignadas = (await self.db.execute(select(NucleoAsignacion.leccion_id).where(and_(
            NucleoAsignacion.estudiante_id == estudiante_id, NucleoAsignacion.estado == ASIGNACION_ACTIVA)
        ))).scalars()
        return any(tiene_generador(x) for x in [*habilitadas, *asignadas])

    async def grado(self, estudiante_id: int) -> Optional[int]:
        matricula = await self.school.matricula_activa(estudiante_id)
        return matricula.anio_lectivo.salon.grado if matricula else None

    # ── Lecciones del grado y medallas ──────────────────────────────────────

    async def lecciones_del_grado(self, grado: int) -> list[M.LeccionMapa]:
        caminos: dict[str, list[str]] = {}
        for lec, cam in (await self.db.execute(
            select(LeccionCamino.leccion_id, LeccionCamino.camino_id)
            .join(CaminoCurricular, CaminoCurricular.id == LeccionCamino.camino_id)
            .join(LeccionCurricular, LeccionCurricular.id == LeccionCamino.leccion_id)
            .where(LeccionCurricular.grado == grado).order_by(CaminoCurricular.orden)
        )).tuples():
            caminos.setdefault(lec, []).append(cam)
        return [
            M.LeccionMapa(lc.id, lc.grado, lc.unidad_numero, lc.unidad_titulo, lc.leccion_numero, lc.leccion_titulo,
                          lc.orden_programa, tuple(caminos.get(lc.id, ())))
            for lc in (await self.db.execute(
                select(LeccionCurricular).where(LeccionCurricular.grado == grado)
                .order_by(LeccionCurricular.orden_programa)
            )).scalars()
            if tiene_generador(lc.id)
        ]

    async def nombres_camino(self) -> dict[str, str]:
        return dict((await self.db.execute(select(CaminoCurricular.id, CaminoCurricular.nombre))).tuples().all())

    async def dominadas_alguna_vez(self, estudiante_id: int) -> dict[str, datetime]:
        """Lección → primera vez que la dominó (evento "lección dominada")."""
        return dict((await self.db.execute(
            select(NucleoExperiencia.leccion_id, func.min(NucleoExperiencia.fecha))
            .where(and_(NucleoExperiencia.estudiante_id == estudiante_id,
                        NucleoExperiencia.tipo == XP_LECCION_DOMINADA))
            .group_by(NucleoExperiencia.leccion_id)
        )).tuples().all())

    async def _catalogo(self, estudiante_id: int, grado: int):
        p = await self.parametros()
        lecciones = await self.lecciones_del_grado(grado)
        dominadas = await self.dominadas_alguna_vez(estudiante_id)
        return M.catalogo_medallas(lecciones, dominadas, await self.nombres_camino(), p), lecciones, dominadas

    async def _ganadas(self, estudiante_id: int) -> dict[tuple[str, str, str], NucleoMedalla]:
        return {(m.tipo, m.clave, m.grado_medalla): m for m in (await self.db.execute(
            select(NucleoMedalla).where(NucleoMedalla.estudiante_id == estudiante_id))).scalars()}

    async def otorgar_medallas(self, estudiante_id: int, grado: Optional[int] = None,
                               vista: bool = False) -> list[dict]:
        """Inserta las medallas que ya cumple y no tiene. Devuelve las nuevas."""
        grado = grado if grado is not None else await self.grado(estudiante_id)
        if grado is None:
            return []
        catalogo, lecciones, dominadas = await self._catalogo(estudiante_id, grado)
        ya = await self._ganadas(estudiante_id)
        nuevas = []
        for m in M.ganadas(catalogo):
            if (m.tipo, m.clave, m.grado_medalla) in ya:
                continue
            # Fecha: cuando dominó la lección que la completó (o ahora)
            if m.tipo == M.MEDALLA_LECCION:
                fecha = dominadas.get(m.clave)
            else:
                if m.tipo == M.MEDALLA_UNIDAD:
                    suyas = [x.id for x in lecciones if M.clave_unidad(x) == m.clave]
                else:
                    suyas = [x.id for x in lecciones for c in x.caminos if M.clave_camino(c, x.grado) == m.clave]
                fechas = sorted(dominadas[i] for i in suyas if i in dominadas)
                fecha = fechas[min(m.meta, len(fechas)) - 1] if fechas else None
            fila = NucleoMedalla(estudiante_id=estudiante_id, tipo=m.tipo, clave=m.clave,
                                 grado_medalla=m.grado_medalla, fecha=fecha or self.reloj(), vista=vista)
            self.db.add(fila)
            nuevas.append(medalla_a_dict(m, fila))
        if nuevas:
            await self.db.flush()
        return nuevas

    async def medallas(self, estudiante_id: int) -> dict:
        grado = await self.grado(estudiante_id)
        if grado is None:
            return {"grado": None, "obtenidas": 0, "total": 0, "medallas": []}
        await self.otorgar_medallas(estudiante_id, grado, vista=True)
        catalogo, _, _ = await self._catalogo(estudiante_id, grado)
        ya = await self._ganadas(estudiante_id)
        filas = [medalla_a_dict(m, ya.get((m.tipo, m.clave, m.grado_medalla))) for m in catalogo]
        return {"grado": grado, "obtenidas": sum(f["obtenida"] for f in filas), "total": len(filas), "medallas": filas}

    # ── Progreso: nivel, caminos y mapa ─────────────────────────────────────

    async def progreso(self, estudiante_id: int) -> dict:
        p = await self.parametros()
        ahora = self.reloj()
        nivel = await self.nivel(estudiante_id)
        base = {
            "nivel": nivel.nivel, "experiencia": nivel.experiencia, "experiencia_en_nivel": nivel.en_el_nivel,
            "experiencia_para_subir": nivel.para_subir,
            "tienda_nivel_por_requisito": [M.nivel_tienda(r, p) for r in range(1, 6)],
            "grado": None, "caminos": [], "unidades": [], "siguiente": None,
        }
        matricula = await self.school.matricula_activa(estudiante_id)
        if matricula is None:
            return base
        grado = matricula.anio_lectivo.salon.grado
        anio_id = matricula.anio_lectivo_id
        base["grado"] = grado
        lecciones = await self.lecciones_del_grado(grado)
        ids = [x.id for x in lecciones]
        dominios = {d.leccion_id: d for d in (await self.db.execute(
            select(NucleoDominio).where(and_(NucleoDominio.estudiante_id == estudiante_id,
                                             NucleoDominio.leccion_id.in_(ids))))).scalars()} if ids else {}
        habilitadas = set((await self.db.execute(select(NucleoHabilitacion.leccion_id).where(and_(
            NucleoHabilitacion.anio_lectivo_id == anio_id, NucleoHabilitacion.habilitada.is_(True))))).scalars())
        asignadas = set((await self.db.execute(select(NucleoAsignacion.leccion_id).where(and_(
            NucleoAsignacion.estudiante_id == estudiante_id, NucleoAsignacion.estado == ASIGNACION_ACTIVA)))).scalars())
        aciertos: dict[str, list[bool]] = {}
        for lec, acierto in (await self.db.execute(
            select(NucleoProblemaSesion.leccion_id, NucleoProblemaSesion.acierto).where(and_(
                NucleoProblemaSesion.estudiante_id == estudiante_id, NucleoProblemaSesion.leccion_id.in_(ids),
                NucleoProblemaSesion.estado == PROBLEMA_TERMINADO,
                NucleoProblemaSesion.zona.notin_(ZONAS_FUERA_DEL_DOMINIO)))
            .order_by(NucleoProblemaSesion.fecha_fin, NucleoProblemaSesion.id)
        )).tuples() if ids else []:
            aciertos.setdefault(lec, []).append(bool(acierto))

        def estado(lec: str) -> str:
            d = dominios.get(lec)
            if d is None:
                return "no_iniciado"
            if d.estado == DOMINIO_PROVISIONAL:
                return "provisional"
            if d.estado == DOMINIO_DOMINADO:
                e = reglas.EstadoDominio(d.estado, d.fecha_dominio, d.ultima_practica, d.repaso_desde)
                return "repaso" if reglas.repaso_pendiente(e, ahora, p) else "dominado"
            return "en_progreso"

        en_practica = habilitadas | asignadas
        siguiente = next((x.id for x in lecciones if x.id in en_practica and estado(x.id) in ("en_progreso", "no_iniciado")),
                         None)
        unidades: dict[int, dict] = {}
        for x in lecciones:
            u = unidades.setdefault(x.unidad_numero, {"unidad_numero": x.unidad_numero, "titulo": x.unidad_titulo,
                                                      "lecciones": []})
            u["lecciones"].append({
                "leccion_id": x.id, "titulo": x.titulo, "leccion_numero": x.leccion_numero, "estado": estado(x.id),
                "en_practica": x.id in en_practica, "siguiente": x.id == siguiente,
                **M.casillas_dominio(aciertos.get(x.id, []), p),
            })
        nombres = await self.nombres_camino()
        caminos: dict[str, list[str]] = {}
        for x in lecciones:
            for cam in x.caminos:
                caminos.setdefault(cam, []).append(x.id)
        base["caminos"] = [
            {"camino": cam, "nombre": nombres.get(cam, cam), "total": len(ls),
             "dominadas": sum(estado(i) in ("dominado", "repaso") for i in ls),
             "provisionales": sum(estado(i) == "provisional" for i in ls)}
            for cam, ls in caminos.items()
        ]
        base["unidades"] = list(unidades.values())
        base["siguiente"] = siguiente
        return base

"""
Núcleo de práctica (fase 3b) con la base: sesión, intentos y eventos, dominio a lo largo de
varios días, cierre de la asignación individual, extensión con pausa, refuerzo, prioridad,
banco forzado, repaso, y la API /api/nucleo de punta a punta.

El tiempo se controla con un reloj falso (ServicioPractica(reloj=...)), así los "días
distintos" y el repaso no dependen de la fecha real. Para la extensión y el refuerzo hace falta
una segunda lección con generador: se registra uno de prueba para g1-u03-l02.
"""

import random
from datetime import datetime, timedelta
from itertools import count

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.models.nucleo import (
    ASIGNACION_CERRADA,
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    SESION_COMPLETADA,
    XP_LECCION_DOMINADA,
    ZONA_EXTENSION,
    ZONA_NORMAL,
    ZONA_REFUERZO,
    ZONA_REPASO,
    NucleoAsignacion,
    NucleoDominio,
    NucleoEvento,
    NucleoExperiencia,
    NucleoExtension,
    NucleoIntento,
    NucleoProblemaSesion,
)
from app.models.user import Estudiante
from app.nucleo.lecciones.naturales.g1_u03_l01 import SumemosHorizontal
from app.nucleo.modos import ModoRespuesta
from app.nucleo.problema import HuecoNumero, HuecoOpcion, problema_desde_dict, solucion
from app.nucleo.registro import GENERADORES
from app.nucleo.servicios import Prohibido, RespuestaInvalida
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.practica import ServicioPractica
from app.services.curriculo_service import cargar_programa, leer_programa
from app.services.school_service import Conflicto
from tests.conftest import TestSessionLocal
from tests.salones_helpers import crear_organizacion, salon_con_estudiantes
from tests.test_organizacion_escolar import _estudiante, _org, _profesor, _salon

pytestmark = pytest.mark.db

L01 = "g1-u03-l01"   # Sumemos de forma horizontal (generador real)
L02 = "g1-u03-l02"   # Restemos de forma horizontal: depende de L01 (generador de prueba)
LUNES = datetime(2026, 11, 9, 15, 0)
_n = count(1)


class Reloj:
    def __init__(self, inicio: datetime = LUNES):
        self.ahora = inicio

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **kw) -> None:
        self.ahora += timedelta(**kw)


class GeneradorPruebaL02(SumemosHorizontal):
    leccion_id = L02
    caminos = ("naturales.resta",)


@pytest.fixture
def con_l02(monkeypatch):
    monkeypatch.setitem(GENERADORES, L02, GeneradorPruebaL02())


async def preparar(db, *, grado=1, habilitar=(L01,)):
    await cargar_programa(db, leer_programa())
    org = await crear_organizacion(db)
    est = Estudiante(codigo_estudiante=f"NUC{next(_n)}", password_hash="x", tipo_usuario="estudiante",
                     nombre_completo="Estudiante Núcleo", organizacion_id=org.id)
    db.add(est)
    await db.flush()
    prof, al = await salon_con_estudiantes(db, [est.id], organizacion_id=org.id, grado=grado)
    hab = ServicioHabilitacion(db)
    for lec in habilitar:
        await hab.habilitar(al.id, prof.id, lec)
    return est, prof, al


def respuesta_bien(ps) -> dict:
    return solucion(problema_desde_dict(ps.problema))


def respuesta_mal(ps) -> dict:
    problema = problema_desde_dict(ps.problema)
    mal = {}
    for h in problema.huecos.values():
        if isinstance(h, HuecoNumero):
            mal[h.id] = str(next(o.valor for o in h.banco if o.valor != h.correcta)) if h.banco else str(h.correcta + 1)
        elif isinstance(h, HuecoOpcion):
            mal[h.id] = next(o.id for o in h.opciones if o.id != h.correcta)
    return mal


async def resolver(serv, est_id, sesion_id, *, bien=True, reloj=None):
    """Resuelve el problema del turno (bien al primer intento, o mal y luego bien)."""
    ps = await serv.siguiente(est_id, sesion_id)
    if reloj:
        reloj.avanzar(minutes=1)
    if not bien:
        await serv.responder(est_id, sesion_id, ps.id, respuesta_mal(ps), 1000)
    r = await serv.responder(est_id, sesion_id, ps.id, respuesta_bien(ps), 1000)
    return ps, r


async def sesion_completa(serv, est_id, reloj, bien=lambda ps: True):
    sesion = await serv.iniciar_sesion(est_id)
    ultima = None
    while (ps := await serv.siguiente(est_id, sesion.id)) is not None:
        reloj.avanzar(minutes=1)
        if not bien(ps):
            await serv.responder(est_id, sesion.id, ps.id, respuesta_mal(ps), 1000)
        ultima = await serv.responder(est_id, sesion.id, ps.id, respuesta_bien(ps), 1000)
    return sesion, ultima


# ─── Sesión y dominio ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_domina_tras_practicar_en_dos_dias():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        reloj = Reloj()
        serv = ServicioPractica(db, rng=random.Random(1), reloj=reloj)

        sesion, ultima = await sesion_completa(serv, est.id, reloj)
        assert sesion.cantidad_problemas == 10
        assert {it["leccion_id"] for it in sesion.plan} == {L01}
        assert sesion.estado == SESION_COMPLETADA and ultima["sesion_completada"]
        assert await serv.siguiente(est.id, sesion.id) is None
        dominio = await db.get(NucleoDominio, (est.id, L01))
        assert dominio.estado == DOMINIO_EN_PROGRESO          # 10 de 10, pero un solo día

        reloj.avanzar(days=1)
        sesion2 = await serv.iniciar_sesion(est.id)
        assert sesion2.id != sesion.id
        _, r = await resolver(serv, est.id, sesion2.id, reloj=reloj)
        assert r["evento_dominio"] == "dominada"
        assert r["experiencia_ganada"] == 1 + 2 + 50
        await db.refresh(dominio)
        assert dominio.estado == DOMINIO_DOMINADO

        bono = (await db.execute(select(NucleoExperiencia).where(
            NucleoExperiencia.tipo == XP_LECCION_DOMINADA))).scalar_one()
        assert bono.primera_vez is True and bono.leccion_id == L01
        resumen = await serv.resumen_dominio(est.id)
        assert resumen["experiencia_total"] == 11 * 3 + 50
        fila = resumen["lecciones"][0]
        assert (fila["leccion_id"], fila["estado"], fila["aciertos_recientes"]) == (L01, DOMINIO_DOMINADO, 10)


@pytest.mark.asyncio
async def test_iniciar_devuelve_la_sesion_activa():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        serv = ServicioPractica(db)
        a = await serv.iniciar_sesion(est.id)
        b = await serv.iniciar_sesion(est.id)
        assert a.id == b.id
        ps1 = await serv.siguiente(est.id, a.id)
        assert (await serv.siguiente(est.id, a.id)).id == ps1.id   # el pendiente no se regenera


@pytest.mark.asyncio
async def test_acierto_es_al_primer_intento_y_sin_pista_3():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        serv = ServicioPractica(db, rng=random.Random(2))
        s = await serv.iniciar_sesion(est.id)

        # Mal y luego bien: correcto, pero no es acierto
        ps, r = await resolver(serv, est.id, s.id, bien=False)
        assert (ps.correcto, ps.acierto, ps.intentos) == (True, False, 2)
        assert r["experiencia_ganada"] == 1

        # Pista de nivel 3 y bien al primer intento: no es acierto
        ps = await serv.siguiente(est.id, s.id)
        pista = await serv.pista(est.id, s.id, ps.id, 3)
        assert pista["texto"] and pista["puntos_gastados"] == 0
        await serv.responder(est.id, s.id, ps.id, respuesta_bien(ps), 1000)
        assert (ps.correcto, ps.acierto, ps.pista_max_nivel) == (True, False, 3)
        intento = (await db.execute(select(NucleoIntento).where(NucleoIntento.problema_sesion_id == ps.id))).scalar_one()
        assert intento.pista_max_nivel == 3

        # Pista de nivel 2: sí es acierto
        ps = await serv.siguiente(est.id, s.id)
        await serv.pista(est.id, s.id, ps.id, 2)
        await serv.responder(est.id, s.id, ps.id, respuesta_bien(ps), 1000)
        assert ps.acierto is True

        # Tres intentos mal: termina, sin acierto, y muestra la solución
        ps = await serv.siguiente(est.id, s.id)
        for k in (1, 2, 3):
            r = await serv.responder(est.id, s.id, ps.id, respuesta_mal(ps), 1000)
            assert r["intentos_restantes"] == 3 - k
        assert r["problema_terminado"] and not r["correcto"]
        assert r["solucion"] == respuesta_bien(ps)
        assert (ps.correcto, ps.acierto) == (False, False)
        assert (await serv.siguiente(est.id, s.id)).orden == 4


@pytest.mark.asyncio
async def test_respuesta_mal_formada_no_cuenta_como_intento():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        serv = ServicioPractica(db)
        s = await serv.iniciar_sesion(est.id)
        ps = await serv.siguiente(est.id, s.id)
        for mala in ({"resultado": "cinco"}, {"resultado": "99"}, {}, {"otro": 1}):
            with pytest.raises(RespuestaInvalida):
                await serv.responder(est.id, s.id, ps.id, mala, 1000)
        assert ps.intentos == 0
        assert await db.scalar(select(func.count()).select_from(NucleoIntento)) == 0

        await serv.responder(est.id, s.id, ps.id, respuesta_bien(ps), 1000)
        with pytest.raises(Conflicto):   # ya no es el problema del turno
            await serv.responder(est.id, s.id, ps.id, respuesta_bien(ps), 1000)
        with pytest.raises(Conflicto):
            await serv.pista(est.id, s.id, ps.id, 1)


@pytest.mark.asyncio
async def test_registro_de_eventos_por_intento():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        serv = ServicioPractica(db)
        s = await serv.iniciar_sesion(est.id)
        ps = await serv.siguiente(est.id, s.id)
        mal = respuesta_mal(ps)
        eventos = [
            {"tipo": "opcion_elegida", "valor": mal["resultado"], "ms": 1500},
            {"tipo": "cambio_opcion", "valor": {"de": mal["resultado"], "a": "x"}, "ms": 2100},
            {"tipo": "voz", "valor": None, "ms": 300},
        ]
        await serv.pista(est.id, s.id, ps.id, 1)
        await serv.responder(est.id, s.id, ps.id, mal, 4200, uso_voz=True, eventos=eventos)

        intento = (await db.execute(select(NucleoIntento))).scalar_one()
        assert (intento.tiempo_ms, intento.uso_voz, intento.correcto) == (4200, True, False)
        assert intento.modo_respuesta == ModoRespuesta.BANCO.value
        assert intento.respuestas == mal
        assert intento.errores["resultado"].startswith("naturales.suma.")
        filas = (await db.execute(select(NucleoEvento).order_by(NucleoEvento.id))).scalars().all()
        assert [e.tipo for e in filas] == ["pista", "opcion_elegida", "cambio_opcion", "voz"]
        assert filas[0].intento_id is None and filas[0].valor == {"nivel": 1}
        assert all(e.intento_id == intento.id for e in filas[1:])
        assert filas[1].ms == 1500


# ─── Asignación individual ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_la_asignacion_individual_se_cierra_al_dominar():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        asig = await hab.asignar(al.id, prof.id, est.id, L01)
        assert (await hab.asignar(al.id, prof.id, est.id, L01)).id == asig.id   # idempotente

        reloj = Reloj()
        serv = ServicioPractica(db, rng=random.Random(3), reloj=reloj)
        await sesion_completa(serv, est.id, reloj)
        assert asig.estado == "activa"
        reloj.avanzar(days=1)
        s = await serv.iniciar_sesion(est.id)
        await resolver(serv, est.id, s.id, reloj=reloj)
        await db.refresh(asig)
        assert asig.estado == ASIGNACION_CERRADA and asig.fecha_cierre == reloj.ahora
        with pytest.raises(Conflicto):
            await hab.asignar(al.id, prof.id, est.id, L01)


@pytest.mark.asyncio
async def test_cancelar_asignacion():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        asig = await hab.asignar(al.id, prof.id, est.id, L01)
        await hab.cancelar_asignacion(asig.id, prof.id)
        assert asig.estado == "cancelada"
        with pytest.raises(Conflicto):
            await hab.cancelar_asignacion(asig.id, prof.id)
        with pytest.raises(Conflicto):   # sin lecciones habilitadas ni asignadas no hay sesión
            await ServicioPractica(db).iniciar_sesion(est.id)


# ─── Extensión y refuerzo ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extension_aparte_y_pausa_sin_aviso(con_l02):
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        reloj = Reloj()
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=L01, estado=DOMINIO_DOMINADO,
                             fecha_inicio=reloj.ahora, fecha_dominio=reloj.ahora, ultima_practica=reloj.ahora))
        await db.flush()
        serv = ServicioPractica(db, rng=random.Random(4), reloj=reloj)

        # Falla los problemas de extensión (mal y luego bien), acierta los demás
        sesion, _ = await sesion_completa(serv, est.id, reloj, bien=lambda ps: ps.zona != ZONA_EXTENSION)
        zonas = [(it["leccion_id"], it["zona"]) for it in sesion.plan]
        assert zonas.count((L02, ZONA_EXTENSION)) == 2 and zonas.count((L01, ZONA_NORMAL)) == 8
        assert zonas[0][1] != ZONA_EXTENSION

        # Fallar en la extensión no crea dominio de L02 ni baja el de L01
        assert await db.get(NucleoDominio, (est.id, L02)) is None
        assert (await db.get(NucleoDominio, (est.id, L01))).estado == DOMINIO_DOMINADO
        ext = await db.get(NucleoExtension, (est.id, L02))
        assert ext.pausada_hasta is not None and ext.pausada_hasta > reloj.ahora

        # En pausa: la siguiente sesión no trae extensión
        reloj.avanzar(hours=1)
        sesion2, _ = await sesion_completa(serv, est.id, reloj)
        assert all(it["zona"] != ZONA_EXTENSION for it in sesion2.plan)

        # Pasada la pausa vuelve
        reloj.avanzar(days=8)
        sesion3 = await serv.iniciar_sesion(est.id)
        assert any(it["zona"] == ZONA_EXTENSION for it in sesion3.plan)


@pytest.mark.asyncio
async def test_refuerzo_del_prerrequisito_que_falla(con_l02):
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db, habilitar=(L02,))   # L01 (su prerrequisito) no está habilitada
        reloj = Reloj()
        serv = ServicioPractica(db, rng=random.Random(5), reloj=reloj)

        sesion, _ = await sesion_completa(serv, est.id, reloj, bien=lambda ps: False)
        assert all(it["zona"] != ZONA_REFUERZO for it in sesion.plan)
        assert (await db.get(NucleoDominio, (est.id, L02))).estado == DOMINIO_EN_PROGRESO

        sesion2 = await serv.iniciar_sesion(est.id)
        zonas = [(it["leccion_id"], it["zona"]) for it in sesion2.plan]
        assert zonas.count((L01, ZONA_REFUERZO)) == 2
        assert zonas.count((L02, ZONA_NORMAL)) == 8

        # Los problemas de refuerzo cuentan para el dominio del prerrequisito
        while (ps := await serv.siguiente(est.id, sesion2.id)) is not None:
            await serv.responder(est.id, sesion2.id, ps.id, respuesta_bien(ps), 1000)
        assert (await db.get(NucleoDominio, (est.id, L01))).estado == DOMINIO_EN_PROGRESO


# ─── Repaso, prioridad, deshabilitar y banco forzado ─────────────────────────

@pytest.mark.asyncio
async def test_la_leccion_dominada_vuelve_como_repaso():
    async with TestSessionLocal() as db:
        est, _, _ = await preparar(db)
        reloj = Reloj()
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=L01, estado=DOMINIO_DOMINADO, fecha_inicio=LUNES,
                             fecha_dominio=LUNES, ultima_practica=LUNES - timedelta(days=15)))
        await db.flush()
        serv = ServicioPractica(db, rng=random.Random(6), reloj=reloj)
        sesion = await serv.iniciar_sesion(est.id)
        assert {it["zona"] for it in sesion.plan} == {ZONA_REPASO}
        # Repaso fallido: menos de 60 % en los primeros 5 → en progreso
        eventos = []
        for _ in range(5):
            ps = await serv.siguiente(est.id, sesion.id)
            r = await serv.responder(est.id, sesion.id, ps.id, respuesta_mal(ps), 1000)
            r = await serv.responder(est.id, sesion.id, ps.id, respuesta_bien(ps), 1000)
            eventos.append(r["evento_dominio"])
        assert eventos[-1] == "repaso_fallido"
        assert (await db.get(NucleoDominio, (est.id, L01))).estado == DOMINIO_EN_PROGRESO


@pytest.mark.asyncio
async def test_maximo_de_lecciones_prioritarias():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        for lec in ("g1-u03-l01", "g1-u03-l02", "g1-u03-l03"):
            await hab.habilitar(al.id, prof.id, lec, prioritaria=True)
        with pytest.raises(Conflicto):
            await hab.habilitar(al.id, prof.id, "g1-u05-l01", prioritaria=True)
        await hab.habilitar(al.id, prof.id, "g1-u03-l01", prioritaria=True)   # reconfigurar no cuenta doble
        await hab.deshabilitar(al.id, prof.id, "g1-u03-l03")
        h = await hab.habilitar(al.id, prof.id, "g1-u05-l01", prioritaria=True)
        assert h.prioritaria


@pytest.mark.asyncio
async def test_habilitar_solo_lecciones_incluidas():
    from app.services.school_service import NoEncontrado

    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        with pytest.raises(NoEncontrado):
            await hab.habilitar(al.id, prof.id, "g9-u99-l99")
        excluida = next(lec.id for lec in leer_programa().lecciones if not lec.incluida)
        with pytest.raises(Conflicto):
            await hab.habilitar(al.id, prof.id, excluida)


@pytest.mark.asyncio
async def test_deshabilitar_conserva_el_dominio():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db)
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=L01, estado=DOMINIO_DOMINADO,
                             fecha_inicio=LUNES, fecha_dominio=LUNES, ultima_practica=LUNES))
        await db.flush()
        await ServicioHabilitacion(db).deshabilitar(al.id, prof.id, L01)
        serv = ServicioPractica(db)
        with pytest.raises(Conflicto):
            await serv.iniciar_sesion(est.id)
        fila = (await serv.resumen_dominio(est.id))["lecciones"][0]
        assert (fila["estado"], fila["habilitada"]) == (DOMINIO_DOMINADO, False)


@pytest.mark.asyncio
async def test_banco_por_grado_y_forzado_por_estudiante():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, grado=4)
        serv = ServicioPractica(db)
        s = await serv.iniciar_sesion(est.id)
        ps = await serv.siguiente(est.id, s.id)
        assert ps.problema["modos"]["respuesta"] == "teclado"
        await ServicioHabilitacion(db).ajustar_estudiante(al.id, prof.id, est.id, banco_forzado=True)
        await serv.responder(est.id, s.id, ps.id, respuesta_bien(ps), 1000)
        ps = await serv.siguiente(est.id, s.id)
        assert ps.problema["modos"]["respuesta"] == "banco"


@pytest.mark.asyncio
async def test_pista_deshabilitada_por_el_profesor():
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db, habilitar=())
        await ServicioHabilitacion(db).habilitar(al.id, prof.id, L01, pistas={"3": False})
        serv = ServicioPractica(db)
        s = await serv.iniciar_sesion(est.id)
        ps = await serv.siguiente(est.id, s.id)
        assert await serv.pistas_habilitadas(s, L01) == {"1": True, "2": True, "3": False}
        with pytest.raises(Prohibido):
            await serv.pista(est.id, s.id, ps.id, 3)
        assert (await serv.pista(est.id, s.id, ps.id, 2))["nivel"] == 2


# ─── API ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_del_nucleo_de_punta_a_punta():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        await db.commit()

    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, HP = await _profesor(c, org)
        _, HP2 = await _profesor(c, org)
        est_id, HE = await _estudiante(c, org)
        _, HE2 = await _estudiante(c, org)
        al = (await _salon(c, HP))["anio_lectivo_id"]
        r = await c.post(f"/api/teachers/salones/{al}/estudiantes/{est_id}", headers=HP)
        assert r.status_code == 204, r.text

        # Sin lecciones habilitadas no hay sesión; sin salón, 403
        assert (await c.post("/api/nucleo/sesiones", headers=HE)).status_code == 409
        assert (await c.post("/api/nucleo/sesiones", headers=HE2)).status_code == 403

        # El profesor habilita con el signo oculto
        r = await c.put(f"/api/nucleo/anios/{al}/lecciones/{L01}", headers=HP,
                        json={"signo": "nunca", "iconos": "azar", "pistas": {"3": False}})
        assert r.status_code == 200, r.text
        assert r.json()["tiene_generador"] and r.json()["pistas"] == {"1": True, "2": True, "3": False}
        assert (await c.put(f"/api/nucleo/anios/{al}/lecciones/{L01}", headers=HP2, json={})).status_code == 404
        assert (await c.put(f"/api/nucleo/anios/{al}/lecciones/no-existe", headers=HP, json={})).status_code == 404
        assert (await c.put(f"/api/nucleo/anios/{al}/lecciones/{L01}", headers=HE, json={})).status_code == 403
        lista = (await c.get(f"/api/nucleo/anios/{al}/lecciones", headers=HP)).json()
        assert [x["leccion_id"] for x in lista] == [L01]

        # El estudiante practica
        r = await c.post("/api/nucleo/sesiones", headers=HE)
        assert r.status_code == 200, r.text
        sesion_id = r.json()["sesion_id"]
        r = await c.get(f"/api/nucleo/sesiones/{sesion_id}/siguiente", headers=HE)
        datos = r.json()
        assert r.status_code == 200 and not datos["sesion_completada"]
        assert datos["pistas_habilitadas"]["3"] is False and datos["intentos_restantes"] == 3
        problema = datos["problema"]
        assert "datos" not in problema and "correcta" not in str(problema)
        assert [h["id"] for h in problema["huecos"]] == ["operador"]
        pid = datos["problema_sesion_id"]
        base = f"/api/nucleo/sesiones/{sesion_id}/problemas/{pid}"

        r = await c.post(f"{base}/pista", headers=HE, json={"nivel": 1})
        assert r.status_code == 200 and r.json()["texto"]
        assert (await c.post(f"{base}/pista", headers=HE, json={"nivel": 3})).status_code == 403
        assert (await c.post(f"{base}/pista", headers=HE, json={"nivel": 4})).status_code == 422

        r = await c.post(f"{base}/respuesta", headers=HE, json={"respuestas": {"operador": "×"}, "tiempo_ms": 10})
        assert r.status_code == 422 and r.json()["codigo"] == "RESPUESTA_INVALIDA"
        r = await c.post(f"{base}/respuesta", headers=HE, json={
            "respuestas": {"operador": "suma"}, "tiempo_ms": 3200, "uso_voz": True,
            "eventos": [{"tipo": "opcion_elegida", "valor": "suma", "ms": 3000}],
        })
        assert r.status_code == 200, r.text
        assert r.json()["correcto"] and r.json()["experiencia_ganada"] == 3
        assert (await c.post(f"{base}/respuesta", headers=HE2, json={"respuestas": {}, "tiempo_ms": 1})).status_code == 403

        r = await c.get("/api/nucleo/dominio", headers=HE)
        assert r.status_code == 200
        assert r.json()["experiencia_total"] == 3
        assert r.json()["lecciones"][0]["estado"] == DOMINIO_EN_PROGRESO

        # El profesor consulta, asigna y ajusta
        r = await c.get(f"/api/nucleo/anios/{al}/estudiantes/{est_id}/dominio", headers=HP)
        assert r.status_code == 200 and r.json()["lecciones"][0]["aciertos_recientes"] == 1
        assert (await c.get(f"/api/nucleo/anios/{al}/estudiantes/{est_id}/dominio", headers=HP2)).status_code == 404
        r = await c.post(f"/api/nucleo/anios/{al}/asignaciones", headers=HP,
                         json={"estudiante_id": est_id, "leccion_id": "g1-u03-l02"})
        assert r.status_code == 201, r.text
        asig_id = r.json()["id"]
        assert len((await c.get(f"/api/nucleo/anios/{al}/asignaciones", headers=HP)).json()) == 1
        r = await c.delete(f"/api/nucleo/asignaciones/{asig_id}", headers=HP)
        assert r.status_code == 200 and r.json()["estado"] == "cancelada"
        r = await c.put(f"/api/nucleo/anios/{al}/estudiantes/{est_id}/ajustes", headers=HP, json={"banco_forzado": True})
        assert r.status_code == 200 and r.json()["banco_forzado"] is True
        r = await c.delete(f"/api/nucleo/anios/{al}/lecciones/{L01}", headers=HP)
        assert r.status_code == 200 and r.json()["habilitada"] is False

    async with TestSessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(NucleoEvento)) == 2   # pista + opción
        assert await db.scalar(select(func.count()).select_from(NucleoProblemaSesion)) == 1
        assert await db.scalar(select(func.count()).select_from(NucleoAsignacion)) == 1

"""
Motivación del núcleo (fase 7b): nivel de jugador, bono por dominar (pregunta 15), medallas, mapa y
barras, tienda con nivel de jugador (pregunta 14), mensajes sin DeepSeek en 1.º y 2.º, y
"diagnóstico pendiente" para quien todavía no entró.
"""

import random
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.api.dependencies import get_llm_service
from app.main import app
from app.models.gamification import CategoriaDesbloqueable, Desbloqueable
from app.models.nucleo import (
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    XP_LECCION_DOMINADA,
    NucleoDominio,
    NucleoExperiencia,
    NucleoMedalla,
)
from app.nucleo import motivacion as M
from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.servicios.motivacion import ServicioMotivacion
from app.nucleo.servicios.practica import ServicioPractica
from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.gamification_repository import GamificationRepository
from app.services.curriculo_service import cargar_programa, leer_programa
from app.services.gamification_service import GamificationService
from tests.conftest import TestSessionLocal
from tests.test_nucleo_diagnostico import preparar as preparar_salon
from tests.test_nucleo_practica import Reloj, respuesta_bien, respuesta_mal
from tests.test_organizacion_escolar import _estudiante, _org, _profesor, _salon

P = ParametrosNucleo(diagnostico_activo=False)
L01 = "g1-u03-l01"


# ─── Nivel ───────────────────────────────────────────────────────────────────

def test_nivel_con_curva_creciente():
    # 60·n: 60 para el 2, 120 más para el 3, 180 más para el 4
    assert [M.experiencia_para_nivel(n, P) for n in (1, 2, 3, 4, 5)] == [0, 60, 180, 360, 600]
    assert [M.nivel_de(x, P).nivel for x in (0, 59, 60, 179, 180, 359, 360)] == [1, 1, 2, 2, 3, 3, 4]
    n = M.nivel_de(200, P)
    assert (n.nivel, n.en_el_nivel, n.para_subir) == (3, 20, 180)
    # Coincide con recorrer los niveles uno a uno, y nunca baja al sumar experiencia
    anterior = 1
    for x in range(0, 20000, 7):
        nivel = M.nivel_de(x, P).nivel
        assert M.experiencia_para_nivel(nivel, P) <= x < M.experiencia_para_nivel(nivel + 1, P)
        assert nivel >= anterior
        anterior = nivel


def test_los_valores_del_nivel_son_parametros():
    p = ParametrosNucleo(nivel_base=40, nivel_incremento=0)
    assert [M.nivel_de(x, p).nivel for x in (39, 40, 80, 400)] == [1, 2, 3, 11]
    with pytest.raises(ValueError):
        ParametrosNucleo(nivel_base=0)


def test_bono_completo_la_primera_vez_y_pequeno_al_recuperar():
    assert M.bono_dominio(True, P) == 50
    assert M.bono_dominio(False, P) == 10
    assert M.bono_dominio(False, ParametrosNucleo(xp_bono_recuperada=0.5)) == 25


def test_tienda_reescala_el_requisito():
    assert [M.nivel_tienda(r, P) for r in (1, 2, 3, 4, 5)] == [1, 4, 7, 10, 13]


# ─── Medallas ────────────────────────────────────────────────────────────────

def _lec(i, u, n, caminos=("naturales.suma",)):
    return M.LeccionMapa(i, 1, u, f"Unidad {u}", n, f"Lección {i}", u * 10 + n, caminos)


LECS = [_lec("a", 1, 1), _lec("b", 1, 2), _lec("c", 2, 1), _lec("d", 2, 2, ("naturales.suma", "naturales.resta"))]


def test_catalogo_de_medallas_y_hitos():
    cat = M.catalogo_medallas(LECS, {"a", "b"}, {"naturales.suma": "Suma"}, P)
    ganadas = {(m.tipo, m.clave, m.grado_medalla) for m in M.ganadas(cat)}
    assert ganadas == {
        ("leccion", "a", ""), ("leccion", "b", ""), ("unidad", "g1-u01", ""),
        ("camino", "naturales.suma@1", "bronce"), ("camino", "naturales.suma@1", "plata"),
    }
    oro = next(m for m in cat if m.clave == "naturales.suma@1" and m.grado_medalla == "oro")
    assert (oro.meta, oro.logradas, oro.titulo) == (4, 2, "Suma")
    # La resta tiene una sola lección: bronce, plata y oro piden 1
    resta = [m for m in cat if m.clave == "naturales.resta@1"]
    assert [m.meta for m in resta] == [1, 1, 1]


def test_casillas_de_dominio_sin_restar():
    c = M.casillas_dominio([False, True] * 7, P)
    assert len(c["casillas"]) == 10 and c["aciertos"] == 5 and c["meta"] == 8
    assert M.casillas_dominio([True], P)["casillas"] == [True] + [None] * 9


# ─── Con la base ─────────────────────────────────────────────────────────────

async def practicar(serv, est_id, reloj, n, bien=True):
    """Resuelve n problemas (bien al primer intento, o mal hasta agotar). Devuelve las respuestas."""
    respuestas = []
    while n > 0:
        sesion = await serv.iniciar_sesion(est_id)
        while n > 0 and (ps := await serv.siguiente(est_id, sesion.id)) is not None:
            reloj.avanzar(minutes=1)
            r = await serv.responder(est_id, sesion.id, ps.id, respuesta_bien(ps) if bien else respuesta_mal(ps), 1000)
            while not r["problema_terminado"]:
                r = await serv.responder(est_id, sesion.id, ps.id, respuesta_mal(ps), 1000)
            respuestas.append(r)
            n -= 1
    return respuestas


def celebraciones(respuestas, tipo=None):
    return [c for r in respuestas for c in r.get("celebraciones", []) if tipo is None or c["tipo"] == tipo]


@pytest.mark.db
@pytest.mark.asyncio
async def test_dominar_da_bono_medalla_y_nivel_y_recuperar_da_bono_pequeno():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar_salon(db, habilitar=[L01])
        reloj = Reloj()
        serv = ServicioPractica(db, P, random.Random(1), reloj)
        mot = ServicioMotivacion(db, P, reloj)
        r = await practicar(serv, est.id, reloj, 10)
        reloj.avanzar(days=1)
        r += await practicar(serv, est.id, reloj, 1)
        [dom] = celebraciones(r, "leccion_dominada")
        assert dom["leccion_id"] == L01 and dom["experiencia"] == 50
        medallas = {(c["medalla"]["tipo"], c["medalla"]["grado_medalla"]) for c in celebraciones(r, "medalla")}
        assert medallas == {("leccion", "")}          # bronce de la suma pide 2 de sus 8 lecciones
        assert [c["nivel"] for c in celebraciones(r, "nivel")] == [2]        # 11 + 22 + 50 = 83 ≥ 60
        assert r[-1]["nivel"]["nivel"] == 2
        assert (await mot.nivel(est.id)).experiencia == 11 + 22 + 50

        # Repaso vencido y fallido: vuelve a "en progreso"; el nivel y las medallas se quedan
        reloj.avanzar(days=15)
        await practicar(serv, est.id, reloj, 5, bien=False)
        assert (await db.get(NucleoDominio, (est.id, L01))).estado == DOMINIO_EN_PROGRESO
        assert (await mot.nivel(est.id)).nivel == 2
        n_medallas = len((await db.execute(select(NucleoMedalla))).scalars().all())

        # La recupera: bono pequeño y "la recuperaste", sin medallas repetidas
        r = await practicar(serv, est.id, reloj, 10)
        reloj.avanzar(days=1)
        r += await practicar(serv, est.id, reloj, 2)
        [rec] = celebraciones(r, "leccion_recuperada")
        assert rec["experiencia"] == 10 and not celebraciones(r, "leccion_dominada")
        assert not celebraciones(r, "medalla")
        assert len((await db.execute(select(NucleoMedalla))).scalars().all()) == n_medallas
        bonos = (await db.execute(select(NucleoExperiencia.cantidad, NucleoExperiencia.primera_vez).where(
            NucleoExperiencia.tipo == XP_LECCION_DOMINADA).order_by(NucleoExperiencia.id))).tuples().all()
        assert bonos == [(50, True), (10, False)]


@pytest.mark.db
@pytest.mark.asyncio
async def test_el_provisional_no_da_bono_hasta_confirmarse():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar_salon(db, habilitar=[L01])
        reloj = Reloj()
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=L01, estado=DOMINIO_PROVISIONAL, fecha_inicio=reloj()))
        await db.flush()
        serv = ServicioPractica(db, P, random.Random(2), reloj)
        mot = ServicioMotivacion(db, P, reloj)
        assert (await mot.nivel(est.id)).experiencia == 0
        assert (await mot.medallas(est.id))["obtenidas"] == 0          # provisional: sin medalla
        r = await practicar(serv, est.id, reloj, 10)
        reloj.avanzar(days=1)
        r += await practicar(serv, est.id, reloj, 1)
        assert (await db.get(NucleoDominio, (est.id, L01))).estado == DOMINIO_DOMINADO
        [dom] = celebraciones(r, "leccion_dominada")
        assert dom["experiencia"] == 50


@pytest.mark.db
@pytest.mark.asyncio
async def test_medallas_por_unidad_e_hitos_y_se_ganan_una_sola_vez():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar_salon(db, habilitar=[L01])
        reloj = Reloj()
        mot = ServicioMotivacion(db, P, reloj)
        unidad3 = ["g1-u03-l01", "g1-u03-l02", "g1-u03-l03"]
        for lec in unidad3:                       # dominadas antes de esta fase: solo el evento guardado
            db.add(NucleoExperiencia(estudiante_id=est.id, tipo=XP_LECCION_DOMINADA, cantidad=50, leccion_id=lec,
                                     primera_vez=True, fecha=reloj()))
        await db.flush()
        datos = await mot.medallas(est.id)
        ganadas = {(m["tipo"], m["clave"], m["grado_medalla"]) for m in datos["medallas"] if m["obtenida"]}
        assert {("leccion", x, "") for x in unidad3} <= ganadas
        assert ("unidad", "g1-u03", "") in ganadas
        assert ("camino", "naturales.suma@1", "bronce") in ganadas
        assert datos["total"] > datos["obtenidas"] > 0
        # Aunque la lección vuelva a "en progreso" (o se borre su dominio), la medalla se queda y no se repite
        assert await mot.otorgar_medallas(est.id) == []
        assert len((await db.execute(select(NucleoMedalla))).scalars().all()) == datos["obtenidas"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_progreso_para_el_mapa_y_las_barras():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar_salon(db, habilitar=["g1-u03-l01", "g1-u03-l02"])
        reloj = Reloj()
        db.add_all([
            NucleoDominio(estudiante_id=est.id, leccion_id="g1-u02-l01", estado=DOMINIO_DOMINADO,
                          fecha_inicio=reloj(), fecha_dominio=reloj(), ultima_practica=reloj()),
            NucleoDominio(estudiante_id=est.id, leccion_id="g1-u03-l01", estado=DOMINIO_PROVISIONAL, fecha_inicio=reloj()),
        ])
        db.add(NucleoExperiencia(estudiante_id=est.id, tipo="practica", cantidad=70, fecha=reloj()))
        await db.flush()
        prog = await ServicioMotivacion(db, P, reloj).progreso(est.id)
        assert (prog["nivel"], prog["experiencia_en_nivel"], prog["experiencia_para_subir"]) == (2, 10, 120)
        assert prog["grado"] == 1 and prog["siguiente"] == "g1-u03-l02"
        paradas = {x["leccion_id"]: x for u in prog["unidades"] for x in u["lecciones"]}
        assert len(paradas) == 21
        assert paradas["g1-u02-l01"]["estado"] == "dominado" and paradas["g1-u03-l01"]["estado"] == "provisional"
        assert paradas["g1-u03-l02"]["siguiente"] and paradas["g1-u03-l02"]["casillas"] == [None] * 10
        suma = next(c for c in prog["caminos"] if c["camino"] == "naturales.suma")
        assert suma["provisionales"] == 1
        assert prog["tienda_nivel_por_requisito"] == [1, 4, 7, 10, 13]


@pytest.mark.db
@pytest.mark.asyncio
async def test_la_tienda_usa_el_nivel_de_jugador_en_el_nucleo():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar_salon(db, habilitar=[L01])
        item = Desbloqueable(categoria=CategoriaDesbloqueable.FONDO, nombre="Fondo nivel 2", precio_puntos=10,
                             nivel_minimo_requerido=2)
        db.add(item)
        repo = GamificationRepository(db)
        await repo.agregar_puntos(est.id, 100, "saldo de prueba")
        db.add(NucleoExperiencia(estudiante_id=est.id, tipo="practica", cantidad=200, fecha=Reloj()()))   # nivel 3
        await db.flush()
        servicio = GamificationService(repo, AdaptiveRepository(db))
        with pytest.raises(HTTPException) as e:
            await servicio.comprar_item(est.id, item.id)
        assert e.value.status_code == 403 and "nivel 4" in e.value.detail and "tienes nivel 3" in e.value.detail
        db.add(NucleoExperiencia(estudiante_id=est.id, tipo="practica", cantidad=200, fecha=Reloj()()))   # 400: nivel 4
        await db.flush()
        r = await servicio.comprar_item(est.id, item.id)
        assert r.exito and r.saldo_nuevo == 90
        # Comprar no toca la experiencia
        assert (await ServicioMotivacion(db, P).experiencia(est.id)) == 400


@pytest.mark.db
@pytest.mark.asyncio
async def test_mensajes_sin_deepseek_en_primero_y_pendiente_para_quien_no_entro():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        await db.commit()
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, HP = await _profesor(c, org)
        est_id, HE = await _estudiante(c, org)
        al = (await _salon(c, HP))["anio_lectivo_id"]
        assert (await c.post(f"/api/teachers/salones/{al}/estudiantes/{est_id}", headers=HP)).status_code == 204

        llm = AsyncMock()
        app.dependency_overrides[get_llm_service] = lambda: llm
        try:
            r = await c.get("/api/mensajes/dashboard", headers=HE)
        finally:
            app.dependency_overrides.pop(get_llm_service, None)
        assert r.status_code == 200 and r.json()["generada_llm"] is False and r.json()["texto"]
        assert not llm.method_calls

        # Nunca entró: sin lecciones habilitadas no hay etiqueta; con lecciones, "pendiente"
        assert (await c.get(f"/api/nucleo/anios/{al}/seguimiento", headers=HP)).json()["diagnosticos"] == {}
        assert (await c.put(f"/api/nucleo/anios/{al}/lecciones/{L01}", headers=HP, json={})).status_code == 200
        tabla = (await c.get(f"/api/nucleo/anios/{al}/seguimiento", headers=HP)).json()
        assert tabla["diagnosticos"] == {str(est_id): "pendiente"}

        # Progreso y medallas por la API
        prog = (await c.get("/api/nucleo/progreso", headers=HE)).json()
        assert prog["nivel"] == 1 and prog["grado"] == 1 and len(prog["unidades"]) > 0
        med = (await c.get("/api/nucleo/medallas", headers=HE)).json()
        assert med["obtenidas"] == 0 and med["total"] > 0

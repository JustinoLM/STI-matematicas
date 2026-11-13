"""
Flujo del profesor del núcleo (fase 6a): catálogo del salón, máximo de prioritarias,
prerrequisitos por año lectivo (sin ciclos, sin pisar al recargar el currículo, y usados por el
reparto), ajustes y asignaciones con nombres, y los permisos de las rutas nuevas.
"""

import random

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.nucleo import ZONA_NORMAL, ZONA_REFUERZO
from app.models.school import ANIO_CERRADO, AnioLectivo
from app.nucleo.prerrequisitos import camino_de_ciclo, combinar
from app.nucleo.registro import GENERADORES
from app.nucleo.servicios.habilitacion import (
    CicloPrerrequisitos,
    MaxPrioritarias,
    PrerrequisitoInvalido,
    ServicioHabilitacion,
)
from app.nucleo.servicios.practica import ServicioPractica
from app.services.curriculo_service import cargar_programa, leer_programa
from app.services.school_service import NoEncontrado
from tests.conftest import TestSessionLocal
from tests.salones_helpers import salon_con_estudiantes
from tests.test_nucleo_practica import (
    L01,
    L02,
    GeneradorPruebaL02,
    Reloj,
    preparar,
    sesion_completa,
)
from tests.test_organizacion_escolar import _estudiante, _org, _profesor, _salon

pytestmark = pytest.mark.db

L03 = "g1-u03-l03"   # depende de L02 en el currículo
N11 = "g1-u04-l01"   # Conozcamos los números del 11 al 20 (depende de g1-u02-l01)


class GeneradorPruebaN11(GeneradorPruebaL02):
    leccion_id = N11
    caminos = ("naturales.numeracion",)


@pytest.fixture
def solo_l01_y_n11(monkeypatch):
    """Solo L01 (real) y N11 (de prueba) tienen generador, para controlar el refuerzo."""
    for leccion_id in [k for k in GENERADORES if k != L01]:
        monkeypatch.delitem(GENERADORES, leccion_id)
    monkeypatch.setitem(GENERADORES, N11, GeneradorPruebaN11())


# ─── Reglas puras ────────────────────────────────────────────────────────────

def test_combinar_usa_el_anio_solo_en_las_lecciones_editadas():
    defecto = {"b": ["a"], "c": ["b"]}
    assert combinar(defecto, {"c"}, {"c": ["a"]}) == {"b": ("a",), "c": ("a",)}
    assert combinar(defecto, {"b"}, {}) == {"c": ("b",)}            # editada y vacía
    assert combinar(defecto, set(), {"b": ["x"]}) == {"b": ("a",), "c": ("b",)}


def test_camino_de_ciclo():
    grafo = {"b": ("a",), "c": ("b",)}
    assert camino_de_ciclo(grafo, "a", ["c"]) == ["c", "b", "a"]   # indirecto
    assert camino_de_ciclo(grafo, "a", ["b"]) == ["b", "a"]        # directo
    assert camino_de_ciclo(grafo, "a", ["a"]) == ["a"]
    assert camino_de_ciclo(grafo, "c", ["a"]) is None
    assert camino_de_ciclo(grafo, "b", []) is None
    # Los prerrequisitos actuales de la lección se reemplazan, no cuentan
    assert camino_de_ciclo({"a": ("b",), "b": ("x",)}, "a", ["b"]) is None


# ─── Catálogo y prioritarias ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_catalogo_del_salon():
    async with TestSessionLocal() as db:
        _, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        await hab.habilitar(al.id, prof.id, L01, signo="azar", iconos="nunca", pistas={"3": False}, prioritaria=True)
        catalogo = {lec["id"]: lec for lec in await hab.catalogo(al.id, prof.id)}
        assert len(catalogo) == 168
        l01 = catalogo[L01]
        assert (l01["habilitada"], l01["signo"], l01["iconos"], l01["prioritaria"]) == (True, "azar", "nunca", True)
        assert l01["pistas"] == {"1": True, "2": True, "3": False}
        assert l01["tiene_generador"] and l01["unidad_numero"] == 3
        l02 = catalogo[L02]
        assert (l02["habilitada"], l02["prerrequisitos"], l02["prerrequisitos_editados"]) == (False, [L01], False)
        assert not catalogo["g1-u01-l01"]["incluida"]
        with pytest.raises(NoEncontrado):
            await hab.catalogo(al.id, prof.id + 999)


@pytest.mark.asyncio
async def test_cuarta_prioritaria_responde_max_prioritarias():
    async with TestSessionLocal() as db:
        _, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        for lec in (L01, L02, L03):
            await hab.habilitar(al.id, prof.id, lec, prioritaria=True)
        with pytest.raises(MaxPrioritarias) as e:
            await hab.habilitar(al.id, prof.id, N11, prioritaria=True)
        assert e.value.codigo == "MAX_PRIORITARIAS"
        # Habilitarla sin prioridad sí se puede
        assert (await hab.habilitar(al.id, prof.id, N11)).habilitada


# ─── Prerrequisitos por año lectivo ──────────────────────────────────────────

async def _pres(hab, al, prof, leccion_id):
    return next(lec for lec in await hab.catalogo(al.id, prof.id) if lec["id"] == leccion_id)


@pytest.mark.asyncio
async def test_editar_prerrequisitos_sin_ciclos():
    async with TestSessionLocal() as db:
        _, prof, al = await preparar(db, habilitar=())
        hab = ServicioHabilitacion(db)
        with pytest.raises(CicloPrerrequisitos):            # L02 depende de L01
            await hab.editar_prerrequisitos(al.id, prof.id, L01, [L02])
        with pytest.raises(CicloPrerrequisitos) as e:       # L03 → L02 → L01
            await hab.editar_prerrequisitos(al.id, prof.id, L01, [L03])
        assert "Sumemos y restemos 3 números" in e.value.mensaje
        with pytest.raises(PrerrequisitoInvalido):
            await hab.editar_prerrequisitos(al.id, prof.id, L01, [L01])
        with pytest.raises(PrerrequisitoInvalido):          # no incluida (prenumérica)
            await hab.editar_prerrequisitos(al.id, prof.id, L01, ["g1-u01-l01"])

        # Sin prerrequisitos: se guarda vacío y ya no hay ciclo al revés
        assert await hab.editar_prerrequisitos(al.id, prof.id, L02, []) == []
        l02 = await _pres(hab, al, prof, L02)
        assert (l02["prerrequisitos"], l02["prerrequisitos_programa"], l02["prerrequisitos_editados"]) == ([], [L01], True)
        assert await hab.editar_prerrequisitos(al.id, prof.id, L01, [L02, N11, L02]) == [L02, N11]
        # Ahora restaurar L02 (depende de L01) formaría un ciclo con la edición de L01
        with pytest.raises(CicloPrerrequisitos):
            await hab.restaurar_prerrequisitos(al.id, prof.id, L02)
        await hab.restaurar_prerrequisitos(al.id, prof.id, L01)
        await hab.restaurar_prerrequisitos(al.id, prof.id, L02)
        l02 = await _pres(hab, al, prof, L02)
        assert (l02["prerrequisitos"], l02["prerrequisitos_editados"]) == ([L01], False)


@pytest.mark.asyncio
async def test_recargar_el_curriculo_no_pisa_y_otro_anio_no_cambia():
    async with TestSessionLocal() as db:
        _, prof, al = await preparar(db, habilitar=())
        _, otro = await salon_con_estudiantes(db, profesor=prof)
        hab = ServicioHabilitacion(db)
        await hab.editar_prerrequisitos(al.id, prof.id, L03, [N11])
        await cargar_programa(db, leer_programa())
        assert (await _pres(hab, al, prof, L03))["prerrequisitos"] == [N11]
        assert (await _pres(hab, otro, prof, L03))["prerrequisitos"] == [L02]
        assert (await ServicioPractica(db).grafo()).prerrequisitos[L03] == (L02,)
        assert (await ServicioPractica(db).grafo(al.id)).prerrequisitos[L03] == (N11,)


@pytest.mark.asyncio
async def test_el_refuerzo_usa_el_grafo_del_anio(solo_l01_y_n11):
    """L01 depende en el currículo de g1-u02-l01 (sin generador): fallar L01 no da refuerzo.
    Si el profesor le pone N11 como prerrequisito en el año, el refuerzo sale de N11, y solo en
    ese salón."""
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db)
        est2, _, _ = await preparar(db)
        await ServicioHabilitacion(db).editar_prerrequisitos(al.id, prof.id, L01, [N11])

        for estudiante, con_refuerzo in ((est, True), (est2, False)):
            reloj = Reloj()
            serv = ServicioPractica(db, rng=random.Random(5), reloj=reloj)
            await sesion_completa(serv, estudiante.id, reloj, bien=lambda ps: False)
            plan = [(it["leccion_id"], it["zona"]) for it in (await serv.iniciar_sesion(estudiante.id)).plan]
            if con_refuerzo:
                assert plan.count((N11, ZONA_REFUERZO)) == 2 and plan.count((L01, ZONA_NORMAL)) == 8
            else:
                assert all(lec == L01 for lec, _ in plan)


@pytest.mark.asyncio
async def test_la_extension_usa_el_grafo_del_anio(solo_l01_y_n11):
    """Con L01 dominada, la extensión propone sus sucesores. N11 no depende de L01 en el
    currículo; si el profesor lo edita en el año, pasa a ser paso siguiente."""
    async with TestSessionLocal() as db:
        est, prof, al = await preparar(db)
        serv = ServicioPractica(db)
        antes = await serv.grafo(al.id)
        assert N11 not in antes.sucesores(L01)
        await ServicioHabilitacion(db).editar_prerrequisitos(al.id, prof.id, N11, [L01])
        assert N11 in (await serv.grafo(al.id)).sucesores(L01)
        assert (await serv.foto(est.id, al.id)).grafo.prerrequisitos[N11] == (L01,)


# ─── API y permisos ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_del_profesor_y_permisos():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        await db.commit()

    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, HP = await _profesor(c, org)
        _, HP2 = await _profesor(c, org)
        est_id, HE = await _estudiante(c, org)
        al = (await _salon(c, HP))["anio_lectivo_id"]
        assert (await c.post(f"/api/teachers/salones/{al}/estudiantes/{est_id}", headers=HP)).status_code == 204
        base = f"/api/nucleo/anios/{al}"

        # Catálogo: solo el profesor dueño
        r = await c.get(f"{base}/catalogo", headers=HP)
        assert r.status_code == 200 and len(r.json()) == 168
        assert (await c.get(f"{base}/catalogo", headers=HP2)).status_code == 404
        assert (await c.get(f"{base}/catalogo", headers=HE)).status_code == 403

        # Prioritarias: la cuarta con código propio
        for lec in (L01, L02, L03):
            assert (await c.put(f"{base}/lecciones/{lec}", headers=HP, json={"prioritaria": True})).status_code == 200
        r = await c.put(f"{base}/lecciones/{N11}", headers=HP, json={"prioritaria": True})
        assert (r.status_code, r.json()["codigo"]) == (409, "MAX_PRIORITARIAS")

        # Prerrequisitos
        r = await c.put(f"{base}/lecciones/{L03}/prerrequisitos", headers=HP, json={"prerrequisitos": [N11]})
        assert r.json() == {"leccion_id": L03, "prerrequisitos": [N11], "editados": True}
        r = await c.put(f"{base}/lecciones/{L01}/prerrequisitos", headers=HP, json={"prerrequisitos": [L02]})
        assert (r.status_code, r.json()["codigo"]) == (409, "PRERREQUISITO_CICLO")
        assert (await c.put(f"{base}/lecciones/{L03}/prerrequisitos", headers=HP2,
                            json={"prerrequisitos": []})).status_code == 404
        r = await c.delete(f"{base}/lecciones/{L03}/prerrequisitos", headers=HP)
        assert r.json() == {"leccion_id": L03, "prerrequisitos": [L02], "editados": False}

        # Ajustes y asignaciones con nombres
        assert (await c.get(f"{base}/ajustes", headers=HP)).json() == [{"estudiante_id": est_id, "banco_forzado": False}]
        await c.put(f"{base}/estudiantes/{est_id}/ajustes", headers=HP, json={"banco_forzado": True})
        assert (await c.get(f"{base}/ajustes", headers=HP)).json()[0]["banco_forzado"] is True
        assert (await c.get(f"{base}/ajustes", headers=HP2)).status_code == 404
        r = await c.post(f"{base}/asignaciones", headers=HP, json={"estudiante_id": est_id, "leccion_id": N11})
        assert r.json()["leccion_titulo"] == "Conozcamos los números del 11 al 20"
        assert r.json()["estudiante_nombre"].startswith("Estudiante ")

        # Año cerrado: se consulta, no se cambia
        async with TestSessionLocal() as db:
            (await db.execute(select(AnioLectivo).where(AnioLectivo.id == al))).scalar_one().estado = ANIO_CERRADO
            await db.commit()
        assert (await c.get(f"{base}/catalogo", headers=HP)).status_code == 200
        r = await c.put(f"{base}/lecciones/{L03}/prerrequisitos", headers=HP, json={"prerrequisitos": []})
        assert (r.status_code, r.json()["codigo"]) == (409, "ANIO_CERRADO")
        r = await c.delete(f"{base}/lecciones/{L03}/prerrequisitos", headers=HP)
        assert (r.status_code, r.json()["codigo"]) == (409, "ANIO_CERRADO")

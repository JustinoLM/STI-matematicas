"""
Currículo como datos (fase 2): catálogo de lecciones, caminos y prerrequisitos por defecto.

Cubre:
- el archivo real (curriculo/programa_meduca.yaml) es válido, refleja el programa entero y
  tiene el grafo completo para 1.º y 2.º;
- cada regla de validación, incluido el rechazo de ciclos;
- la carga idempotente y la sincronización (títulos, caminos, prerrequisitos, reordenamiento);
- que una carga inválida o con lecciones retiradas no escribe nada;
- el endpoint de solo lectura (acceso y filtro por grado).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.models.curriculo import (
    CaminoCurricular,
    LeccionCamino,
    LeccionCurricular,
    PrerrequisitoDefecto,
)
from app.services.curriculo_service import (
    ErrorCurriculo,
    buscar_ciclo,
    cargar_programa,
    leer_programa,
    programa_desde_dict,
    validar_programa,
)
from tests.conftest import TestSessionLocal, admin_headers
from tests.test_organizacion_escolar import _estudiante, _org, _profesor

# ─── Programa mínimo de prueba ───────────────────────────────────────────────


def _base() -> dict:
    """1.º y 2.º con cinco lecciones; válido."""
    return {
        "version": 1,
        "caminos": [
            {"id": "naturales.numeracion", "conjunto": "naturales", "habilidad": "numeracion", "nombre": "Numeración"},
            {"id": "naturales.suma", "conjunto": "naturales", "habilidad": "suma", "nombre": "Suma"},
            {"id": "naturales.resta", "conjunto": "naturales", "habilidad": "resta", "nombre": "Resta"},
        ],
        "grados": [
            {"grado": 1, "unidades": [
                {"numero": 1, "titulo": "Entorno", "lecciones": [
                    {"id": "a", "numero": 1, "titulo": "Clasifiquemos", "incluida": False, "motivo": "Prenumérica"},
                ]},
                {"numero": 2, "titulo": "Números", "lecciones": [
                    {"id": "b", "numero": 1, "titulo": "Números del 0 al 10",
                     "caminos": ["naturales.numeracion"], "prerrequisitos": []},
                    {"id": "c", "numero": 2, "titulo": "Sumemos",
                     "caminos": ["naturales.suma"], "prerrequisitos": ["b"]},
                ]},
            ]},
            {"grado": 2, "unidades": [
                {"numero": 1, "titulo": "Más", "lecciones": [
                    {"id": "d", "numero": 1, "titulo": "Restemos",
                     "caminos": ["naturales.resta"], "prerrequisitos": ["c"]},
                    {"id": "e", "numero": 2, "titulo": "Sumemos y restemos",
                     "caminos": ["naturales.suma", "naturales.resta"], "prerrequisitos": ["c", "d"],
                     "presentacion": "cinta"},
                ]},
            ]},
        ],
    }


def _leccion(datos: dict, leccion_id: str) -> dict:
    for g in datos["grados"]:
        for u in g["unidades"]:
            for lec in u["lecciones"]:
                if lec["id"] == leccion_id:
                    return lec
    raise KeyError(leccion_id)


def _errores(datos: dict) -> list[str]:
    return validar_programa(programa_desde_dict(datos))


# ─── Archivo real ────────────────────────────────────────────────────────────

def test_el_archivo_real_es_valido():
    programa = leer_programa()
    assert validar_programa(programa) == []


def test_el_archivo_real_refleja_el_programa_entero():
    programa = leer_programa()
    assert len(programa.lecciones) == 168
    assert {lec.grado for lec in programa.lecciones} == {1, 2, 3, 4, 5, 6}
    assert [lec.orden_programa for lec in programa.lecciones] == list(range(1, 169))
    incluidas = {g: sum(1 for lec in programa.lecciones if lec.grado == g and lec.incluida) for g in (1, 2)}
    assert incluidas == {1: 21, 2: 17}
    for lec in programa.lecciones:
        if not lec.incluida:
            assert lec.motivo_exclusion


def test_el_grafo_de_1_y_2_esta_completo():
    """Toda lección incluida de 1.º y 2.º declara sus prerrequisitos (aunque sea [])."""
    programa = leer_programa()
    sin_grafo = [lec.id for lec in programa.lecciones
                 if lec.grado <= 2 and lec.incluida and lec.prerrequisitos is None]
    assert sin_grafo == []
    # Solo la primera lección numérica de 1.º no tiene prerrequisitos
    raices = [lec.id for lec in programa.lecciones
              if lec.grado <= 2 and lec.incluida and lec.prerrequisitos == []]
    assert raices == ["g1-u02-l01"]


def test_decisiones_del_archivo_real():
    programa = leer_programa()
    assert programa.leccion("g1-u03-l03").caminos == ["naturales.suma", "naturales.resta"]
    assert programa.leccion("g2-u04-l04").presentacion_especial == "cinta"
    assert programa.leccion("g2-u01-l03").incluida is False
    assert programa.leccion("g2-u02-l01").prerrequisitos == ["g1-u07-l01", "g1-u05-l02"]
    tiempo = programa.leccion("g3-u07-l03")
    assert tiempo.parcial and "reloj" in tiempo.nota_parcial
    assert programa.leccion("g5-u02-l02").cubierta_por == "sistema_decimales"
    assert programa.leccion("g6-u03-l01").cubierta_por == "modulo_regla_de_tres"


# ─── Validación ──────────────────────────────────────────────────────────────

def test_el_programa_base_es_valido():
    assert _errores(_base()) == []


def test_rechaza_ids_de_leccion_repetidos():
    datos = _base()
    _leccion(datos, "c")["id"] = "b"
    _leccion(datos, "d")["prerrequisitos"] = ["b"]
    _leccion(datos, "e")["prerrequisitos"] = ["d"]
    assert "Id de lección repetido: b" in _errores(datos)


def test_rechaza_caminos_repetidos():
    datos = _base()
    datos["caminos"].append(dict(datos["caminos"][0]))
    assert any("Camino repetido: naturales.numeracion" in e for e in _errores(datos))


def test_rechaza_numeracion_repetida():
    datos = _base()
    _leccion(datos, "c")["numero"] = 1
    assert any("Numeración repetida: grado 1, unidad 2, lección 1" in e for e in _errores(datos))


def test_rechaza_prerrequisito_inexistente():
    datos = _base()
    _leccion(datos, "c")["prerrequisitos"] = ["no-existe"]
    assert "c: el prerrequisito no-existe no existe" in _errores(datos)


def test_rechaza_prerrequisito_de_un_grado_mayor():
    datos = _base()
    _leccion(datos, "c")["prerrequisitos"] = ["d"]   # c es de 1.º, d de 2.º
    errores = _errores(datos)
    assert any("c (1.º): el prerrequisito d es de un grado mayor (2.º)" in e for e in errores)


def test_rechaza_un_ciclo():
    datos = _base()
    _leccion(datos, "d")["prerrequisitos"] = ["e"]   # d → e → d
    errores = _errores(datos)
    assert any(e.startswith("Ciclo de prerrequisitos:") for e in errores)
    ciclo = next(e for e in errores if e.startswith("Ciclo"))
    assert "d" in ciclo and "e" in ciclo


def test_rechaza_un_ciclo_largo_en_el_mismo_grado():
    datos = _base()
    _leccion(datos, "b")["prerrequisitos"] = ["c"]   # b → c → b
    assert any(e.startswith("Ciclo de prerrequisitos:") for e in _errores(datos))


def test_rechaza_una_leccion_que_se_exige_a_si_misma():
    datos = _base()
    _leccion(datos, "c")["prerrequisitos"] = ["c"]
    assert "Ciclo de prerrequisitos: c → c" in _errores(datos)


def test_buscar_ciclo():
    assert buscar_ciclo({"a": [], "b": ["a"], "c": ["a", "b"]}) is None
    ciclo = buscar_ciclo({"a": ["b"], "b": ["c"], "c": ["a"]})
    assert ciclo[0] == ciclo[-1] and set(ciclo) == {"a", "b", "c"}


def test_rechaza_prerrequisito_no_incluido():
    datos = _base()
    _leccion(datos, "c")["prerrequisitos"] = ["a"]
    assert "c: el prerrequisito a no está incluido en el STI" in _errores(datos)


def test_rechaza_leccion_no_incluida_con_prerrequisitos():
    datos = _base()
    _leccion(datos, "a")["prerrequisitos"] = ["b"]
    assert "a: no está incluida y tiene prerrequisitos" in _errores(datos)


def test_rechaza_leccion_no_incluida_sin_motivo():
    datos = _base()
    del _leccion(datos, "a")["motivo"]
    assert "a: no está incluida y no tiene motivo" in _errores(datos)


def test_rechaza_leccion_incluida_sin_camino():
    datos = _base()
    _leccion(datos, "b")["caminos"] = []
    assert "b: está incluida pero no tiene camino" in _errores(datos)


def test_rechaza_camino_inexistente():
    datos = _base()
    _leccion(datos, "b")["caminos"] = ["naturales.inventado"]
    assert "b: el camino naturales.inventado no existe" in _errores(datos)


def test_rechaza_parcial_sin_nota():
    datos = _base()
    _leccion(datos, "b")["parcial"] = True
    assert "b: es parcial y no tiene nota_parcial" in _errores(datos)


def test_rechaza_presentacion_y_cubierta_no_admitidas():
    datos = _base()
    _leccion(datos, "b")["presentacion"] = "holograma"
    _leccion(datos, "c")["cubierta_por"] = "otro_sistema"
    errores = _errores(datos)
    assert any(e.startswith("b: presentación 'holograma' no admitida") for e in errores)
    assert any(e.startswith("c: cubierta_por 'otro_sistema' no admitido") for e in errores)


def test_junta_todos_los_errores():
    datos = _base()
    _leccion(datos, "b")["caminos"] = []
    _leccion(datos, "c")["prerrequisitos"] = ["no-existe"]
    del _leccion(datos, "a")["motivo"]
    assert len(_errores(datos)) == 3


@pytest.mark.parametrize("cambio", [
    lambda d: _leccion(d, "b").update({"clave_desconocida": 1}),
    lambda d: d["grados"][0].update({"grado": 7}),
    lambda d: _leccion(d, "b").pop("titulo"),
])
def test_rechaza_errores_de_estructura(cambio):
    datos = _base()
    cambio(datos)
    with pytest.raises(ErrorCurriculo) as e:
        programa_desde_dict(datos)
    assert all(err.startswith("Estructura:") for err in e.value.errores)


# ─── Carga en la base ────────────────────────────────────────────────────────

async def _cargar(datos: dict):
    async with TestSessionLocal() as db:
        resumen = await cargar_programa(db, programa_desde_dict(datos))
        await db.commit()
    return resumen


async def _conteos() -> tuple[int, int, int, int]:
    async with TestSessionLocal() as db:
        return tuple([
            (await db.execute(select(func.count()).select_from(modelo))).scalar_one()
            for modelo in (CaminoCurricular, LeccionCurricular, LeccionCamino, PrerrequisitoDefecto)
        ])


async def _prerrequisitos(leccion_id: str) -> set[str]:
    async with TestSessionLocal() as db:
        filas = await db.execute(select(PrerrequisitoDefecto.prerrequisito_id)
                                 .where(PrerrequisitoDefecto.leccion_id == leccion_id))
        return set(filas.scalars())


@pytest.mark.asyncio
async def test_la_carga_es_idempotente():
    primera = await _cargar(_base())
    assert primera.lecciones_creadas == 5 and primera.caminos_creados == 3
    assert primera.prerrequisitos_agregados == 4
    conteos = await _conteos()
    assert conteos == (3, 5, 5, 4)

    segunda = await _cargar(_base())
    assert not segunda.hubo_cambios
    assert await _conteos() == conteos


@pytest.mark.asyncio
async def test_la_carga_del_archivo_real_es_idempotente():
    programa = leer_programa()
    async with TestSessionLocal() as db:
        await cargar_programa(db, programa)
        await db.commit()
    conteos = await _conteos()
    assert conteos[1] == 168
    async with TestSessionLocal() as db:
        resumen = await cargar_programa(db, leer_programa())
        await db.commit()
    assert not resumen.hubo_cambios
    assert await _conteos() == conteos


@pytest.mark.asyncio
async def test_la_carga_actualiza_titulos_caminos_y_prerrequisitos():
    await _cargar(_base())
    datos = _base()
    _leccion(datos, "c")["titulo"] = "Sumemos de forma horizontal"
    _leccion(datos, "e")["prerrequisitos"] = ["d"]           # quita c
    _leccion(datos, "e")["caminos"] = ["naturales.suma"]     # quita resta
    resumen = await _cargar(datos)
    assert resumen.lecciones_actualizadas == 1
    assert resumen.prerrequisitos_quitados == 1
    assert resumen.enlaces_camino_quitados == 1
    assert await _prerrequisitos("e") == {"d"}
    async with TestSessionLocal() as db:
        assert (await db.get(LeccionCurricular, "c")).leccion_titulo == "Sumemos de forma horizontal"


@pytest.mark.asyncio
async def test_la_carga_admite_reordenar_lecciones():
    """Intercambiar dos lecciones choca con las restricciones únicas si no fueran diferibles."""
    await _cargar(_base())
    datos = _base()
    unidad = datos["grados"][0]["unidades"][1]
    b, c = unidad["lecciones"]
    b["numero"], c["numero"] = 2, 1
    c["prerrequisitos"] = []
    b["prerrequisitos"] = ["c"]
    _leccion(datos, "d")["prerrequisitos"] = ["b"]
    unidad["lecciones"] = [c, b]
    resumen = await _cargar(datos)
    assert resumen.lecciones_actualizadas == 2
    async with TestSessionLocal() as db:
        orden = (await db.execute(select(LeccionCurricular.id).order_by(LeccionCurricular.orden_programa))).scalars().all()
    assert orden == ["a", "c", "b", "d", "e"]


@pytest.mark.asyncio
async def test_la_carga_elimina_caminos_que_ya_no_estan():
    await _cargar(_base())
    datos = _base()
    _leccion(datos, "d")["caminos"] = ["naturales.suma"]
    _leccion(datos, "e")["caminos"] = ["naturales.suma"]
    datos["caminos"] = [c for c in datos["caminos"] if c["id"] != "naturales.resta"]
    resumen = await _cargar(datos)
    assert resumen.caminos_eliminados == 1
    assert (await _conteos())[0] == 2


@pytest.mark.asyncio
async def test_una_carga_invalida_no_escribe_nada():
    datos = _base()
    _leccion(datos, "d")["prerrequisitos"] = ["e"]   # ciclo
    with pytest.raises(ErrorCurriculo):
        await _cargar(datos)
    assert await _conteos() == (0, 0, 0, 0)


@pytest.mark.asyncio
async def test_no_borra_lecciones_que_faltan_en_el_archivo():
    await _cargar(_base())
    datos = _base()
    datos["grados"][1]["unidades"][0]["lecciones"].pop()   # quita e
    with pytest.raises(ErrorCurriculo) as e:
        await _cargar(datos)
    assert any("La lección e está en la base pero ya no en el archivo" in err for err in e.value.errores)
    assert (await _conteos())[1] == 5


@pytest.mark.asyncio
async def test_la_base_rechaza_exclusion_sin_motivo():
    """La regla también está en la base (CHECK), no solo en el cargador."""
    from sqlalchemy.exc import IntegrityError

    async with TestSessionLocal() as db:
        db.add(LeccionCurricular(
            id="x", grado=1, unidad_numero=1, unidad_titulo="U", leccion_numero=1,
            leccion_titulo="L", orden_programa=1, incluida=False, motivo_exclusion=None,
        ))
        with pytest.raises(IntegrityError):
            await db.commit()


# ─── Endpoint ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_exige_profesor_o_administrador():
    await _cargar(_base())
    async with AsyncClient(app=app, base_url="http://test") as c:
        assert (await c.get("/api/curriculo/lecciones")).status_code == 401
        org = await _org(c)
        _, h_est = await _estudiante(c, org)
        _, h_prof = await _profesor(c, org)
        assert (await c.get("/api/curriculo/lecciones", headers=h_est)).status_code == 403
        assert (await c.get("/api/curriculo/caminos", headers=h_est)).status_code == 403
        assert (await c.get("/api/curriculo/lecciones", headers=h_prof)).status_code == 200
        assert (await c.get("/api/curriculo/lecciones", headers=admin_headers())).status_code == 200


@pytest.mark.asyncio
async def test_endpoint_lista_el_catalogo_por_grado():
    await _cargar(_base())
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/api/curriculo/lecciones", params={"grado": 2}, headers=admin_headers())
        assert r.status_code == 200
        lecciones = r.json()
        assert [lec["id"] for lec in lecciones] == ["d", "e"]
        e = lecciones[1]
        assert e["caminos"] == ["naturales.suma", "naturales.resta"]
        assert e["prerrequisitos"] == ["c", "d"]          # en el orden del programa
        assert e["presentacion_especial"] == "cinta"
        assert e["grado"] == 2 and e["unidad_titulo"] == "Más" and e["orden_programa"] == 5

        r = await c.get("/api/curriculo/lecciones", headers=admin_headers())
        todas = r.json()
        assert [lec["id"] for lec in todas] == ["a", "b", "c", "d", "e"]
        a = todas[0]
        assert a["incluida"] is False and a["motivo_exclusion"] == "Prenumérica" and a["caminos"] == []

        assert (await c.get("/api/curriculo/lecciones", params={"grado": 7},
                            headers=admin_headers())).status_code == 422


@pytest.mark.asyncio
async def test_endpoint_caminos():
    await _cargar(_base())
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/api/curriculo/caminos", headers=admin_headers())
        assert r.status_code == 200
        assert [cam["id"] for cam in r.json()] == ["naturales.numeracion", "naturales.suma", "naturales.resta"]


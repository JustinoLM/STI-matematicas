"""
Generadores de suma y resta de 1.º grado (fase 5a): U3 L1–L3, U5 L1–L5 y U7 L1–L3.

Pruebas con muchos problemas aleatorios por generador (docs/DISENO_MODULAR.md, sección 4 →
Pruebas): la respuesta correcta es correcta, el banco tiene entre 3 y 4 opciones distintas con
una sola correcta, los números están en el rango de la lección y no hay llevadas ni préstamos
donde no corresponden. Además: signo oculto sin ambigüedad, enunciado e íconos del mismo dato,
vista pública sin respuestas, semirrecta y la clasificación de los errores propios de cada lección.

Se mantiene rápida: los casos aleatorios van en una sola pasada por generador, y los errores se
prueban con problemas armados a mano (sin buscar con el generador).
"""

import itertools
import json
import random
from decimal import Decimal

import pytest

from app.nucleo.lecciones.naturales import comun
from app.nucleo.lecciones.naturales.comun import (
    ANOTAR,
    CALCULO,
    FALTANTE,
    HUECO_FALTANTE,
    HUECO_NUMERO1,
    HUECO_NUMERO2,
    HUECO_OPERADOR,
    HUECO_PASO,
    HUECO_RESULTADO,
    OPCION_DE_SIGNO,
    PASOS,
    RESTA,
    SEMIRRECTA,
    SUMA,
    Planteo,
    lleva,
    parciales,
    pide_prestado,
    valor,
)
from app.nucleo.modos import ModoRespuesta, ModosProblema
from app.nucleo.problema import (
    HuecoNumero,
    HuecoOpcion,
    Numero,
    problema_a_dict,
    problema_desde_dict,
    solucion,
)
from app.nucleo.registro import GENERADORES, obtener_generador

D = Decimal
N = 1200
LECCIONES = sorted(GENERADORES)

COMBINACIONES = [
    ModosProblema(mostrar_signo=s, mostrar_iconos=i, respuesta=r, opciones_banco=o)
    for s, i, r, o in itertools.product(
        (True, False), (True, False), (ModoRespuesta.BANCO, ModoRespuesta.TECLADO), (3, 4)
    )
]
BANCO = ModosProblema(mostrar_signo=True, mostrar_iconos=True, respuesta=ModoRespuesta.BANCO)


def problemas(gen, n=N, semilla=20261112):
    rng = random.Random(semilla)
    for k in range(n):
        yield gen.crear(rng, COMBINACIONES[k % len(COMBINACIONES)])


_CACHE: dict[str, list] = {}


def muestra(leccion_id: str) -> list:
    """Los mismos N problemas para todas las pruebas de una lección (se generan una vez)."""
    if leccion_id not in _CACHE:
        _CACHE[leccion_id] = list(problemas(obtener_generador(leccion_id)))
    return _CACHE[leccion_id]


def armar(leccion_id, nums, ops, forma=CALCULO, modos=BANCO, **kw):
    """Problema con números fijos, armado por la base del generador."""
    gen = obtener_generador(leccion_id)
    return gen._armar(Planteo(list(nums), list(ops), forma=forma, **kw), modos, random.Random(0))


def con_pasos(leccion_id, a, b, op, fn):
    paso, segs = fn(a, b)
    return armar(leccion_id, [a, b], [op], PASOS, paso=paso, segmentos_paso=segs)


# ─── Propiedades de todos los generadores ────────────────────────────────────

@pytest.mark.parametrize("leccion_id", LECCIONES)
def test_muchos_problemas_aleatorios(leccion_id):
    gen = obtener_generador(leccion_id)
    for p in muestra(leccion_id):
        assert gen.en_rango(p), p.datos
        nums, ops = p.datos["numeros"], p.datos["operaciones"]
        assert all(x >= 0 for x in [*nums, *parciales(nums, ops)])

        # La solución es correcta y cada hueco tiene su respuesta
        sol = solucion(p)
        assert gen.corregir(p, sol).correcto

        for h in p.huecos.values():
            if isinstance(h, HuecoNumero) and p.modos.respuesta == ModoRespuesta.BANCO:
                valores = [o.valor for o in h.banco]
                assert len(h.banco) == p.modos.opciones_banco
                assert len(set(valores)) == len(valores)
                assert valores.count(h.correcta) == 1
                assert all(v >= 0 and v == v.to_integral_value() for v in valores)
                # Cada incorrecta con regla se clasifica con esa misma regla
                for o in h.banco:
                    if o.regla is not None:
                        assert gen.clasificar_error(p, h.id, o.valor) == o.regla
            elif isinstance(h, HuecoNumero):
                assert h.banco is None


@pytest.mark.parametrize("leccion_id", LECCIONES)
def test_signo_oculto_sin_ambiguedad(leccion_id):
    """Con el signo oculto, solo la combinación correcta de signos es correcta."""
    gen = obtener_generador(leccion_id)
    vistos = 0
    for p in muestra(leccion_id):
        ops_huecos = [h for h in p.huecos.values() if isinstance(h, HuecoOpcion)]
        if p.modos.mostrar_signo or p.datos["forma"] == ANOTAR:
            continue
        vistos += 1
        assert ops_huecos and all(h.id.startswith(HUECO_OPERADOR) for h in ops_huecos)
        correctas = 0
        for combo in itertools.product(("suma", "resta"), repeat=len(ops_huecos)):
            correctas += gen.corregir(p, {h.id: c for h, c in zip(ops_huecos, combo)}).correcto
        assert correctas == 1
    assert vistos > 0


@pytest.mark.parametrize("leccion_id", LECCIONES)
def test_enunciado_e_iconos_salen_del_mismo_dato(leccion_id):
    for p in muestra(leccion_id)[:300]:
        e = p.enunciado
        assert e["situacion"] and 0 <= e["variante"] < 1000
        visibles = [s.valor for s in p.segmentos if isinstance(s, Numero)]
        # Las cantidades del enunciado son números que se ven en la expresión
        assert all(D(c) in visibles for c in e["cantidades"])
        if p.iconos is not None:
            assert p.modos.mostrar_iconos
            assert p.iconos == e["cantidades"][:len(p.iconos)]
        if not p.modos.mostrar_iconos:
            assert p.iconos is None


@pytest.mark.parametrize("leccion_id", LECCIONES)
def test_json_y_vista_publica(leccion_id):
    for p in muestra(leccion_id)[:200]:
        copia = problema_desde_dict(json.loads(json.dumps(problema_a_dict(p))))
        assert copia == p
        publica = problema_a_dict(p, incluir_respuestas=False)
        assert "datos" not in publica
        assert all("correcta" not in h for h in publica["huecos"])
        assert all("regla" not in o for h in publica["huecos"] for o in h.get("banco", []))
        assert publica["enunciado"] == p.enunciado and publica["presentacion"] == p.presentacion


@pytest.mark.parametrize("leccion_id", LECCIONES)
def test_reglas_y_pistas(leccion_id):
    gen = obtener_generador(leccion_id)
    for regla in gen.reglas_error():
        assert regla.camino in gen.caminos
    assert len({r.codigo for r in gen.reglas_error()}) == len(gen.reglas_error())
    for p in muestra(leccion_id)[:60]:
        textos = [gen.texto_pista(p, n) for n in (1, 2, 3)]
        assert all(textos) and len(set(textos)) == 3


def test_mismo_rng_mismo_problema():
    for leccion_id in LECCIONES:
        gen = obtener_generador(leccion_id)
        a = [problema_a_dict(p) for p in problemas(gen, 20, semilla=7)]
        b = [problema_a_dict(p) for p in problemas(gen, 20, semilla=7)]
        assert a == b


# ─── Rango y forma de cada lección ───────────────────────────────────────────

def _formas(leccion_id):
    return {p.datos["forma"] for p in muestra(leccion_id)}


def test_u3_l1_incluye_el_cero_y_el_hueco_en_medio():
    ps = muestra("g1-u03-l01")
    con_cero = [p for p in ps if 0 in p.datos["numeros"]]
    assert con_cero and all(p.modos.mostrar_signo for p in con_cero)
    assert {sum(p.datos["numeros"]) for p in ps} == set(range(1, 11))
    assert _formas("g1-u03-l01") == {CALCULO, FALTANTE}


def test_u3_l2_resta_hasta_10_con_cero():
    ps = muestra("g1-u03-l02")
    assert max(p.datos["numeros"][0] for p in ps) == 10
    assert any(p.datos["numeros"][1] == 0 for p in ps) and any(valor(p.datos["numeros"], [RESTA]) == 0 for p in ps)
    assert _formas("g1-u03-l02") == {CALCULO, FALTANTE}
    assert {p.enunciado["situacion"] for p in ps} >= {"quitar", "comparar", "faltante_resta"}


@pytest.mark.parametrize("leccion_id, maximo", [("g1-u03-l03", 10), ("g1-u05-l04", 20)])
def test_tres_numeros_los_cuatro_tipos(leccion_id, maximo):
    ps = muestra(leccion_id)
    assert {tuple(p.datos["operaciones"]) for p in ps} == {(SUMA, SUMA), (RESTA, RESTA), (SUMA, RESTA), (RESTA, SUMA)}
    for p in ps:
        assert max([*p.datos["numeros"], *parciales(p.datos["numeros"], p.datos["operaciones"])]) <= maximo
    assert any(len([h for h in p.huecos if h.startswith(HUECO_OPERADOR)]) == 2 for p in ps)


def test_u5_l1_sin_llevar_y_con_pasos():
    for p in muestra("g1-u05-l01"):
        a, b = p.datos["numeros"]
        assert not lleva(a, b) and a + b <= 19 and max(a, b) >= 10
    assert PASOS in _formas("g1-u05-l01")


def test_u5_l2_siempre_completa_el_10():
    for p in muestra("g1-u05-l02"):
        a, b = p.datos["numeros"]
        assert a < 10 and b < 10 and lleva(a, b)
        if p.datos["forma"] == PASOS:
            assert p.huecos[HUECO_PASO].correcta == a + b - 10
    assert _formas("g1-u05-l02") == {CALCULO, PASOS}


def test_u5_l3_con_y_sin_cruzar_la_decena():
    cruza = [pide_prestado(*p.datos["numeros"]) for p in muestra("g1-u05-l03")]
    assert any(cruza) and not all(cruza)
    assert any(p.datos["numeros"][1] == 10 for p in muestra("g1-u05-l03"))


@pytest.mark.parametrize("leccion_id, comprueba", [
    ("g1-u07-l01", lambda a, b: not lleva(a, b) and a + b <= 99),
    ("g1-u07-l02", lambda a, b: not pide_prestado(a, b) and a <= 99),
])
def test_u7_sin_llevar_ni_pedir_prestado(leccion_id, comprueba):
    ps = muestra(leccion_id)
    for p in ps:
        assert comprueba(*p.datos["numeros"])
    assert max(max(p.datos["numeros"]) for p in ps) >= 80   # llega cerca de 99


def test_u7_l2_todos_los_tipos_del_libro():
    assert {p.datos["tipo"] for p in muestra("g1-u07-l02")} == {
        "D0-D0", "unidades_iguales", "decenas_iguales", "DU-D0", "DU-U", "DU-DU"}


# ─── Semirrecta ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("leccion_id, saltos", [("g1-u05-l05", {1}), ("g1-u07-l03", {1, 5, 10})])
def test_semirrecta_presentacion(leccion_id, saltos):
    ps = muestra(leccion_id)
    vistos = set()
    for p in ps:
        pres = p.presentacion
        a, b = p.datos["numeros"]
        op = p.datos["operaciones"][0]
        r = valor([a, b], [op])
        assert pres["tipo"] == "semirrecta" and p.iconos is None
        assert pres["desde"] <= min(a, r) and max(a, r) <= pres["hasta"]
        assert pres["inicio"] == a and pres["salto"] * pres["saltos"] == b
        assert pres["sentido"] == ("derecha" if op == SUMA else "izquierda")
        # La llegada solo se ve cuando hay que anotar la operación
        assert ("llegada" in pres) == (p.datos["forma"] == ANOTAR)
        if p.datos["forma"] == ANOTAR:
            assert pres["llegada"] == r
            assert list(p.huecos) == [HUECO_NUMERO1, HUECO_OPERADOR, HUECO_NUMERO2, HUECO_RESULTADO]
        vistos.add(pres["salto"])
        if pres["salto"] == 5:
            assert a % 5 == 0
        if pres["salto"] < 10 and leccion_id == "g1-u07-l03":
            assert pres["hasta"] - pres["desde"] <= 50   # tramo legible en tablet
    assert vistos == saltos
    assert _formas(leccion_id) == {SEMIRRECTA, ANOTAR}


def test_semirrecta_u7_cruza_decenas():
    assert any(lleva(*p.datos["numeros"]) or pide_prestado(*p.datos["numeros"])
               for p in muestra("g1-u07-l03") if p.datos["operaciones"] in ([SUMA], [RESTA]))


def test_ventana_semirrecta():
    assert comun.ventana_semirrecta(22, 30, 1) == (20, 40)
    assert comun.ventana_semirrecta(90, 55, 5) == (50, 100)
    assert comun.ventana_semirrecta(20, 50, 10) == (0, 100)
    assert comun.ventana_semirrecta(3, 9, 1) == (0, 20)
    with pytest.raises(ValueError):
        comun.semirrecta(5, SUMA, 7, 5, desde=0, hasta=20, etiquetas_cada=1, mostrar_llegada=False)


# ─── Clasificación de errores propios de cada lección ────────────────────────

def clasifica(p, hueco, respuesta):
    return obtener_generador(p.leccion_id).clasificar_error(p, hueco, D(respuesta))


@pytest.mark.parametrize("leccion_id, nums, ops, hueco, respuesta, regla", [
    # U3 L1 y L2: hueco en medio
    ("g1-u03-l01", [7, 3], [SUMA], HUECO_FALTANTE, 10, "naturales.suma.faltante"),
    ("g1-u03-l01", [7, 3], [SUMA], HUECO_FALTANTE, 2, "naturales.suma.conto_uno_menos"),
    ("g1-u03-l02", [8, 5], [RESTA], HUECO_FALTANTE, 11, "naturales.resta.faltante"),
    # U3 L2: resta
    ("g1-u03-l02", [8, 5], [RESTA], HUECO_RESULTADO, 13, "naturales.resta.sumo"),
    ("g1-u03-l02", [8, 5], [RESTA], HUECO_RESULTADO, 4, "naturales.resta.conto_uno_menos"),
    ("g1-u03-l02", [8, 5], [RESTA], HUECO_RESULTADO, 2, "naturales.resta.conto_uno_mas"),
    ("g1-u03-l02", [8, 5], [RESTA], HUECO_RESULTADO, 8, "naturales.resta.copio_numero"),
    # Tres números: 5 + 2 − 3 = 4
    ("g1-u03-l03", [5, 2, 3], [SUMA, RESTA], HUECO_RESULTADO, 7, "naturales.resta.omitio_tercero"),
    ("g1-u03-l03", [5, 2, 3], [SUMA, RESTA], HUECO_RESULTADO, 10, "naturales.resta.sumo"),
    ("g1-u03-l03", [5, 2, 3], [SUMA, RESTA], HUECO_RESULTADO, 0, "naturales.suma.resto"),
    # Dos cifras
    ("g1-u05-l01", [10, 6], [SUMA], HUECO_RESULTADO, 106, "naturales.suma.junto_cifras"),
    ("g1-u07-l01", [32, 20], [SUMA], HUECO_RESULTADO, 34, "naturales.suma.valor_posicional"),
    ("g1-u07-l01", [32, 5], [SUMA], HUECO_RESULTADO, 82, "naturales.suma.valor_posicional"),
    ("g1-u07-l01", [32, 25], [SUMA], HUECO_RESULTADO, 47, "naturales.suma.error_de_decena"),
    ("g1-u07-l02", [34, 20], [RESTA], HUECO_RESULTADO, 32, "naturales.resta.valor_posicional"),
    ("g1-u07-l02", [57, 17], [RESTA], HUECO_RESULTADO, 50, "naturales.resta.error_de_decena"),
    # Cruzar la decena
    ("g1-u05-l03", [13, 9], [RESTA], HUECO_RESULTADO, 16, "naturales.resta.menor_del_mayor"),
    ("g1-u05-l02", [8, 5], [SUMA], HUECO_RESULTADO, 3, "naturales.suma.resto"),
    ("g1-u05-l02", [9, 5], [SUMA], HUECO_RESULTADO, 4, "naturales.suma.resto"),
    ("g1-u05-l02", [9, 6], [SUMA], HUECO_RESULTADO, 5, "naturales.suma.error_de_decena"),
])
def test_clasificacion(leccion_id, nums, ops, hueco, respuesta, regla):
    forma = FALTANTE if hueco == HUECO_FALTANTE else CALCULO
    p = armar(leccion_id, nums, ops, forma)
    r = obtener_generador(leccion_id).corregir(p, {**solucion(p), hueco: str(respuesta)})
    assert not r.correcto and r.huecos[hueco].error == regla


@pytest.mark.parametrize("leccion_id, a, b, op, fn, paso, segmentos, errores", [
    ("g1-u05-l02", 9, 4, SUMA, comun.pasos_completar_10, 3, "9 + 4 = 10 + _ = _",
     {4: "naturales.suma.paso_sumando", 1: "naturales.suma.paso_complemento"}),
    ("g1-u05-l02", 2, 9, SUMA, comun.pasos_completar_10, 1, "2 + 9 = _ + 10 = _",
     {2: "naturales.suma.paso_sumando"}),
    ("g1-u05-l01", 12, 3, SUMA, comun.pasos_separar_10, 5, "12 + 3 = 10 + _ = _",
     {3: "naturales.suma.paso_sumando", 2: "naturales.suma.paso_sumando"}),
    ("g1-u05-l03", 19, 7, RESTA, comun.pasos_resta_hasta_19, 2, "19 − 7 = 10 + _ = _",
     {7: "naturales.resta.paso_incompleto", 9: "naturales.resta.paso_incompleto"}),
    ("g1-u05-l03", 13, 9, RESTA, comun.pasos_resta_hasta_19, 1, "13 − 9 = _ + 3 = _",
     {9: "naturales.resta.paso_incompleto", 6: "naturales.resta.paso_incompleto"}),
])
def test_pasos_de_la_estrategia(leccion_id, a, b, op, fn, paso, segmentos, errores):
    p = con_pasos(leccion_id, a, b, op, fn)
    texto = " ".join(s["valor"] if s["tipo"] == "numero" else s.get("simbolo", "_")
                     for s in problema_a_dict(p)["segmentos"])
    assert texto == segmentos
    assert p.huecos[HUECO_PASO].correcta == paso and p.huecos[HUECO_RESULTADO].correcta == valor([a, b], [op])
    assert list(p.huecos) == [HUECO_PASO, HUECO_RESULTADO]
    gen = obtener_generador(leccion_id)
    assert gen.en_rango(p)
    for respuesta, regla in errores.items():
        assert clasifica(p, HUECO_PASO, respuesta) == regla


def test_semirrecta_errores_de_lectura():
    pres = comun.semirrecta(35, SUMA, 15, 5, desde=30, hasta=60, etiquetas_cada=10, mostrar_llegada=True)
    p = armar("g1-u07-l03", [35, 15], [SUMA], ANOTAR, presentacion=pres)
    assert clasifica(p, HUECO_NUMERO1, 50) == "naturales.suma.semirrecta_al_reves"
    assert clasifica(p, HUECO_NUMERO2, 20) == "naturales.suma.conto_mal_los_saltos"
    assert clasifica(p, HUECO_RESULTADO, 45) == "naturales.suma.conto_mal_los_saltos"
    assert obtener_generador("g1-u07-l03").corregir(p, {HUECO_OPERADOR: "resta", HUECO_NUMERO1: "35",
                                                        HUECO_NUMERO2: "15", HUECO_RESULTADO: "50"}
                                                    ).huecos[HUECO_OPERADOR].error == "naturales.suma.confundio_operacion"


def test_el_signo_oculto_de_tres_numeros_clasifica_por_camino():
    modos = ModosProblema(mostrar_signo=False, respuesta=ModoRespuesta.BANCO)
    p = armar("g1-u03-l03", [5, 2, 3], [SUMA, RESTA], modos=modos)
    assert list(p.huecos) == ["operador", "operador2"]
    r = obtener_generador("g1-u03-l03").corregir(p, {"operador": "resta", "operador2": "suma"})
    assert r.huecos["operador"].error == "naturales.suma.confundio_operacion"
    assert r.huecos["operador2"].error == "naturales.resta.confundio_operacion"
    assert OPCION_DE_SIGNO[RESTA] == "resta"


def test_signos_unicos():
    assert not comun.signos_unicos([5, 0], [SUMA])
    assert comun.signos_unicos([5, 2, 3], [SUMA, RESTA])
    assert not comun.signos_unicos([4, 2, 2], [SUMA, RESTA])    # 4 − 2 + 2 también da 4

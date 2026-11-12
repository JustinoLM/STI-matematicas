"""
Núcleo de práctica (fase 3a): problema genérico, validación de cada tipo de hueco, banco de
opciones, reglas de error, modos y parámetros. Ver docs/DISENO_MODULAR.md, sección 1.
"""

import json
import random
from decimal import Decimal

import pytest

from app.nucleo.banco import armar_banco
from app.nucleo.errores import NO_CLASIFICADO, ReglaError, clasificar
from app.nucleo.modos import (
    ConfigModosLeccion,
    Modo,
    ModoRespuesta,
    ModosProblema,
    resolver_binario,
    resolver_modo_respuesta,
    resolver_modos,
)
from app.nucleo.parametros import ParametrosNucleo, cargar_parametros, parametros_desde_config
from app.nucleo.problema import (
    FraccionFija,
    HuecoCantidad,
    HuecoFraccion,
    HuecoNumero,
    HuecoOpcion,
    Numero,
    Opcion,
    OpcionBanco,
    ProblemaExpresion,
    ProblemaOrdenar,
    RefHueco,
    Simbolo,
    Texto,
    problema_a_dict,
    problema_desde_dict,
    texto_numero,
)
from app.nucleo.validacion import HUECO_ORDEN, RespuestaMalFormada, validar

D = Decimal
MODOS = ModosProblema(mostrar_signo=True, mostrar_iconos=False, respuesta=ModoRespuesta.TECLADO)


def expresion(segmentos, *huecos, datos=None):
    return ProblemaExpresion(
        leccion_id="prueba", generador_version=1, segmentos=segmentos,
        huecos={h.id: h for h in huecos}, modos=MODOS, datos=datos or {},
    )


# ─── Ejemplos de la tabla del diseño ─────────────────────────────────────────

def p_suma():          # 23 + 14 = _
    return expresion([Numero(D(23)), Simbolo("+"), Numero(D(14)), Simbolo("="), RefHueco("r")],
                     HuecoNumero("r", D(37)))


def p_en_medio():      # 1 + _ = 10
    return expresion([Numero(D(1)), Simbolo("+"), RefHueco("x"), Simbolo("="), Numero(D(10))],
                     HuecoNumero("x", D(9)))


def p_secuencia():     # 12, 13, _, 15
    return expresion([Numero(D(12)), Texto(","), Numero(D(13)), Texto(","), RefHueco("x"),
                      Texto(","), Numero(D(15))], HuecoNumero("x", D(14)))


def p_decenas():       # _ decenas y _ unidades (de 47)
    return expresion([RefHueco("d"), Texto("decenas y"), RefHueco("u"), Texto("unidades")],
                     HuecoNumero("d", D(4)), HuecoNumero("u", D(7)))


def p_residuo():       # 17 ÷ 5 = _ residuo _
    return expresion([Numero(D(17)), Simbolo("÷"), Numero(D(5)), Simbolo("="), RefHueco("c"),
                      Texto("residuo"), RefHueco("r")], HuecoNumero("c", D(3)), HuecoNumero("r", D(2)))


def p_operador():      # 8 _ 3 = 5
    return expresion([Numero(D(8)), RefHueco("op"), Numero(D(3)), Simbolo("="), Numero(D(5))],
                     HuecoOpcion("op", (Opcion("suma", "+"), Opcion("resta", "−")), "resta"))


def p_comparar():      # 45 _ 54
    return expresion([Numero(D(45)), RefHueco("rel"), Numero(D(54))],
                     HuecoOpcion("rel", (Opcion("menor", "<"), Opcion("mayor", ">"), Opcion("igual", "=")), "menor"))


def p_tiempo(acepta_sin_normalizar=False):   # 3 h 40 min + 2 h 35 min = _ h _ min
    return expresion([Numero(D(3)), Texto("h"), Numero(D(40)), Texto("min"), Simbolo("+"),
                      Numero(D(2)), Texto("h"), Numero(D(35)), Texto("min"), Simbolo("="), RefHueco("t")],
                     HuecoCantidad("t", ("h", "min"), (D(6), D(15)), factores=(D(60), D(1)),
                                   acepta_sin_normalizar=acepta_sin_normalizar))


def p_fraccion(acepta_equivalente=True):     # ½ + ¼ = _/_
    return expresion([FraccionFija(1, 2), Simbolo("+"), FraccionFija(1, 4), Simbolo("="), RefHueco("f")],
                     HuecoFraccion("f", 3, 4, acepta_equivalente=acepta_equivalente))


TODOS = [p_suma, p_en_medio, p_secuencia, p_decenas, p_residuo, p_operador, p_comparar,
         p_tiempo, p_fraccion]


# ─── Estructura ──────────────────────────────────────────────────────────────

def test_los_ejemplos_del_diseno_se_construyen_y_sobreviven_al_json():
    for fabrica in TODOS:
        p = fabrica()
        d = problema_a_dict(p)
        assert problema_desde_dict(json.loads(json.dumps(d))) == p


def test_ordenar_sobrevive_al_json():
    p = ProblemaOrdenar("prueba", 1, [D(12), D(5), D(9)], ascendente=True, modos=MODOS)
    assert problema_desde_dict(json.loads(json.dumps(problema_a_dict(p)))) == p
    assert p.correcta == [D(5), D(9), D(12)]


def test_los_huecos_quedan_en_el_orden_de_la_expresion():
    p = expresion([RefHueco("b"), Texto("y"), RefHueco("a")], HuecoNumero("a", D(1)), HuecoNumero("b", D(2)))
    assert list(p.huecos) == ["b", "a"]


@pytest.mark.parametrize("segmentos, huecos", [
    ([RefHueco("x")], []),                                     # referencia a un hueco que no existe
    ([Numero(D(1))], [HuecoNumero("x", D(1))]),                # hueco que no aparece
    ([RefHueco("x"), RefHueco("x")], [HuecoNumero("x", D(1))]),  # hueco repetido
])
def test_expresion_inconsistente_se_rechaza(segmentos, huecos):
    with pytest.raises(ValueError):
        expresion(segmentos, *huecos)


def test_huecos_mal_definidos_se_rechazan():
    with pytest.raises(ValueError):
        HuecoOpcion("x", (Opcion("a", "+"),), "b")
    with pytest.raises(ValueError):
        HuecoOpcion("x", (Opcion("a", "+"), Opcion("a", "−")), "a")
    with pytest.raises(ValueError):
        HuecoFraccion("x", 1, 0)
    with pytest.raises(ValueError):
        HuecoCantidad("x", ("h", "min"), (D(1),))
    with pytest.raises(ValueError):
        HuecoCantidad("x", ("h", "min"), (D(1), D(2)), acepta_sin_normalizar=True)


def test_la_vista_publica_no_revela_respuestas():
    p = p_suma()
    p.huecos["r"].banco = [OpcionBanco(D(37)), OpcionBanco(D(36), "naturales.suma.conto_uno_menos"),
                           OpcionBanco(D(38))]
    for fabrica in [lambda: p, *TODOS]:
        publica = problema_a_dict(fabrica(), incluir_respuestas=False)
        texto = json.dumps(publica)
        assert "correcta" not in texto
        assert "regla" not in texto
        assert "datos" not in publica
        assert "numerador" not in json.dumps(publica["huecos"])
    publica = problema_a_dict(p, incluir_respuestas=False)
    assert [o["valor"] for o in publica["huecos"][0]["banco"]] == ["37", "36", "38"]


def test_texto_numero():
    assert texto_numero(D("5")) == "5"
    assert texto_numero(D("2.50")) == "2.5"
    assert texto_numero(D("1E+2")) == "100"
    assert texto_numero(D("0.025")) == "0.025"


# ─── Validación por tipo de hueco ────────────────────────────────────────────

@pytest.mark.parametrize("respuesta, correcta", [
    (37, True), ("37", True), (" 37 ", True), (37.0, True), ("37,0", True), (D("37.00"), True),
    (36, False), ("3.7", False), (-37, False),
])
def test_hueco_numero(respuesta, correcta):
    assert validar(p_suma(), {"r": respuesta}).correcto is correcta


@pytest.mark.parametrize("respuesta", ["", "treinta", None, True, [37], "NaN", "Infinity", {"r": 1}])
def test_hueco_numero_mal_formado(respuesta):
    with pytest.raises(RespuestaMalFormada):
        validar(p_suma(), {"r": respuesta})


def test_hueco_numero_es_exacto_sin_redondear():
    p = expresion([RefHueco("r")], HuecoNumero("r", D("0.1")))
    assert not validar(p, {"r": "0.1004"}).correcto   # el sistema de decimales redondearía a 0.100


def test_varios_huecos_numericos_se_validan_por_separado():
    r = validar(p_residuo(), {"c": 3, "r": 1})
    assert not r.correcto
    assert r.huecos["c"].correcto and not r.huecos["r"].correcto
    assert validar(p_decenas(), {"d": "4", "u": "7"}).correcto
    assert validar(p_en_medio(), {"x": 9}).correcto
    assert validar(p_secuencia(), {"x": 14}).correcto


def test_faltan_o_sobran_huecos():
    with pytest.raises(RespuestaMalFormada):
        validar(p_residuo(), {"c": 3})
    with pytest.raises(RespuestaMalFormada):
        validar(p_suma(), {"r": 37, "otro": 1})
    with pytest.raises(RespuestaMalFormada):
        validar(p_suma(), [37])


def test_hueco_opcion():
    assert validar(p_operador(), {"op": "resta"}).correcto
    assert not validar(p_operador(), {"op": "suma"}).correcto
    assert validar(p_comparar(), {"rel": "menor"}).correcto
    assert not validar(p_comparar(), {"rel": "igual"}).correcto
    for mala in ["−", "multiplicacion", 1, None]:
        with pytest.raises(RespuestaMalFormada):
            validar(p_comparar(), {"rel": mala})


@pytest.mark.parametrize("respuesta, con_equivalentes, sin_equivalentes", [
    ({"numerador": 3, "denominador": 4}, True, True),
    ("3/4", True, True),
    ({"numerador": "6", "denominador": "8"}, True, False),
    ("6/8", True, False),
    ("1/4", False, False),
    ("4/3", False, False),
])
def test_hueco_fraccion(respuesta, con_equivalentes, sin_equivalentes):
    assert validar(p_fraccion(True), {"f": respuesta}).correcto is con_equivalentes
    assert validar(p_fraccion(False), {"f": respuesta}).correcto is sin_equivalentes


@pytest.mark.parametrize("respuesta", ["3/0", "3", "a/4", "3/4/5", {"numerador": 3}, 0.75, "1.5/2", "--3/4"])
def test_hueco_fraccion_mal_formado(respuesta):
    with pytest.raises(RespuestaMalFormada):
        validar(p_fraccion(), {"f": respuesta})


def test_hueco_cantidad():
    assert validar(p_tiempo(), {"t": {"h": 6, "min": 15}}).correcto
    assert validar(p_tiempo(), {"t": [6, "15"]}).correcto
    assert not validar(p_tiempo(), {"t": {"h": 5, "min": 75}}).correcto       # sin normalizar
    assert validar(p_tiempo(True), {"t": {"h": 5, "min": 75}}).correcto       # si el hueco lo acepta
    assert not validar(p_tiempo(True), {"t": {"h": 5, "min": 70}}).correcto
    for mala in [{"h": 6}, {"h": 6, "min": 15, "s": 0}, [6], "6 h 15 min", {"h": "seis", "min": 15}]:
        with pytest.raises(RespuestaMalFormada):
            validar(p_tiempo(), {"t": mala})


def test_ordenar():
    p = ProblemaOrdenar("prueba", 1, [D(12), D(5), D(9)], ascendente=True, modos=MODOS)
    assert validar(p, {HUECO_ORDEN: [5, 9, 12]}).correcto
    assert not validar(p, {HUECO_ORDEN: [12, 9, 5]}).correcto
    desc = ProblemaOrdenar("prueba", 1, [D(12), D(5), D(9)], ascendente=False, modos=MODOS)
    assert validar(desc, {HUECO_ORDEN: ["12", "9", "5"]}).correcto
    for mala in [[5, 9], [5, 9, 13], [5, 9, 12, 12], "5,9,12"]:
        with pytest.raises(RespuestaMalFormada):
            validar(p, {HUECO_ORDEN: mala})
    with pytest.raises(RespuestaMalFormada):
        validar(p, {"otro": [5, 9, 12]})


def test_ordenar_con_numeros_repetidos():
    p = ProblemaOrdenar("prueba", 1, [D(3), D(1), D(3)], ascendente=True, modos=MODOS)
    assert validar(p, {HUECO_ORDEN: [1, 3, 3]}).correcto


def test_en_modo_banco_solo_valen_las_opciones_del_banco():
    p = p_suma()
    p.huecos["r"].banco = [OpcionBanco(D(37)), OpcionBanco(D(36)), OpcionBanco(D(38))]
    assert validar(p, {"r": 37}).correcto
    assert not validar(p, {"r": "36"}).correcto
    with pytest.raises(RespuestaMalFormada):
        validar(p, {"r": 40})


# ─── Reglas de error ─────────────────────────────────────────────────────────

def test_codigo_de_regla_lleva_el_camino():
    with pytest.raises(ValueError):
        ReglaError("conto_uno_menos", "x", lambda p, h: [])
    with pytest.raises(ValueError):
        ReglaError("naturales..x", "x", lambda p, h: [])
    assert ReglaError("naturales.suma.x", "x", lambda p, h: []).camino == "naturales.suma"


def test_clasificar_gana_la_primera_regla():
    reglas = [
        ReglaError("a.b.primera", "", lambda p, h: [D(1), D(2)]),
        ReglaError("a.b.segunda", "", lambda p, h: [D(2), D(3)]),
    ]
    p = p_suma()
    assert clasificar(reglas, p, "r", D(2)) == "a.b.primera"
    assert clasificar(reglas, p, "r", D(3)) == "a.b.segunda"
    assert clasificar(reglas, p, "r", D(9)) == NO_CLASIFICADO


# ─── Banco de opciones ───────────────────────────────────────────────────────

def no_negativo(v):
    return v >= 0


@pytest.mark.parametrize("cantidad", [3, 4])
def test_banco_con_distractores_de_reglas(cantidad):
    rng = random.Random(1)
    distractores = [("x.y.a", D(4)), ("x.y.b", D(6)), ("x.y.c", D(1)), ("x.y.d", D(6))]
    for _ in range(200):
        banco = armar_banco(D(5), distractores, cantidad, rng, no_negativo)
        valores = [o.valor for o in banco]
        assert len(banco) == cantidad
        assert len(set(valores)) == cantidad
        assert valores.count(D(5)) == 1
        correcta = next(o for o in banco if o.valor == D(5))
        assert correcta.regla is None
        assert all(o.regla is not None for o in banco if o.valor != D(5))   # alcanzaron las reglas


def test_banco_completa_con_cercanos_y_respeta_validez():
    rng = random.Random(2)
    # Las reglas no dan nada útil: repetidos, iguales a la correcta o negativos
    distractores = [("x.y.a", D(0)), ("x.y.b", D(-1)), ("x.y.c", D(0))]
    for _ in range(200):
        banco = armar_banco(D(0), distractores, 4, rng, no_negativo)
        valores = sorted(o.valor for o in banco)
        assert valores == [D(0), D(1), D(2), D(3)]
        assert all(o.regla is None for o in banco)


def test_banco_mezcla_la_posicion_de_la_correcta():
    rng = random.Random(3)
    posiciones = {
        [o.valor for o in armar_banco(D(5), [], 3, rng, no_negativo)].index(D(5))
        for _ in range(100)
    }
    assert posiciones == {0, 1, 2}


def test_banco_con_paso_decimal():
    banco = armar_banco(D("0.5"), [], 3, random.Random(4), no_negativo, paso=D("0.1"))
    assert sorted(o.valor for o in banco)[1] == D("0.5")
    assert all(abs(o.valor - D("0.5")) <= D("0.1") for o in banco)


def test_banco_rechaza_cantidades_invalidas():
    with pytest.raises(ValueError):
        armar_banco(D(5), [], 2, random.Random(), no_negativo)
    with pytest.raises(ValueError):
        armar_banco(D(5), [], 5, random.Random(), no_negativo)
    with pytest.raises(ValueError):
        armar_banco(D(-1), [], 3, random.Random(), no_negativo)
    with pytest.raises(ValueError):
        armar_banco(D(0), [], 3, random.Random(), lambda v: v == 0)   # no hay vecinos válidos


# ─── Modos ───────────────────────────────────────────────────────────────────

def test_resolver_binario():
    rng = random.Random(5)
    assert all(resolver_binario(Modo.SIEMPRE, 0.0, rng) for _ in range(50))
    assert not any(resolver_binario(Modo.NUNCA, 1.0, rng) for _ in range(50))
    muestras = [resolver_binario(Modo.AZAR, 0.5, rng) for _ in range(2000)]
    assert 900 < sum(muestras) < 1100
    assert not any(resolver_binario(Modo.AZAR, 0.0, rng) for _ in range(50))


@pytest.mark.parametrize("grado, intermedios, forzado, esperado", [
    (1, False, False, ModoRespuesta.BANCO),
    (2, False, False, ModoRespuesta.BANCO),
    (3, True, False, ModoRespuesta.BANCO),
    (3, False, False, ModoRespuesta.TECLADO),
    (4, True, False, ModoRespuesta.TECLADO),
    (6, True, False, ModoRespuesta.TECLADO),
    (6, False, True, ModoRespuesta.BANCO),      # banco forzado por el profesor
    (3, False, True, ModoRespuesta.BANCO),
])
def test_banco_o_teclado(grado, intermedios, forzado, esperado):
    assert resolver_modo_respuesta(grado, intermedios, forzado, ParametrosNucleo()) == esperado


def test_resolver_modos_respeta_lo_que_admite_la_leccion():
    rng = random.Random(6)
    config = ConfigModosLeccion(signo=Modo.NUNCA, iconos=Modo.SIEMPRE)
    comunes = dict(grado_estudiante=1, banco_forzado=False, banco_en_grados_intermedios=True,
                   parametros=ParametrosNucleo(opciones_banco=4), rng=rng)
    m = resolver_modos(config, admite_signo_oculto=True, admite_iconos=True, **comunes)
    assert (m.mostrar_signo, m.mostrar_iconos, m.respuesta, m.opciones_banco) == (False, True, ModoRespuesta.BANCO, 4)
    m = resolver_modos(config, admite_signo_oculto=False, admite_iconos=False, **comunes)
    assert (m.mostrar_signo, m.mostrar_iconos) == (True, False)


def test_modos_sobreviven_al_dict():
    m = ModosProblema(mostrar_signo=False, mostrar_iconos=True, respuesta=ModoRespuesta.TECLADO, opciones_banco=4)
    assert ModosProblema.desde_dict(json.loads(json.dumps(m.a_dict()))) == m


# ─── Parámetros ──────────────────────────────────────────────────────────────

def test_parametros_por_defecto_validos():
    p = ParametrosNucleo()
    assert p.opciones_banco == 3 and p.intentos_por_problema == 3


@pytest.mark.parametrize("cambio", [
    {"opciones_banco": 2}, {"opciones_banco": 5}, {"proporcion_azar_signo": 1.5},
    {"intentos_por_problema": 0}, {"grado_maximo_banco": 4, "grado_minimo_teclado": 4},
])
def test_parametros_fuera_de_rango(cambio):
    with pytest.raises(ValueError):
        ParametrosNucleo(**cambio)


def test_parametros_desde_config_ignora_lo_invalido():
    p = parametros_desde_config({
        "nucleo.opciones_banco": "4",
        "nucleo.proporcion_azar_signo": "0.25",
        "nucleo.intentos_por_problema": "muchos",    # no es número → valor por defecto
        "nucleo.proporcion_azar_iconos": "7",       # fuera de rango → valor por defecto
        "nucleo.no_existe": "1",
        "ml_ultimo_entrenamiento": "2026-01-01",    # otra clave del sistema
    })
    assert p == ParametrosNucleo(opciones_banco=4, proporcion_azar_signo=0.25)


@pytest.mark.asyncio
async def test_cargar_parametros_de_la_base():
    from app.models.config import ConfiguracionSistema
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        assert await cargar_parametros(db) == ParametrosNucleo()
        db.add(ConfiguracionSistema(clave="nucleo.opciones_banco", valor="4"))
        db.add(ConfiguracionSistema(clave="nucleo.grado_maximo_banco", valor="3"))
        await db.commit()
        assert await cargar_parametros(db) == ParametrosNucleo(opciones_banco=4, grado_maximo_banco=3)

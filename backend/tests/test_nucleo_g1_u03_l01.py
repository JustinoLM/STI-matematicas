"""
Generador de referencia del núcleo: g1-u03-l01 "Sumemos de forma horizontal".

Pruebas con muchos problemas aleatorios (docs/DISENO_MODULAR.md, sección 4 → Pruebas): la
respuesta correcta es correcta, el banco tiene entre 3 y 4 opciones distintas con una sola
correcta, y los números están dentro del rango de la lección. Además: signo oculto, íconos,
clasificación de errores, pistas y el registro de generadores contra el catálogo.
"""

import itertools
import json
import random
from decimal import Decimal

import pytest

from app.nucleo.errores import NO_CLASIFICADO
from app.nucleo.lecciones.naturales.reglas import HUECO_OPERADOR, HUECO_RESULTADO
from app.nucleo.modos import ModoRespuesta, ModosProblema
from app.nucleo.problema import (
    HuecoNumero,
    HuecoOpcion,
    problema_a_dict,
    problema_desde_dict,
)
from app.nucleo.registro import GENERADORES, obtener_generador, tiene_generador
from app.nucleo.validacion import RespuestaMalFormada
from app.services.curriculo_service import leer_programa

D = Decimal
GEN = obtener_generador("g1-u03-l01")
N = 2000

COMBINACIONES = [
    ModosProblema(mostrar_signo=s, mostrar_iconos=i, respuesta=r, opciones_banco=o)
    for s, i, r, o in itertools.product(
        (True, False), (True, False), (ModoRespuesta.BANCO, ModoRespuesta.TECLADO), (3, 4)
    )
]


def problemas(n=N, semilla=20261112):
    rng = random.Random(semilla)
    for k in range(n):
        modos = COMBINACIONES[k % len(COMBINACIONES)]
        yield GEN.crear(rng, modos)


def test_muchos_problemas_aleatorios():
    totales = set()
    for p in problemas():
        a, b = p.datos["sumandos"]
        totales.add(a + b)

        # Rango de la lección
        assert GEN.en_rango(p)
        assert 1 <= a <= 9 and 1 <= b <= 9 and 2 <= a + b <= 10

        # Respuesta correcta
        if p.modos.mostrar_signo:
            hueco = p.huecos[HUECO_RESULTADO]
            assert isinstance(hueco, HuecoNumero) and list(p.huecos) == [HUECO_RESULTADO]
            assert hueco.correcta == a + b
            assert GEN.corregir(p, {HUECO_RESULTADO: a + b}).correcto
        else:
            hueco = p.huecos[HUECO_OPERADOR]
            assert isinstance(hueco, HuecoOpcion) and list(p.huecos) == [HUECO_OPERADOR]
            assert GEN.corregir(p, {HUECO_OPERADOR: "suma"}).correcto
            # Nunca ambiguo: "−" no puede ser correcto (b nunca es 0)
            assert not GEN.corregir(p, {HUECO_OPERADOR: "resta"}).correcto
            assert a - b != a + b

        # Banco: entre 3 y 4 opciones distintas, una sola correcta, todas naturales
        if p.modos.respuesta == ModoRespuesta.BANCO and p.modos.mostrar_signo:
            banco = hueco.banco
            valores = [o.valor for o in banco]
            assert len(banco) == p.modos.opciones_banco
            assert len(set(valores)) == len(valores)
            assert sum(GEN.corregir(p, {HUECO_RESULTADO: v}).correcto for v in valores) == 1
            assert all(v >= 0 and v == v.to_integral_value() for v in valores)
            # Cada incorrecta con regla se clasifica con esa misma regla
            for o in banco:
                if o.regla is not None:
                    assert GEN.clasificar_error(p, HUECO_RESULTADO, o.valor) == o.regla
        else:
            assert getattr(hueco, "banco", None) is None

        # Íconos: una cantidad por sumando, solo si se muestran
        assert p.iconos == ([a, b] if p.modos.mostrar_iconos else None)

    assert totales == set(range(2, 11))   # aparecen todos los totales


def test_las_reglas_de_error_dan_casi_siempre_las_opciones_incorrectas():
    """Con 3 opciones casi nunca hace falta completar con números cercanos."""
    con_cercanos = 0
    total = 0
    for p in problemas(500):
        if p.modos.respuesta == ModoRespuesta.BANCO and p.modos.mostrar_signo and p.modos.opciones_banco == 3:
            total += 1
            con_cercanos += any(o.regla is None and o.valor != p.huecos[HUECO_RESULTADO].correcta
                                for o in p.huecos[HUECO_RESULTADO].banco)
    assert total > 0 and con_cercanos == 0


def test_el_json_conserva_el_problema_y_la_correccion():
    for p in problemas(300):
        copia = problema_desde_dict(json.loads(json.dumps(problema_a_dict(p))))
        assert copia == p
        assert GEN.en_rango(copia)


def test_mismo_rng_mismo_problema():
    a = [problema_a_dict(p) for p in problemas(50, semilla=7)]
    b = [problema_a_dict(p) for p in problemas(50, semilla=7)]
    assert a == b


def test_ambos_modos_de_signo_e_iconos_aparecen():
    vistos = {(p.modos.mostrar_signo, p.modos.mostrar_iconos) for p in problemas(64)}
    assert len(vistos) == 4


# ─── Clasificación de errores ────────────────────────────────────────────────

def problema(a, b, mostrar_signo=True):
    """Problema con sumandos fijos: se buscan con el propio generador."""
    rng = random.Random(0)
    modos = ModosProblema(mostrar_signo=mostrar_signo, respuesta=ModoRespuesta.TECLADO)
    for _ in range(10000):
        p = GEN.crear(rng, modos)
        if p.datos["sumandos"] == [a, b]:
            return p
    raise AssertionError(f"No salió {a} + {b}")


@pytest.mark.parametrize("respuesta, regla", [
    (1, "naturales.suma.resto"),
    (4, "naturales.suma.conto_uno_menos"),
    (6, "naturales.suma.conto_uno_mas"),
    (3, "naturales.suma.copio_sumando"),
    (2, "naturales.suma.copio_sumando"),
    (9, NO_CLASIFICADO),
])
def test_clasificacion_de_errores_en_3_mas_2(respuesta, regla):
    r = GEN.corregir(problema(3, 2), {HUECO_RESULTADO: respuesta})
    assert not r.correcto
    assert r.huecos[HUECO_RESULTADO].error == regla


def test_la_respuesta_correcta_no_lleva_error():
    r = GEN.corregir(problema(3, 2), {HUECO_RESULTADO: 5})
    assert r.correcto and r.huecos[HUECO_RESULTADO].error is None


def test_prioridad_de_reglas_cuando_coinciden():
    # 2 + 1 = 3: 1 es "restó" y también "copió un sumando" → gana restó
    assert GEN.clasificar_error(problema(2, 1), HUECO_RESULTADO, D(1)) == "naturales.suma.resto"
    # 2 es "contó uno de menos" y también "copió un sumando" → gana contó uno de menos
    assert GEN.clasificar_error(problema(2, 1), HUECO_RESULTADO, D(2)) == "naturales.suma.conto_uno_menos"


def test_signo_oculto_clasifica_confundio_operacion():
    r = GEN.corregir(problema(3, 2, mostrar_signo=False), {HUECO_OPERADOR: "resta"})
    assert r.huecos[HUECO_OPERADOR].error == "naturales.suma.confundio_operacion"


def test_respuesta_mal_formada():
    p = problema(3, 2)
    for mala in [{}, {HUECO_RESULTADO: "cinco"}, {HUECO_OPERADOR: "suma"}]:
        with pytest.raises(RespuestaMalFormada):
            GEN.corregir(p, mala)


def test_reglas_pertenecen_a_los_caminos_del_generador():
    for regla in GEN.reglas_error():
        assert regla.camino in GEN.caminos


# ─── Pistas ──────────────────────────────────────────────────────────────────

def test_pistas_de_los_tres_niveles():
    for p in [problema(3, 2), problema(4, 1), problema(3, 2, mostrar_signo=False)]:
        textos = [GEN.texto_pista(p, n) for n in (1, 2, 3)]
        assert all(textos) and len(set(textos)) == 3
    # Nivel 3 es "casi la respuesta": cuenta hasta uno antes del total, sin darlo
    assert GEN.texto_pista(problema(3, 4), 3) == "Cuenta desde 3: 4, 5, 6… ¿qué número sigue?"
    assert "7" not in GEN.texto_pista(problema(3, 4), 3)
    with pytest.raises(ValueError):
        GEN.texto_pista(problema(3, 2), 4)


# ─── Registro contra el catálogo ─────────────────────────────────────────────

def test_registro_contra_el_catalogo():
    programa = leer_programa()
    ids = {lec.id for lec in programa.lecciones}
    assert GENERADORES, "Debe haber al menos el generador de referencia"
    for leccion_id, gen in GENERADORES.items():
        assert leccion_id == gen.leccion_id
        assert leccion_id in ids
        leccion = programa.leccion(leccion_id)
        assert leccion.incluida
        assert set(gen.caminos) == set(leccion.caminos)
    assert tiene_generador("g1-u03-l01")
    assert not tiene_generador("g1-u03-l02")
    with pytest.raises(KeyError):
        obtener_generador("no-existe")

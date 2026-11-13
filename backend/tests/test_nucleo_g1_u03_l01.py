"""
Generador de referencia del núcleo: g1-u03-l01 "Sumemos de forma horizontal".

Pruebas con muchos problemas aleatorios (docs/DISENO_MODULAR.md, sección 4 → Pruebas): la
respuesta correcta es correcta, el banco tiene entre 3 y 4 opciones distintas con una sola
correcta, y los números están dentro del rango de la lección. Además: signo oculto, íconos,
clasificación de errores, pistas y el registro de generadores contra el catálogo.
"""

import random
from decimal import Decimal

import pytest

from app.nucleo.errores import NO_CLASIFICADO
from app.nucleo.lecciones.naturales.reglas import HUECO_OPERADOR, HUECO_RESULTADO
from app.nucleo.modos import ModoRespuesta, ModosProblema
from app.nucleo.problema import (
    problema_a_dict,
    problema_desde_dict,
)
from app.nucleo.registro import GENERADORES, obtener_generador, tiene_generador
from app.nucleo.validacion import RespuestaMalFormada
from app.services.curriculo_service import leer_programa

D = Decimal
GEN = obtener_generador("g1-u03-l01")
N = 2000

# Las propiedades con muchos problemas aleatorios (rango, banco, JSON, íconos y enunciado) están
# en test_nucleo_lecciones_g1.py, para todos los generadores de 1.º. Aquí quedan los casos
# concretos del generador de referencia.


# ─── Clasificación de errores ────────────────────────────────────────────────

def problema(a, b, mostrar_signo=True):
    """Problema con sumandos fijos: se buscan con el propio generador."""
    rng = random.Random(0)
    modos = ModosProblema(mostrar_signo=mostrar_signo, respuesta=ModoRespuesta.TECLADO)
    for _ in range(10000):
        p = GEN.crear(rng, modos)
        if p.datos["numeros"] == [a, b] and p.datos["forma"] == "calculo":
            return p
    raise AssertionError(f"No salió {a} + {b}")


def test_lee_problemas_de_la_version_1():
    """Los problemas guardados con la versión 1 ("sumandos") se siguen corrigiendo y dan pistas."""
    v1 = problema_a_dict(problema(3, 2))
    v1["generador_version"] = 1
    v1["datos"] = {"sumandos": [3, 2]}
    v1.pop("enunciado")
    p = problema_desde_dict(v1)
    assert p.enunciado is None
    assert GEN.corregir(p, {HUECO_RESULTADO: 4}).huecos[HUECO_RESULTADO].error == "naturales.suma.conto_uno_menos"
    assert GEN.texto_pista(p, 3) == "Cuenta desde 3: 4… ¿qué número sigue?"


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
    assert not tiene_generador("g1-u06-l06")   # ordinales: excluida
    with pytest.raises(KeyError):
        obtener_generador("no-existe")

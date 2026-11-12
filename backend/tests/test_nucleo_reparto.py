"""
Reparto de la sesión (fase 3b), como lógica pura: prioridad, debilidad, novedad, repaso,
zona de extensión y zona de refuerzo.

Grafo de prueba:  A → B → C   y   A → D   (B y D dependen de A; C depende de B)
"""

import random
from collections import Counter
from datetime import datetime

import pytest

from app.models.nucleo import (
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    ZONA_EXTENSION,
    ZONA_NORMAL,
    ZONA_PRIORIDAD,
    ZONA_REFUERZO,
    ZONA_REPASO,
)
from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.reparto import (
    Candidata,
    Grafo,
    SinLecciones,
    candidatos_extension,
    candidatos_refuerzo,
    repartir,
)

P = ParametrosNucleo()
GRAFO = Grafo(
    prerrequisitos={"B": ("A",), "C": ("B",), "D": ("A",)},
    orden={"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6},
)


def todas(_):
    return True


def cand(leccion_id, estado="no_iniciado", **kw):
    return Candidata(leccion_id=leccion_id, orden=GRAFO.orden[leccion_id], estado=estado, **kw)


def plan(candidatas, extension=(), refuerzo=(), p=P, semilla=1):
    return repartir(candidatas, list(extension), list(refuerzo), GRAFO, p, random.Random(semilla))


def conteo(items):
    return Counter((it.leccion_id, it.zona) for it in items)


# ─── Básico ──────────────────────────────────────────────────────────────────

def test_sin_candidatas_no_hay_sesion():
    with pytest.raises(SinLecciones):
        plan([])


def test_una_leccion_nueva_ocupa_toda_la_sesion():
    items = plan([cand("A")])
    assert conteo(items) == {("A", ZONA_NORMAL): 10}


def test_el_tamano_de_la_sesion_es_un_parametro():
    assert len(plan([cand("A")], p=ParametrosNucleo(problemas_por_sesion=6))) == 6


# ─── Prioridad ───────────────────────────────────────────────────────────────

def test_las_prioritarias_se_reparten_la_mitad():
    items = plan([cand("A", DOMINIO_EN_PROGRESO, prioritaria=True, precision=0.5, resultados=4),
                  cand("D", DOMINIO_EN_PROGRESO, precision=0.5, resultados=4)])
    assert conteo(items) == {("A", ZONA_PRIORIDAD): 5, ("D", ZONA_NORMAL): 5}


def test_varias_prioritarias_comparten_su_mitad():
    items = plan([cand("A", DOMINIO_EN_PROGRESO, prioritaria=True),
                  cand("D", DOMINIO_EN_PROGRESO, prioritaria=True),
                  cand("E", DOMINIO_EN_PROGRESO)])
    c = conteo(items)
    assert c[("A", ZONA_PRIORIDAD)] + c[("D", ZONA_PRIORIDAD)] == 5
    assert {c[("A", ZONA_PRIORIDAD)], c[("D", ZONA_PRIORIDAD)]} == {2, 3}
    assert c[("E", ZONA_NORMAL)] == 5


def test_la_prioritaria_dominada_cede_su_espacio():
    items = plan([cand("A", DOMINIO_DOMINADO, prioritaria=True),
                  cand("D", DOMINIO_EN_PROGRESO, precision=0.5, resultados=4)])
    c = conteo(items)
    assert not any(z == ZONA_PRIORIDAD for _, z in c)
    assert c == {("D", ZONA_NORMAL): 10}


def test_solo_prioritarias_llenan_la_sesion():
    items = plan([cand("A", DOMINIO_EN_PROGRESO, prioritaria=True)])
    assert conteo(items) == {("A", ZONA_PRIORIDAD): 10}


# ─── Debilidad, novedad y repaso ─────────────────────────────────────────────

def test_la_mas_debil_recibe_mas_problemas():
    items = plan([cand("A", DOMINIO_EN_PROGRESO, precision=0.9, resultados=10),
                  cand("D", DOMINIO_EN_PROGRESO, precision=0.3, resultados=10),
                  cand("E", DOMINIO_EN_PROGRESO, precision=0.6, resultados=10)])
    c = conteo(items)
    assert c[("D", ZONA_NORMAL)] == 4 and c[("E", ZONA_NORMAL)] == 3 and c[("A", ZONA_NORMAL)] == 3


def test_se_introduce_una_sola_leccion_nueva_por_sesion():
    items = plan([cand("A"), cand("E"), cand("F")])
    assert set(conteo(items)) == {("A", ZONA_NORMAL)}
    items = plan([cand("A"), cand("E"), cand("F")], p=ParametrosNucleo(nuevas_por_sesion=2))
    assert set(conteo(items)) == {("A", ZONA_NORMAL), ("E", ZONA_NORMAL)}


def test_una_nueva_espera_a_su_prerrequisito_candidato():
    # B depende de A: mientras A no esté dominada, B no entra (aunque esté habilitada)
    items = plan([cand("A", DOMINIO_EN_PROGRESO, precision=0.5, resultados=5), cand("B")])
    assert set(conteo(items)) == {("A", ZONA_NORMAL)}
    items = plan([cand("A", DOMINIO_DOMINADO), cand("B")])
    assert ("B", ZONA_NORMAL) in conteo(items)


def test_un_prerrequisito_no_habilitado_no_bloquea():
    # C depende de B, pero B no es candidata: el profesor habilitó C directamente
    items = plan([cand("C")])
    assert conteo(items) == {("C", ZONA_NORMAL): 10}


def test_el_repaso_siempre_conserva_un_lugar():
    candidatas = [cand(x, DOMINIO_EN_PROGRESO, precision=0.5, resultados=5) for x in ("A", "D", "E", "F")]
    candidatas.append(cand("B", DOMINIO_DOMINADO, repaso_pendiente=True))
    c = conteo(plan(candidatas))
    assert c[("B", ZONA_REPASO)] >= 1
    assert len({lec for lec, _ in c}) == P.max_lecciones_resto


def test_el_provisional_se_practica_como_repaso():
    c = conteo(plan([cand("A", DOMINIO_PROVISIONAL, repaso_pendiente=True)]))
    assert c == {("A", ZONA_REPASO): 10}


def test_sin_nada_pendiente_se_practican_las_dominadas_mas_antiguas():
    items = plan([
        cand("A", DOMINIO_DOMINADO, ultima_practica=datetime(2026, 11, 10)),
        cand("D", DOMINIO_DOMINADO, ultima_practica=datetime(2026, 11, 1)),
    ], p=ParametrosNucleo(max_lecciones_resto=1))
    assert set(conteo(items)) == {("D", ZONA_NORMAL)}


# ─── Extensión ───────────────────────────────────────────────────────────────

def test_candidatos_de_extension():
    candidatas = [cand("A", DOMINIO_DOMINADO)]
    assert candidatos_extension(candidatas, {"A": DOMINIO_DOMINADO}, set(), todas, GRAFO) == ["B", "D"]
    # No se extiende a lo que ya es candidata, está dominado, en pausa o sin generador
    assert candidatos_extension(candidatas + [cand("B")], {}, set(), todas, GRAFO) == ["D"]
    assert candidatos_extension(candidatas, {"B": DOMINIO_DOMINADO}, set(), todas, GRAFO) == ["D"]
    assert candidatos_extension(candidatas, {}, {"B"}, todas, GRAFO) == ["D"]
    assert candidatos_extension(candidatas, {}, set(), lambda i: i != "D", GRAFO) == ["B"]
    # Solo desde lecciones dominadas
    assert candidatos_extension([cand("A", DOMINIO_EN_PROGRESO)], {}, set(), todas, GRAFO) == []


def test_la_extension_recibe_sus_problemas():
    c = conteo(plan([cand("A", DOMINIO_DOMINADO)], extension=["B", "D"]))
    assert c[("B", ZONA_EXTENSION)] == 1 and c[("D", ZONA_EXTENSION)] == 1
    assert c[("A", ZONA_NORMAL)] == 8
    c = conteo(plan([cand("A", DOMINIO_DOMINADO)], extension=["B"],
                    p=ParametrosNucleo(problemas_extension=1)))
    assert c[("B", ZONA_EXTENSION)] == 1


# ─── Refuerzo ────────────────────────────────────────────────────────────────

def test_candidatos_de_refuerzo():
    falla = cand("C", DOMINIO_EN_PROGRESO, precision=0.4, resultados=6)
    assert candidatos_refuerzo([falla], {}, todas, GRAFO, P) == ["B"]
    # El prerrequisito dominado no necesita refuerzo
    assert candidatos_refuerzo([falla], {"B": DOMINIO_DOMINADO}, todas, GRAFO, P) == []
    # Si el prerrequisito ya es candidata, se practica normalmente
    assert candidatos_refuerzo([falla, cand("B", DOMINIO_EN_PROGRESO)], {}, todas, GRAFO, P) == []
    # Con pocos problemas o buena precisión, no falla
    assert candidatos_refuerzo([cand("C", DOMINIO_EN_PROGRESO, precision=0.4, resultados=4)], {}, todas, GRAFO, P) == []
    assert candidatos_refuerzo([cand("C", DOMINIO_EN_PROGRESO, precision=0.6, resultados=8)], {}, todas, GRAFO, P) == []
    # Sin generador no hay refuerzo
    assert candidatos_refuerzo([falla], {}, lambda i: i != "B", GRAFO, P) == []


def test_el_refuerzo_recibe_sus_problemas():
    c = conteo(plan([cand("C", DOMINIO_EN_PROGRESO, precision=0.4, resultados=6)], refuerzo=["B"]))
    assert c == {("B", ZONA_REFUERZO): 2, ("C", ZONA_NORMAL): 8}


def test_prioridad_refuerzo_y_extension_juntos():
    candidatas = [cand("A", DOMINIO_DOMINADO),
                  cand("C", DOMINIO_EN_PROGRESO, prioritaria=True, precision=0.4, resultados=6),
                  cand("E", DOMINIO_EN_PROGRESO, precision=0.7, resultados=6)]
    c = conteo(plan(candidatas, extension=["D"], refuerzo=["B"]))
    assert c[("C", ZONA_PRIORIDAD)] == 5
    assert c[("B", ZONA_REFUERZO)] == 2
    assert c[("D", ZONA_EXTENSION)] == 2
    assert c[("E", ZONA_NORMAL)] == 1
    assert sum(c.values()) == 10


def test_nunca_empieza_por_extension_ni_refuerzo():
    candidatas = [cand("A", DOMINIO_DOMINADO), cand("C", DOMINIO_EN_PROGRESO, precision=0.4, resultados=6)]
    for semilla in range(200):
        items = plan(candidatas, extension=["D"], refuerzo=["B"], semilla=semilla)
        assert items[0].zona not in (ZONA_EXTENSION, ZONA_REFUERZO)
        assert len(items) == 10


def test_sesion_corta_no_se_pasa_del_tamano():
    p = ParametrosNucleo(problemas_por_sesion=3)
    candidatas = [cand("A", DOMINIO_DOMINADO),
                  cand("C", DOMINIO_EN_PROGRESO, prioritaria=True, precision=0.4, resultados=6)]
    items = plan(candidatas, extension=["D"], refuerzo=["B"], p=p)
    assert len(items) == 3
    assert conteo(items)[("C", ZONA_PRIORIDAD)] == 2

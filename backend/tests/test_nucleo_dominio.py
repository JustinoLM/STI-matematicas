"""
Regla de dominio por lección (fase 3b), como lógica pura: dominar, días distintos, repaso,
volver a "en progreso" y dominio provisional. Todos los valores salen de ParametrosNucleo.
"""

from datetime import datetime, timedelta

import pytest

from app.models.nucleo import (
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    NO_INICIADO,
)
from app.nucleo.dominio import (
    EV_DOMINADA,
    EV_INICIADA,
    EV_PROVISIONAL_RETIRADO,
    EV_REPASO_APROBADO,
    EV_REPASO_FALLIDO,
    EstadoDominio,
    Resultado,
    cumple_regla_dominio,
    evaluar,
    fecha_local,
    repaso_pendiente,
    repaso_vencido,
)
from app.nucleo.parametros import ParametrosNucleo

P = ParametrosNucleo()
LUNES = datetime(2026, 11, 9, 15, 0)   # 10:00 en Panamá


def serie(aciertos: str, inicio: datetime = LUNES, cada: timedelta = timedelta(minutes=1)) -> list[Resultado]:
    """'1101' → resultados con acierto/fallo, uno por minuto desde `inicio`."""
    return [Resultado(c == "1", inicio + cada * k) for k, c in enumerate(aciertos)]


def practicar(e: EstadoDominio, previos: list[Resultado], nuevos: list[Resultado], p=P):
    """Aplica evaluar() a cada resultado nuevo; devuelve el estado final, los eventos y todos los resultados."""
    todos = list(previos)
    eventos = []
    for r in nuevos:
        todos.append(r)
        e, ev = evaluar(e, todos, p)
        eventos.append(ev)
    return e, eventos, todos


def dos_dias(dia1: str, dia2: str) -> list[Resultado]:
    return serie(dia1) + serie(dia2, LUNES + timedelta(days=1))


# ─── Dominar ─────────────────────────────────────────────────────────────────

def test_el_primer_problema_inicia_la_leccion():
    e, ev = evaluar(EstadoDominio(), serie("0"), P)
    assert e.estado == DOMINIO_EN_PROGRESO and ev == EV_INICIADA
    assert e.ultima_practica == LUNES


def test_domina_con_80_por_ciento_en_dos_dias():
    e, eventos, _ = practicar(EstadoDominio(), [], dos_dias("11110", "11101"))
    assert e.estado == DOMINIO_DOMINADO
    assert eventos[-1] == EV_DOMINADA and eventos.count(EV_DOMINADA) == 1
    assert e.fecha_dominio == LUNES + timedelta(days=1, minutes=4)


def test_no_domina_con_menos_de_10_problemas():
    e, _, _ = practicar(EstadoDominio(), [], dos_dias("1111", "11111"))
    assert e.estado == DOMINIO_EN_PROGRESO


def test_no_domina_con_70_por_ciento():
    e, _, _ = practicar(EstadoDominio(), [], dos_dias("11100", "11110"))
    assert e.estado == DOMINIO_EN_PROGRESO


def test_no_domina_en_un_solo_dia_aunque_acierte_todo():
    e, _, todos = practicar(EstadoDominio(), [], serie("1" * 20))
    assert e.estado == DOMINIO_EN_PROGRESO
    assert not cumple_regla_dominio(todos, P)


def test_cuentan_solo_los_ultimos_10():
    # Empezó fallando, pero los últimos 10 (en dos días) son 9 de 10
    e, _, _ = practicar(EstadoDominio(), [], dos_dias("00000" + "11111", "11011"))
    assert e.estado == DOMINIO_DOMINADO


def test_los_dias_son_de_panama():
    # 22:00 y 01:00 en Panamá son dos días distintos; en UTC serían el mismo (03:00 y 06:00)
    a = datetime(2026, 11, 12, 3, 0)
    b = datetime(2026, 11, 12, 6, 0)
    assert a.date() == b.date()
    assert fecha_local(a, P) != fecha_local(b, P)
    resultados = serie("11111", a - timedelta(minutes=5)) + serie("11111", b)
    assert cumple_regla_dominio(resultados, P)


def test_los_valores_son_parametros():
    p = ParametrosNucleo(ventana_dominio=4, umbral_dominio=1.0, dias_distintos_dominio=1)
    e, _, _ = practicar(EstadoDominio(), [], serie("1110"), p)
    assert e.estado == DOMINIO_EN_PROGRESO
    e, _, _ = practicar(EstadoDominio(), [], serie("1111"), p)
    assert e.estado == DOMINIO_DOMINADO


def test_evaluar_exige_el_resultado_nuevo():
    with pytest.raises(ValueError):
        evaluar(EstadoDominio(), [], P)


# ─── Repaso ──────────────────────────────────────────────────────────────────

def dominada():
    e, _, todos = practicar(EstadoDominio(), [], dos_dias("11111", "11111"))
    assert e.estado == DOMINIO_DOMINADO
    return e, todos


def test_repaso_vence_a_las_dos_semanas():
    e, _ = dominada()
    assert not repaso_vencido(e, e.ultima_practica + timedelta(days=13), P)
    assert repaso_vencido(e, e.ultima_practica + timedelta(days=14), P)
    assert repaso_pendiente(e, e.ultima_practica + timedelta(days=14), P)
    assert not repaso_pendiente(e, e.ultima_practica + timedelta(days=1), P)


def test_repaso_fallido_vuelve_a_en_progreso():
    e, todos = dominada()
    inicio = e.ultima_practica + timedelta(days=15)
    e, eventos, _ = practicar(e, todos, serie("10100", inicio))   # 2 de 5 = 40 %
    assert eventos[:4] == [None] * 4 and eventos[4] == EV_REPASO_FALLIDO
    assert e.estado == DOMINIO_EN_PROGRESO and e.repaso_desde is None


def test_repaso_con_60_por_ciento_sigue_dominado():
    e, todos = dominada()
    inicio = e.ultima_practica + timedelta(days=15)
    e, eventos, _ = practicar(e, todos, serie("10101", inicio))   # 3 de 5 = 60 %
    assert eventos[-1] == EV_REPASO_APROBADO
    assert e.estado == DOMINIO_DOMINADO and e.repaso_desde is None


def test_la_ventana_de_repaso_queda_abierta_entre_sesiones():
    e, todos = dominada()
    inicio = e.ultima_practica + timedelta(days=15)
    e, _, todos = practicar(e, todos, serie("10", inicio))
    assert e.repaso_desde == inicio
    assert repaso_pendiente(e, inicio + timedelta(days=1), P)
    e, eventos, _ = practicar(e, todos, serie("000", inicio + timedelta(days=1)))
    assert eventos[-1] == EV_REPASO_FALLIDO


def test_practicar_antes_de_las_dos_semanas_no_abre_repaso():
    e, todos = dominada()
    e, eventos, _ = practicar(e, todos, serie("00000", e.ultima_practica + timedelta(days=13)))
    assert e.estado == DOMINIO_DOMINADO and e.repaso_desde is None
    assert eventos == [None] * 5


def test_despues_del_repaso_fallido_hay_que_volver_a_dominar():
    e, todos = dominada()
    inicio = e.ultima_practica + timedelta(days=15)
    e, _, todos = practicar(e, todos, serie("00000", inicio))
    assert e.estado == DOMINIO_EN_PROGRESO
    e, eventos, _ = practicar(e, todos, serie("1111111111", inicio + timedelta(days=1)))
    assert e.estado == DOMINIO_DOMINADO and EV_DOMINADA in eventos


# ─── Dominio provisional (diagnóstico, fase 7) ───────────────────────────────

def test_provisional_se_retira_con_menos_de_60():
    e = EstadoDominio(estado=DOMINIO_PROVISIONAL)
    assert repaso_pendiente(e, LUNES, P)
    e, eventos, _ = practicar(e, [], serie("01000"))
    assert eventos[-1] == EV_PROVISIONAL_RETIRADO and e.estado == DOMINIO_EN_PROGRESO


def test_provisional_se_confirma_con_la_regla_absoluta():
    e = EstadoDominio(estado=DOMINIO_PROVISIONAL)
    e, eventos, todos = practicar(e, [], serie("11011"))
    assert e.estado == DOMINIO_PROVISIONAL and EV_REPASO_APROBADO not in eventos
    e, eventos, _ = practicar(e, todos, serie("11111", LUNES + timedelta(days=1)))
    assert e.estado == DOMINIO_DOMINADO and eventos[-1] == EV_DOMINADA


def test_no_iniciado_es_el_estado_por_defecto():
    assert EstadoDominio().estado == NO_INICIADO

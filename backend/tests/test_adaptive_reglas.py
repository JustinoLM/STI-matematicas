"""Rachas acumuladas entre sesiones y regla especial del nivel 5."""

from types import SimpleNamespace

import pytest

from app.models.adaptive import PerfilAprendizaje
from app.models.problem import Operacion
from app.services.adaptive_service import AdaptiveService


class _ProblemRepo:
    async def get_problem_by_id(self, problema_id):
        return SimpleNamespace(operacion=Operacion.SUMA)


def _servicio():
    return AdaptiveService(adaptive_repo=None, problem_repo=_ProblemRepo(), problem_service=None)


def _perfil(**kw):
    base = dict(
        nivel_suma=2, nivel_resta=2, nivel_multiplicacion=2, nivel_division=2, nivel_actual=2,
        consecutivas_correctas_suma=0, consecutivas_correctas_resta=0,
        consecutivas_correctas_mult=0, consecutivas_correctas_div=0,
        practicas_perfectas_consecutivas=0,
        perfil_aprendizaje=PerfilAprendizaje.NO_CLASIFICADO,  # umbral 10
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _intentos(*aciertos):
    return [SimpleNamespace(es_correcto=a, problema_id=i) for i, a in enumerate(aciertos)]


@pytest.mark.asyncio
async def test_racha_se_acumula_entre_sesiones_y_sube_nivel():
    srv, perfil = _servicio(), _perfil()
    # 4 sesiones con 3 aciertos seguidos de suma cada una: 3, 6, 9 y 12 ≥ umbral 10
    for esperado in (3, 6, 9):
        cambio = await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(True, True, True))
        assert cambio is None
        assert perfil.consecutivas_correctas_suma == esperado
    cambio = await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(True, True, True))
    assert cambio is not None and cambio.nivel_nuevo == 3
    assert perfil.nivel_suma == 3
    assert perfil.consecutivas_correctas_suma == 0  # se reinicia al subir


@pytest.mark.asyncio
async def test_un_fallo_en_la_sesion_reinicia_la_racha():
    srv, perfil = _servicio(), _perfil(consecutivas_correctas_suma=8)
    # hubo un fallo al principio: solo cuentan los 2 aciertos finales
    await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(False, True, True))
    assert perfil.consecutivas_correctas_suma == 2
    # si el último intento falla, la racha vuelve a 0
    await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(True, True, False))
    assert perfil.consecutivas_correctas_suma == 0


@pytest.mark.asyncio
async def test_el_umbral_mas_alto_ya_es_alcanzable():
    """Umbral 15 (en desarrollo): imposible en una sesión (máx. 14), posible en dos."""
    srv = _servicio()
    perfil = _perfil(perfil_aprendizaje=PerfilAprendizaje.EN_DESARROLLO)
    await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(*[True] * 8))
    assert perfil.nivel_suma == 2
    cambio = await srv._evaluar_nivel_operacion(perfil, Operacion.SUMA, _intentos(*[True] * 7))
    assert cambio is not None and perfil.nivel_suma == 3


def _sesion_perfecta():
    return SimpleNamespace(es_practica_perfecta=True)


@pytest.mark.asyncio
async def test_tres_perfectas_no_llegan_a_nivel_5_si_hay_operaciones_bajas():
    srv = _servicio()
    perfil = _perfil(nivel_actual=4, nivel_suma=4, nivel_resta=4, nivel_multiplicacion=4, nivel_division=3,
                     practicas_perfectas_consecutivas=2)
    cambios = await srv._evaluar_cambios_nivel(perfil, _sesion_perfecta(), [])
    assert perfil.nivel_actual == 4
    assert not any(c.operacion == "nivel_general" for c in cambios)
    assert perfil.practicas_perfectas_consecutivas == 3  # la racha se conserva


@pytest.mark.asyncio
async def test_tres_perfectas_llegan_a_nivel_5_cuando_todas_estan_en_4():
    srv = _servicio()
    perfil = _perfil(nivel_actual=4, nivel_suma=4, nivel_resta=4, nivel_multiplicacion=4, nivel_division=4,
                     practicas_perfectas_consecutivas=2)
    cambios = await srv._evaluar_cambios_nivel(perfil, _sesion_perfecta(), [])
    assert perfil.nivel_actual == 5
    assert any(c.operacion == "nivel_general" and c.nivel_nuevo == 5 for c in cambios)
    assert perfil.practicas_perfectas_consecutivas == 0


@pytest.mark.asyncio
async def test_racha_bloqueada_asciende_cuando_se_cumple_la_regla():
    srv = _servicio()
    perfil = _perfil(nivel_actual=4, nivel_suma=4, nivel_resta=4, nivel_multiplicacion=4, nivel_division=3,
                     practicas_perfectas_consecutivas=3)
    await srv._evaluar_cambios_nivel(perfil, _sesion_perfecta(), [])
    assert perfil.nivel_actual == 4
    perfil.nivel_division = 4
    await srv._evaluar_cambios_nivel(perfil, _sesion_perfecta(), [])
    assert perfil.nivel_actual == 5


@pytest.mark.asyncio
async def test_subidas_por_debajo_del_nivel_5_no_cambian():
    srv = _servicio()
    perfil = _perfil(nivel_actual=2, practicas_perfectas_consecutivas=2)
    await srv._evaluar_cambios_nivel(perfil, _sesion_perfecta(), [])
    assert perfil.nivel_actual == 3

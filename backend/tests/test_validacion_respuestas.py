"""Regla de corrección (redondeo a 3 decimales, ROUND_HALF_UP) y diagnóstico perfecto."""

import re
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.core.respuestas import redondear_respuesta, respuesta_es_correcta
from app.main import app
from app.models.problem import Operacion as O
from app.services.adaptive_service import AdaptiveService
from tests.conftest import TestSessionLocal
from tests.test_pistas_errores_anomalias import _crear_estudiante, _problema_y_sesion


@pytest.mark.parametrize(
    "respuesta,resultado,esperado",
    [
        (D("12.34"), D("12.35"), False),        # difieren en 0.01
        (D("20.8"), D("20.80"), True),          # escritura equivalente
        (D("18.5175"), D("18.518"), True),      # 18.5175 → 18.518 (mitad hacia arriba)
        (D("18.518"), D("18.5175"), True),
        (D("18.5174"), D("18.518"), False),     # 18.5174 → 18.517
        (D("18.5176"), D("18.518"), True),
        (D("0.0005"), D("0.001"), True),
        (D("-1.0005"), D("-1.001"), True),      # mitad hacia arriba en valor absoluto
        (D("8.02"), D("8"), False),
        (D("8"), D("8.000"), True),
        (5, D("5"), True),
        (2.5, D("2.500"), True),
        ("3.1416", D("3.142"), True),
    ],
)
def test_regla_de_redondeo_a_tres_decimales(respuesta, resultado, esperado):
    assert respuesta_es_correcta(respuesta, resultado) is esperado


def test_redondeo_mitad_hacia_arriba():
    assert redondear_respuesta(D("2.6745")) == D("2.675")
    assert redondear_respuesta(D("2.6744")) == D("2.674")
    assert redondear_respuesta(D("20.8")) == D("20.800")


def test_no_queda_ninguna_tolerancia_de_0_01_en_el_backend():
    codigo = "\n".join(p.read_text() for p in Path("app").rglob("*.py"))
    assert not re.search(r"<=\s*(self\.TOLERANCIA|Decimal\(\"0\.01\"\))", codigo)
    assert "TOLERANCIA" not in codigo


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "respuesta,correcta",
    [(18.5175, True), (18.518, True), (18.52, False), (18.5174, False)],
)
async def test_practica_aplica_la_regla(respuesta, correcta):
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, H = await _crear_estudiante(c, "VAL001")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est, O.SUMA, "10", "8.518", "18.518")
        r = await c.post(
            f"/api/practices/{sid}/submit-problem", headers=H,
            json={"problema_id": pid, "respuesta": respuesta, "tiempo_resolucion": 5},
        )
        assert r.status_code == 200, r.text
        assert r.json()["es_correcto"] is correcta


# ─── Diagnóstico ─────────────────────────────────────────────────────────────

class _RepoProblemas:
    OPERACIONES = {1: O.SUMA, 2: O.SUMA, 3: O.RESTA, 4: O.RESTA,
                   5: O.MULTIPLICACION, 6: O.MULTIPLICACION, 7: O.DIVISION, 8: O.DIVISION}

    async def get_problem_by_id(self, problema_id):
        return SimpleNamespace(id=problema_id, operacion=self.OPERACIONES[problema_id],
                               resultado=D("10.5"))


class _RepoAdaptativo:
    def __init__(self):
        self.diagnostico = SimpleNamespace(problemas_ids=list(range(1, 9)), estudiante_id=1)
        self.perfil = SimpleNamespace()

    async def get_diagnostico(self, _id):
        return self.diagnostico

    async def update_diagnostico(self, _d):
        return None

    async def get_or_create_perfil(self, _id):
        return self.perfil

    async def update_perfil(self, _p):
        return None


async def _evaluar(respuestas):
    repo = _RepoAdaptativo()
    svc = AdaptiveService(adaptive_repo=repo, problem_repo=_RepoProblemas(), problem_service=None)
    return await svc.evaluar_diagnostico(1, respuestas), repo


@pytest.mark.asyncio
async def test_diagnostico_perfecto_asigna_nivel_3_a_cada_operacion_y_nivel_actual_4():
    resultado, repo = await _evaluar({i: D("10.5") for i in range(1, 9)})
    assert resultado.perfecto is True
    assert (resultado.nivel_suma, resultado.nivel_resta,
            resultado.nivel_multiplicacion, resultado.nivel_division) == (3, 3, 3, 3)
    assert resultado.nivel_actual == 4
    # queda guardado igual en el diagnóstico y en el perfil
    d, p = repo.diagnostico, repo.perfil
    assert (d.nivel_suma_asignado, d.nivel_resta_asignado, d.nivel_mult_asignado,
            d.nivel_div_asignado, d.nivel_actual_asignado, d.perfecto) == (3, 3, 3, 3, 4, True)
    assert (p.nivel_suma, p.nivel_resta, p.nivel_multiplicacion, p.nivel_division, p.nivel_actual) == (3, 3, 3, 3, 4)


@pytest.mark.asyncio
async def test_operacion_con_2_de_2_recibe_el_mismo_nivel_con_o_sin_puntuacion_perfecta():
    respuestas = {i: D("10.5") for i in range(1, 9)}
    respuestas[8] = D("99")                      # falla un problema de división
    resultado, _ = await _evaluar(respuestas)
    assert resultado.perfecto is False
    assert resultado.nivel_suma == 3             # 2/2, igual que en el caso perfecto
    assert resultado.nivel_division == 2         # 1/2
    assert resultado.nivel_actual == 3           # máximo de las operaciones


@pytest.mark.asyncio
async def test_diagnostico_usa_el_redondeo_a_tres_decimales():
    respuestas = {i: D("10.5") for i in range(1, 9)}
    respuestas[1] = D("10.5004")                 # → 10.500: correcta
    respuestas[2] = D("10.5005")                 # → 10.501: incorrecta
    resultado, _ = await _evaluar(respuestas)
    assert resultado.correctos_por_operacion["suma"] == 1
    assert resultado.nivel_suma == 2

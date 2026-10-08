"""Generación de problemas (ProblemService) y ausencia del router heredado /api/problems."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.problem import Operacion as O
from app.repositories.problem_repository import ProblemRepository
from app.services.problem_service import ProblemService
from tests.conftest import TestSessionLocal, admin_headers


async def _generar(db, op, nivel, n=40, decimales=None, rango=None):
    svc = ProblemService(ProblemRepository(db))
    cfg = ProblemService.NIVEL_CONFIG[nivel]
    rmin, rmax = rango or cfg["rango"]
    dec = cfg["decimales"] if decimales is None else decimales
    return [
        await svc._generate_single_problem(nivel, [op], dec, rmin, rmax) for _ in range(n)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("nivel", [1, 2, 3, 4, 5])
async def test_cada_nivel_respeta_su_configuracion(nivel):
    cfg = ProblemService.NIVEL_CONFIG[nivel]
    async with TestSessionLocal() as db:
        for op in cfg["operaciones"]:
            for p in await _generar(db, op, nivel, n=15):
                assert p.operacion == op and p.nivel_dificultad == nivel
                if op in (O.SUMA, O.RESTA):
                    assert p.numero1 <= cfg["rango"][1] and p.numero2 <= cfg["rango"][1]
                # el producto puede sumar los decimales de los factores (hasta 1 del segundo)
                limite = cfg["decimales"] + (1 if op == O.MULTIPLICACION else 0)
                assert p.cantidad_decimales <= max(limite, 3)


@pytest.mark.asyncio
async def test_resta_nunca_es_negativa():
    async with TestSessionLocal() as db:
        for p in await _generar(db, O.RESTA, 3, n=80):
            assert p.numero1 >= p.numero2 and p.resultado >= 0


@pytest.mark.asyncio
async def test_multiplicacion_limita_los_rangos():
    async with TestSessionLocal() as db:
        for p in await _generar(db, O.MULTIPLICACION, 5, n=60):
            assert p.numero1 <= 50 and p.numero2 <= 20


@pytest.mark.asyncio
@pytest.mark.parametrize("nivel", [1, 3, 4, 5])
async def test_las_divisiones_son_exactas_y_sin_residuo(nivel):
    async with TestSessionLocal() as db:
        for p in await _generar(db, O.DIVISION, nivel, n=60):
            assert p.numero2 > 0
            # generación inversa: dividendo = divisor × cociente exacto (≤ 2 decimales)
            assert p.numero1 / p.numero2 == p.resultado.quantize(Decimal("0.001")) or abs(
                p.numero1 / p.numero2 - p.resultado
            ) < Decimal("0.001")
            assert p.resultado == p.resultado.quantize(Decimal("0.01"))


@pytest.mark.asyncio
async def test_firma_formato_y_reutilizacion():
    async with TestSessionLocal() as db:
        svc = ProblemService(ProblemRepository(db))
        assert svc._generate_signature(O.SUMA, Decimal("12.50"), Decimal("8.30")) == "plus_12.50_8.30"
        assert svc._generate_signature(O.DIVISION, Decimal("9"), Decimal("3")) == "div_9_3"
        primero = await svc._generate_single_problem(1, [O.SUMA], 0, 5, 5)   # siempre 5 + 5
        segundo = await svc._generate_single_problem(1, [O.SUMA], 0, 5, 5)
        assert primero.id == segundo.id and primero.signature == "plus_5_5"


@pytest.mark.asyncio
async def test_el_router_heredado_de_problemas_ya_no_existe():
    async with AsyncClient(app=app, base_url="http://test") as c:
        for metodo, ruta in [("POST", "/api/problems/generate"), ("POST", "/api/problems/submit"),
                             ("POST", "/api/problems/validate"), ("GET", "/api/problems/1")]:
            r = await c.request(metodo, ruta, headers=admin_headers())
            assert r.status_code == 404

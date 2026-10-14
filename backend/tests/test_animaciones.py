"""Animaciones guardadas: sin duplicados aunque dos peticiones lleguen a la vez."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.problem import Operacion, Problema
from app.repositories.animaciones_repository import AnimacionesRepository
from tests.conftest import TestSessionLocal
from tests.test_medallas_sesiones_config import _estudiante


async def _problema(db, firma):
    p = Problema(operacion=Operacion.SUMA, numero1=Decimal("1.5"), numero2=Decimal("2"), resultado=Decimal("3.5"),
                 nivel_dificultad=1, cantidad_decimales=1, signature=firma)
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_guardar_dos_veces_la_misma_animacion_deja_una_sola():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "ANI001")
    async with TestSessionLocal() as db:
        p = await _problema(db, "ani_1")
        await db.commit()
        repo = AnimacionesRepository(db)
        a1, _ = await repo.guardar(est, p.id, "+", "1.5", "2", 1)
        a2, _ = await repo.guardar(est, p.id, "+", "1.5", "2", 1)
        assert a1.id == a2.id
        assert await repo.count(est) == 1


@pytest.mark.asyncio
async def test_si_dos_peticiones_pasan_la_comprobacion_a_la_vez_no_hay_error_ni_duplicado(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "ANI002")
    async with TestSessionLocal() as db:
        p = await _problema(db, "ani_2")
        await db.commit()
        repo = AnimacionesRepository(db)
        primera, _ = await repo.guardar(est, p.id, "+", "1.5", "2", 1)

        # Simula la carrera: la comprobación "¿ya existe?" de la segunda petición aún no ve la primera
        original = repo.get_por_problema
        llamadas = {"n": 0}

        async def _sin_ver_la_primera(estudiante_id, problema_id):
            llamadas["n"] += 1
            return None if llamadas["n"] == 1 else await original(estudiante_id, problema_id)

        monkeypatch.setattr(repo, "get_por_problema", _sin_ver_la_primera)
        segunda, eliminada = await repo.guardar(est, p.id, "+", "1.5", "2", 1)
        assert segunda.id == primera.id and eliminada is None
        assert await repo.count(est) == 1

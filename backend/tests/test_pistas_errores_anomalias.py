"""
Pistas (cobro solo si se genera), tipo de error por intento, detección de
anomalías al completar la práctica y alertas visibles para el profesor.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.adaptive import (
    AlertaEstudiante,
    EstadoSesion,
    PerfilEstudiante,
    SesionPractica,
    TipoAlerta,
)
from app.models.error import ErrorComun, EstudianteError
from app.models.group import EstudianteGrupo, Grupo
from app.models.organization import Organizacion
from app.models.problem import Intento, Operacion, Problema, TipoSesion
from app.models.user import Profesor
from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.gamification_repository import GamificationRepository
from app.repositories.practice_repository import PracticeRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.practice_service import PracticeService
from app.services.teacher_service import TeacherService
from tests.conftest import TestSessionLocal, admin_headers


async def _crear_estudiante(c: AsyncClient, codigo: str, org_id=None):
    r = await c.post(
        "/api/auth/admin/students",
        headers=admin_headers(),
        json={"codigo_estudiante": codigo, "nombre_completo": "Estudiante de prueba",
              "password": "password123", **({"organizacion_id": org_id} if org_id else {})},
    )
    assert r.status_code == 201, r.text
    est_id = r.json()["id"]
    login = await c.post("/api/auth/login", json={"codigo": codigo, "password": "password123"})
    return est_id, {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _problema_y_sesion(db, est_id, op=Operacion.RESTA, a="9", b="4", r="5", n=1):
    db.add(PerfilEstudiante(estudiante_id=est_id))
    await db.flush()
    problemas = []
    for i in range(n):
        p = Problema(operacion=op, numero1=Decimal(a), numero2=Decimal(b), resultado=Decimal(r),
                     nivel_dificultad=1, cantidad_decimales=0, signature=f"sig_{est_id}_{i}")
        db.add(p)
        problemas.append(p)
    await db.flush()
    s = SesionPractica(estudiante_id=est_id, perfil_id=est_id, cantidad_problemas=n,
                       problemas_ids=[p.id for p in problemas], progreso_actual=0,
                       estado=EstadoSesion.EN_PROGRESO, nivel_actual_inicio=1)
    db.add(s)
    await db.flush()
    await GamificationRepository(db).agregar_puntos(est_id, 100, "saldo de prueba")
    await db.commit()
    return problemas[0].id, s.id


async def _saldo(c, H):
    return (await c.get("/api/gamification/balance", headers=H)).json()["puntos_totales"]


# ─── Pistas ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pistas_niveles_1_y_2_funcionan_y_son_gratis():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est_id, H = await _crear_estudiante(c, "PIS001")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est_id)
        for nivel in (1, 2):
            r = await c.post("/api/hints/request", headers=H,
                             json={"sesion_id": sid, "problema_id": pid, "nivel_pista": nivel})
            assert r.status_code == 200, r.text
            assert r.json()["puntos_gastados"] == 0 and r.json()["generada_llm"] is False
        assert await _saldo(c, H) == 100


@pytest.mark.asyncio
async def test_pista_nivel_3_cobra_solo_si_se_genera_y_usa_el_contexto(monkeypatch):
    prompts = []

    async def fake_generate(self, prompt, **kw):
        prompts.append(prompt)
        return "Piensa en cuánto te falta para llegar al total."

    monkeypatch.setattr("app.services.llm_service.LLMService.generate", fake_generate)
    async with AsyncClient(app=app, base_url="http://test") as c:
        est_id, H = await _crear_estudiante(c, "PIS002")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est_id)
            # el estudiante sumó en vez de restar (9 + 4 = 13) antes de pedir la pista
            db.add(Intento(estudiante_id=est_id, problema_id=pid, respuesta_estudiante=Decimal("13"),
                           es_correcto=False, tiempo_resolucion=8, tipo_sesion=TipoSesion.PRACTICA,
                           sesion_id=sid))
            await db.commit()
        r = await c.post("/api/hints/request", headers=H,
                         json={"sesion_id": sid, "problema_id": pid, "nivel_pista": 3})
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["generada_llm"] is True and cuerpo["puntos_gastados"] == 10
        assert await _saldo(c, H) == 90
    assert "13.0" in prompts[0]                      # respuesta incorrecta previa
    assert "operación diferente" in prompts[0]       # tipo de error detectado


@pytest.mark.asyncio
async def test_pista_nivel_3_no_cobra_si_el_llm_falla(monkeypatch):
    async def fallo(self, prompt, **kw):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr("app.services.llm_service.LLMService.generate", fallo)
    async with AsyncClient(app=app, base_url="http://test") as c:
        est_id, H = await _crear_estudiante(c, "PIS003")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est_id)
        r = await c.post("/api/hints/request", headers=H,
                         json={"sesion_id": sid, "problema_id": pid, "nivel_pista": 3})
        assert r.status_code == 200, r.text
        assert r.json()["generada_llm"] is False and r.json()["puntos_gastados"] == 0
        assert await _saldo(c, H) == 100


@pytest.mark.asyncio
async def test_pista_nivel_3_sin_saldo_devuelve_402():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est_id, H = await _crear_estudiante(c, "PIS004")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est_id)
            await GamificationRepository(db).gastar_puntos(est_id, 95, "vaciar")
            await db.commit()
        r = await c.post("/api/hints/request", headers=H,
                         json={"sesion_id": sid, "problema_id": pid, "nivel_pista": 3})
        assert r.status_code == 402


# ─── Tipo de error por intento ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intento_incorrecto_registra_el_tipo_de_error_y_acertar_lo_resuelve():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est_id, H = await _crear_estudiante(c, "ERR001")
        async with TestSessionLocal() as db:
            pid, sid = await _problema_y_sesion(db, est_id)

        r = await c.post(f"/api/practices/{sid}/submit-problem", headers=H,
                         json={"problema_id": pid, "respuesta": 13, "tiempo_resolucion": 5})
        assert r.status_code == 200, r.text
        async with TestSessionLocal() as db:
            filas = (await db.execute(select(EstudianteError, ErrorComun)
                                      .join(ErrorComun, ErrorComun.id == EstudianteError.error_id)
                                      .where(EstudianteError.estudiante_id == est_id))).all()
            assert len(filas) == 1
            assert filas[0][1].codigo == "confundio_operacion" and filas[0][0].resuelto is False

        r = await c.post(f"/api/practices/{sid}/submit-problem", headers=H,
                         json={"problema_id": pid, "respuesta": 5, "tiempo_resolucion": 5})
        assert r.status_code == 200 and r.json()["es_correcto"] is True
        async with TestSessionLocal() as db:
            fila = (await db.execute(select(EstudianteError)
                                     .where(EstudianteError.estudiante_id == est_id))).scalar_one()
            assert fila.resuelto is True and fila.fecha_resolucion is not None


# ─── Anomalías ───────────────────────────────────────────────────────────────

def _servicio(db):
    return PracticeService(PracticeRepository(db), AdaptiveRepository(db), ProblemRepository(db))


async def _sesion_completada(db, est_id, velocidad, ops, perfecta=False, n=6):
    s = SesionPractica(
        estudiante_id=est_id, perfil_id=est_id, cantidad_problemas=n, problemas_ids=[],
        progreso_actual=n, estado=EstadoSesion.COMPLETADA, nivel_actual_inicio=2,
        operaciones_incluidas=ops, velocidad_promedio=Decimal(str(velocidad)),
        es_practica_perfecta=perfecta, problemas_correctos=n if perfecta else 3,
        problemas_incorrectos=0 if perfecta else n - 3,
        fecha_inicio=datetime.utcnow() - timedelta(minutes=10), fecha_fin=datetime.utcnow(),
    )
    db.add(s)
    await db.flush()
    return s


@pytest.mark.asyncio
async def test_velocidad_sospechosa_solo_con_multiplicacion_o_division():
    async with AsyncClient(app=app, base_url="http://test") as c:
        a, _ = await _crear_estudiante(c, "ANO001")
        b, _ = await _crear_estudiante(c, "ANO002")
    async with TestSessionLocal() as db:
        db.add_all([PerfilEstudiante(estudiante_id=a), PerfilEstudiante(estudiante_id=b)])
        await db.flush()
        con_mult = await _sesion_completada(db, a, 2.0, {"×": 4, "+": 2})
        solo_suma = await _sesion_completada(db, b, 2.0, {"+": 3, "-": 3})
        await db.commit()
        srv = _servicio(db)
        assert [x["tipo"] for x in await srv.revisar_sesion_completada(con_mult.id)] == ["velocidad_sospechosa"]
        assert await srv.revisar_sesion_completada(solo_suma.id) == []
        alertas = (await db.execute(select(AlertaEstudiante))).scalars().all()
        assert len(alertas) == 1 and alertas[0].tipo == TipoAlerta.POSIBLE_TRAMPA
        assert alertas[0].estudiante_id == a and alertas[0].severidad == "warning"


@pytest.mark.asyncio
async def test_patron_perfecto_sospechoso():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _crear_estudiante(c, "ANO003")
    async with TestSessionLocal() as db:
        db.add(PerfilEstudiante(estudiante_id=est))
        await db.flush()
        s = await _sesion_completada(db, est, 9.0, {"+": 6}, perfecta=True)
        p = Problema(operacion=Operacion.SUMA, numero1=Decimal(1), numero2=Decimal(1), resultado=Decimal(2),
                     nivel_dificultad=1, cantidad_decimales=0, signature="pp")
        db.add(p)
        await db.flush()
        for i in range(6):  # un intento correcto por problema, todos en 9 s (varianza 0)
            db.add(Intento(estudiante_id=est, problema_id=p.id, respuesta_estudiante=Decimal(2),
                           es_correcto=True, tiempo_resolucion=9, tipo_sesion=TipoSesion.PRACTICA,
                           sesion_id=s.id))
        await db.commit()
        # get_intentos_sesion devuelve 6 intentos del mismo problema → no es "uno por problema":
        # para el patrón se necesitan problemas distintos
        await db.execute(Intento.__table__.delete())
        for i in range(6):
            q = Problema(operacion=Operacion.SUMA, numero1=Decimal(i), numero2=Decimal(1),
                         resultado=Decimal(i + 1), nivel_dificultad=1, cantidad_decimales=0, signature=f"q{i}")
            db.add(q)
            await db.flush()
            db.add(Intento(estudiante_id=est, problema_id=q.id, respuesta_estudiante=Decimal(i + 1),
                           es_correcto=True, tiempo_resolucion=9, tipo_sesion=TipoSesion.PRACTICA,
                           sesion_id=s.id))
        await db.commit()
        res = await _servicio(db).revisar_sesion_completada(s.id)
        assert [x["tipo"] for x in res] == ["patron_perfecto"]
        assert res[0]["severidad"] == "critical"


@pytest.mark.asyncio
async def test_outlier_de_velocidad_respecto_a_la_organizacion():
    async with AsyncClient(app=app, base_url="http://test") as c:
        async with TestSessionLocal() as db:
            org = Organizacion(nombre="Org de prueba", codigo="ORGT1")
            db.add(org)
            await db.commit()
            org_id = org.id
        sospechoso, _ = await _crear_estudiante(c, "ANO004", org_id)
        otros = [(await _crear_estudiante(c, f"REF{i:03d}", org_id))[0] for i in range(12)]
    async with TestSessionLocal() as db:
        db.add_all([PerfilEstudiante(estudiante_id=e) for e in [sospechoso] + otros])
        await db.flush()
        for i, e in enumerate(otros):  # grupo: ~15 s por problema (desviación ≈ 1.2)
            await _sesion_completada(db, e, 12 + (i % 5) * 1.5, {"+": 3, "-": 3})
        rapida = await _sesion_completada(db, sospechoso, 4.0, {"+": 3, "-": 3})  # sin × ni ÷
        normal = await _sesion_completada(db, otros[0], 14.0, {"+": 3, "-": 3})
        await db.commit()
        srv = _servicio(db)
        assert [x["tipo"] for x in await srv.revisar_sesion_completada(rapida.id)] == ["outlier_velocidad"]
        assert await srv.revisar_sesion_completada(normal.id) == []


@pytest.mark.asyncio
async def test_el_profesor_ve_las_alertas_de_posible_trampa():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _crear_estudiante(c, "ANO005")
    async with TestSessionLocal() as db:
        prof = Profesor(codigo_profesor="PROFT01", password_hash="x", tipo_usuario="profesor",
                        nombre_completo="Profesor de prueba")
        db.add(prof)
        await db.flush()
        grupo = Grupo(nombre="G1", profesor_id=prof.id, codigo_grupo="GRP-T1")
        db.add(grupo)
        await db.flush()
        db.add(EstudianteGrupo(estudiante_id=est, grupo_id=grupo.id, activo=True))
        db.add(PerfilEstudiante(estudiante_id=est))
        await db.flush()
        s = await _sesion_completada(db, est, 2.0, {"×": 6})
        await db.commit()
        await _servicio(db).revisar_sesion_completada(s.id)

        alertas = await TeacherService(db).get_alertas(prof.id)
        trampas = [a for a in alertas if a.tipo == TipoAlerta.POSIBLE_TRAMPA]
        assert len(trampas) == 1
        assert trampas[0].estudiante_id == est and trampas[0].severidad == "media"

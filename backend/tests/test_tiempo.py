"""
Fechas y horas (fase 7a): la API manda siempre la hora con zona, y las reglas que dependen del
día usan la fecha de Panamá desde un solo lugar (app/core/tiempo.py).

Fronteras: una práctica a las 11:30 p. m. de Panamá (04:30 UTC del día siguiente) cuenta para ese
día, y el último día de un trimestre dura hasta la medianoche de Panamá.
"""

import importlib
import pkgutil
import typing
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from pydantic import BaseModel, PlainSerializer

import app.schemas as paquete_esquemas
from app.core import tiempo
from app.core.tiempo import FechaHora, a_iso_utc, fecha_local, inicio_dia_local_utc
from app.main import app
from app.models.adaptive import EstadoSesion, PerfilEstudiante, SesionPractica
from app.nucleo import seguimiento as calc
from app.nucleo.dominio import Resultado, cumple_regla_dominio
from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.seguimiento import Periodo
from app.repositories.practice_repository import PracticeRepository
from tests.conftest import TestSessionLocal, admin_headers

# 14 de noviembre, 11:30 p. m. en Panamá = 15 de noviembre, 04:30 UTC
NOCHE_14 = datetime(2026, 11, 15, 4, 30)
# 15 de noviembre, 00:30 a. m. en Panamá = 15 de noviembre, 05:30 UTC
MADRUGADA_15 = datetime(2026, 11, 15, 5, 30)


# ─── Fecha local ─────────────────────────────────────────────────────────────

def test_las_11_y_media_de_la_noche_son_del_mismo_dia_en_panama():
    assert NOCHE_14.date() == date(2026, 11, 15)               # en UTC ya es el 15
    assert fecha_local(NOCHE_14) == date(2026, 11, 14)
    assert fecha_local(MADRUGADA_15) == date(2026, 11, 15)
    # Con zona da lo mismo
    assert fecha_local(NOCHE_14.replace(tzinfo=timezone.utc)) == date(2026, 11, 14)


def test_inicio_del_dia_de_panama_en_utc():
    assert inicio_dia_local_utc(date(2026, 11, 15)) == datetime(2026, 11, 15, 5, 0)


def test_el_dominio_cuenta_la_noche_como_el_mismo_dia():
    """10 aciertos: 5 a las 11:00 p. m. y 5 a las 11:30 p. m. del 14 (Panamá) son UN día, aunque en
    UTC caigan en el 15. Con un día solo no se domina; con la madrugada del 15, sí."""
    p = ParametrosNucleo()
    noche = [Resultado(True, NOCHE_14 - timedelta(minutes=30 - i)) for i in range(5)]
    otra_noche = [Resultado(True, NOCHE_14 + timedelta(minutes=i)) for i in range(5)]
    assert not cumple_regla_dominio(noche + otra_noche, p)
    madrugada = [Resultado(True, MADRUGADA_15 + timedelta(minutes=i)) for i in range(5)]
    assert cumple_regla_dominio(noche + madrugada, p)


def test_el_ultimo_dia_del_trimestre_dura_hasta_la_medianoche_de_panama():
    t3 = Periodo(3, date(2026, 9, 14), date(2026, 11, 14))
    p = ParametrosNucleo()
    assert t3.contiene(NOCHE_14, p)                         # 11:30 p. m. del último día
    assert not t3.contiene(MADRUGADA_15, p)                 # 00:30 a. m. del día siguiente
    # El trimestre vigente cambia a la medianoche de Panamá, no a la de UTC
    ts = [Periodo(1, date(2026, 3, 2), date(2026, 6, 5)), Periodo(2, date(2026, 6, 15), date(2026, 9, 4))]
    assert calc.trimestre_vigente(ts, fecha_local(datetime(2026, 6, 15, 4, 59))) == 1
    assert calc.trimestre_vigente(ts, fecha_local(datetime(2026, 6, 15, 5, 0))) == 2


# ─── Serialización con zona ──────────────────────────────────────────────────

def _esquemas():
    for mod in pkgutil.iter_modules(paquete_esquemas.__path__):
        modulo = importlib.import_module(f"app.schemas.{mod.name}")
        for obj in vars(modulo).values():
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj.__module__ == modulo.__name__:
                yield obj


def _tiene_datetime(anotacion) -> bool:
    if anotacion is datetime:
        return True
    return any(_tiene_datetime(a) for a in typing.get_args(anotacion))


def test_ningun_esquema_usa_datetime_sin_zona():
    sueltos = []
    for esquema in _esquemas():
        for nombre, campo in esquema.model_fields.items():
            if _tiene_datetime(campo.annotation) and not any(isinstance(m, PlainSerializer) for m in campo.metadata):
                # Optional[FechaHora] deja el serializador dentro de la anotación
                if "PlainSerializer" not in repr(campo.annotation):
                    sueltos.append(f"{esquema.__name__}.{nombre}")
    assert sueltos == [], f"Usa FechaHora (app/core/tiempo.py) en: {sueltos}"


def test_fecha_hora_serializa_con_z_y_recibe_horas_con_zona():
    class M(BaseModel):
        f: FechaHora
        g: typing.Optional[FechaHora] = None

    m = M(f=NOCHE_14)
    assert m.model_dump(mode="json") == {"f": "2026-11-15T04:30:00Z", "g": None}
    # Una hora de Panamá con zona se guarda en UTC sin zona
    recibida = M(f="2026-11-14T23:30:00-05:00")
    assert recibida.f == NOCHE_14 and recibida.f.tzinfo is None


def test_los_diccionarios_de_la_api_tambien_llevan_z():
    assert jsonable_encoder({"x": NOCHE_14, "y": [NOCHE_14]}) == {
        "x": "2026-11-15T04:30:00Z", "y": ["2026-11-15T04:30:00Z"]}
    assert a_iso_utc(NOCHE_14.replace(tzinfo=timezone.utc)) == "2026-11-15T04:30:00Z"


def test_reloj_fijo_solo_fuera_de_produccion(monkeypatch):
    monkeypatch.setenv("STI_RELOJ_FIJO", "2026-11-14T23:30:00-05:00")
    monkeypatch.setattr(tiempo.settings, "ENVIRONMENT", "development")
    assert tiempo.ahora_utc() == NOCHE_14 and tiempo.hoy_local() == date(2026, 11, 14)
    monkeypatch.setattr(tiempo.settings, "ENVIRONMENT", "production")
    assert tiempo.ahora_utc() != NOCHE_14


# ─── Con la base ─────────────────────────────────────────────────────────────

@pytest.mark.db
@pytest.mark.asyncio
async def test_la_api_devuelve_horas_con_z():
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.post("/api/auth/admin/students", headers=admin_headers(),
                         json={"codigo_estudiante": "ZONA01", "nombre_completo": "Estudiante Zona",
                               "password": "password123"})
        assert r.status_code == 201, r.text
        login = await c.post("/api/auth/login", json={"codigo": "ZONA01", "password": "password123"})
        r = await c.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
        assert r.status_code == 200, r.text
        assert r.json()["fecha_creacion"].endswith("Z")


@pytest.mark.db
@pytest.mark.asyncio
async def test_la_racha_cuenta_la_practica_de_la_noche_en_su_dia(monkeypatch):
    """Practicó el 13 a mediodía y el 14 a las 11:30 p. m. (Panamá). A las 11:45 p. m. del 14 la
    racha es de 2 días; en UTC la práctica de la noche caería el 15 y la racha sería 0."""
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.post("/api/auth/admin/students", headers=admin_headers(),
                         json={"codigo_estudiante": "ZONA02", "nombre_completo": "Estudiante Racha",
                               "password": "password123"})
        est_id = r.json()["id"]
    monkeypatch.setattr(tiempo, "ahora_utc", lambda: NOCHE_14 + timedelta(minutes=15))
    async with TestSessionLocal() as db:
        perfil = PerfilEstudiante(estudiante_id=est_id)
        db.add(perfil)
        await db.flush()
        for inicio in (datetime(2026, 11, 13, 17, 0), NOCHE_14):
            db.add(SesionPractica(estudiante_id=est_id, perfil_id=est_id, cantidad_problemas=1, problemas_ids=[],
                                  estado=EstadoSesion.COMPLETADA, nivel_actual_inicio=1,
                                  fecha_inicio=inicio, fecha_fin=inicio + timedelta(minutes=5)))
        await db.flush()
        assert await PracticeRepository(db).get_dias_consecutivos_practicando(est_id) == 2
        await db.rollback()

"""
Tests de la protección de los endpoints de administración.

Todos los endpoints /api/admin/* y /api/auth/admin/* exigen un token con
role="admin", obtenido en POST /api/auth/admin-login.
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.main import app
from tests.conftest import admin_headers

ENDPOINTS_ADMIN = [
    ("GET", "/api/admin/organizations"),
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/export/estudiantes"),
    ("GET", "/api/admin/export/resumen"),
    ("GET", "/api/admin/ml/estado"),
    ("DELETE", "/api/admin/students/1"),
    ("POST", "/api/admin/import/excel"),
    ("POST", "/api/auth/admin/students"),
    ("POST", "/api/auth/admin/teachers"),
    ("POST", "/api/auth/admin/bulk/students"),
    ("POST", "/api/auth/admin/bulk/teachers"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
async def test_admin_sin_token_devuelve_401(metodo, ruta):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.request(metodo, ruta)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
async def test_admin_con_token_de_profesor_devuelve_403(metodo, ruta):
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/auth/admin/teachers",
            headers=admin_headers(),
            json={
                "codigo_profesor": "PROFADM1",
                "nombre_completo": "Profe Prueba",
                "password": "password123",
            },
        )
        login = await client.post(
            "/api/auth/login", json={"codigo": "PROFADM1", "password": "password123"}
        )
        token = login.json()["access_token"]
        response = await client.request(
            metodo, ruta, headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_con_token_de_admin_accede():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/admin/organizations", headers=admin_headers())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_token_de_admin_no_sirve_como_usuario():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/auth/me", headers=admin_headers())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_correcto_y_token_funciona(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "clave-de-prueba-admin")
    async with AsyncClient(app=app, base_url="http://test") as client:
        login = await client.post(
            "/api/auth/admin-login", json={"password": "clave-de-prueba-admin"}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        response = await client.get(
            "/api/admin/organizations", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_login_password_incorrecta(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "clave-de-prueba-admin")
    from app.api.routers import auth as auth_router

    auth_router._admin_fallos.clear()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/auth/admin-login", json={"password": "incorrecta"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_deshabilitado_sin_password_configurada(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/auth/admin-login", json={"password": "cualquiera"})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_admin_login_bloquea_tras_cinco_fallos(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "clave-de-prueba-admin")
    from app.api.routers import auth as auth_router

    auth_router._admin_fallos.clear()
    async with AsyncClient(app=app, base_url="http://test") as client:
        for _ in range(5):
            r = await client.post("/api/auth/admin-login", json={"password": "mala"})
            assert r.status_code == 401
        bloqueado = await client.post(
            "/api/auth/admin-login", json={"password": "clave-de-prueba-admin"}
        )
    auth_router._admin_fallos.clear()
    assert bloqueado.status_code == 429

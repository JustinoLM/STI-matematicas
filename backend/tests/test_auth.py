"""
Tests del sistema de autenticación.

Prueba login, creación de usuarios, tokens JWT y protección de endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from tests.conftest import admin_headers
from app.core.config import settings


@pytest.mark.asyncio
async def test_create_student_success():
    """Test de creación de estudiante exitosa."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024001",
                "nombre_completo": "Juan Pérez",
                "password": "password123"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["codigo_estudiante"] == "EST2024001"
    assert data["nombre_completo"] == "Juan Pérez"
    assert data["tipo_usuario"] == "estudiante"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_student_duplicate_codigo():
    """Test de creación de estudiante con código duplicado."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear primer estudiante
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024002",
                "nombre_completo": "María García",
                "password": "password123"
            }
        )
        
        # Intentar crear otro con mismo código
        response = await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024002",
                "nombre_completo": "Pedro López",
                "password": "password456"
            }
        )
    
    assert response.status_code == 400
    assert "código" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_teacher_success():
    """Test de creación de profesor exitosa."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/admin/teachers",
            headers=admin_headers(),
            json={
                "codigo_profesor": "PROF001",
                "nombre_completo": "Ana Martínez",
                "password": "password123",
                "institucion": "Escuela Central"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["codigo_profesor"] == "PROF001"
    assert data["nombre_completo"] == "Ana Martínez"
    assert data["tipo_usuario"] == "profesor"


@pytest.mark.asyncio
async def test_login_student_success():
    """Test de login exitoso de estudiante."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear estudiante
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024003",
                "nombre_completo": "Carlos Ruiz",
                "password": "password123"
            }
        )
        
        # Login
        response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST2024003",
                "password": "password123"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["tipo_usuario"] == "estudiante"


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Test de login con contraseña incorrecta."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear estudiante
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024004",
                "nombre_completo": "Luis Gómez",
                "password": "password123"
            }
        )
        
        # Login con contraseña incorrecta
        response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST2024004",
                "password": "wrongpassword"
            }
        )
    
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """Test de login con código inexistente."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST9999999",
                "password": "password123"
            }
        )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_authenticated():
    """Test de obtener usuario actual con token válido."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y hacer login
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024005",
                "nombre_completo": "Sofia López",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST2024005",
                "password": "password123"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Obtener usuario actual
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["tipo_usuario"] == "estudiante"


@pytest.mark.asyncio
async def test_get_current_user_no_token():
    """Test de obtener usuario actual sin token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/auth/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test de obtener usuario actual con token inválido."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_success():
    """Test de cambio de contraseña exitoso."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y hacer login
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST2024006",
                "nombre_completo": "Miguel Torres",
                "password": "oldpassword"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST2024006",
                "password": "oldpassword"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Cambiar contraseña
        response = await client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "password_actual": "oldpassword",
                "password_nueva": "newpassword123"
            }
        )
    
    assert response.status_code == 200
    assert "exitosa" in response.json()["message"].lower()
    
    # Verificar que puede hacer login con nueva contraseña
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "EST2024006",
                "password": "newpassword123"
            }
        )
        assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_endpoint():
    """Test de que profesor no puede acceder a endpoint de estudiante."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear profesor
        await client.post(
            "/api/auth/admin/teachers",
            headers=admin_headers(),
            json={
                "codigo_profesor": "PROF002",
                "nombre_completo": "Roberto Díaz",
                "password": "password123"
            }
        )
        
        # Login como profesor
        login_response = await client.post(
            "/api/auth/login",
            json={
                "codigo": "PROF002",
                "password": "password123"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Intentar acceder a endpoint de estudiante
        response = await client.get(
            "/api/auth/me/student",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 403
    assert "estudiantes" in response.json()["detail"].lower()

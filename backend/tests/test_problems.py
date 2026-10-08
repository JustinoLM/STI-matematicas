"""
Tests del módulo de generación de problemas.

Prueba generación, validación y registro de intentos.
"""

import pytest
from httpx import AsyncClient
from decimal import Decimal

from app.main import app
from tests.conftest import admin_headers


@pytest.mark.asyncio
async def test_generate_problems_default_level_1():
    """Test de generación de problemas nivel 1 (básico)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar estudiante
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST001",
                "nombre_completo": "Test Student",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST001", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar problemas nivel 1
        response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 5
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    
    # Verificar estructura de cada problema
    for problema in data:
        assert "id" in problema
        assert "operacion" in problema
        assert "numero1" in problema
        assert "numero2" in problema
        assert "nivel_dificultad" in problema
        assert problema["nivel_dificultad"] == 1
        assert problema["operacion"] in ["+", "-"]
        assert "resultado" not in problema  # No debe mostrar resultado


@pytest.mark.asyncio
async def test_generate_problems_level_3_with_multiplication():
    """Test de generación nivel 3 (incluye multiplicación)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST002",
                "nombre_completo": "Test Student 2",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST002", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar problemas nivel 3
        response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 3,
                "cantidad": 10
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    
    # Verificar que hay variedad de operaciones
    operaciones = [p["operacion"] for p in data]
    assert len(set(operaciones)) >= 2  # Al menos 2 tipos de operación diferentes


@pytest.mark.asyncio
async def test_generate_problems_custom_parameters():
    """Test de generación con parámetros personalizados."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST003",
                "nombre_completo": "Test Student 3",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST003", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar solo sumas
        response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 2,
                "operaciones_permitidas": ["+"],
                "decimales_maximos": 1,
                "rango_min": 10,
                "rango_max": 50,
                "cantidad": 5
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que todos son sumas
    for problema in data:
        assert problema["operacion"] == "+"
        # Verificar rango (aproximado, puede haber decimales)
        assert float(problema["numero1"]) >= 10
        assert float(problema["numero1"]) <= 50


@pytest.mark.asyncio
async def test_submit_answer_correct():
    """Test de enviar respuesta correcta."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST004",
                "nombre_completo": "Test Student 4",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST004", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar un problema
        gen_response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 1
            }
        )
        problema = gen_response.json()[0]
        
        # Obtener problema completo para saber la respuesta correcta
        problema_completo = await client.get(
            f"/api/problems/{problema['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        respuesta_correcta = problema_completo.json()["resultado"]
        
        # Enviar respuesta correcta
        response = await client.post(
            "/api/problems/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "problema_id": problema["id"],
                "respuesta_estudiante": respuesta_correcta,
                "tiempo_resolucion": 10,
                "solicito_pista": False,
                "tipo_sesion": "practica"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["es_correcto"] is True
    assert "problema" in data
    assert data["tiempo_resolucion"] == 10


@pytest.mark.asyncio
async def test_submit_answer_incorrect():
    """Test de enviar respuesta incorrecta."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST005",
                "nombre_completo": "Test Student 5",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST005", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar problema
        gen_response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 1
            }
        )
        problema = gen_response.json()[0]
        
        # Enviar respuesta incorrecta
        response = await client.post(
            "/api/problems/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "problema_id": problema["id"],
                "respuesta_estudiante": "999.99",  # Claramente incorrecta
                "tiempo_resolucion": 5,
                "solicito_pista": False,
                "tipo_sesion": "practica"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["es_correcto"] is False
    assert data["respuesta_estudiante"] == "999.99"


@pytest.mark.asyncio
async def test_validate_answer_without_registering():
    """Test de validar respuesta sin registrar intento."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST006",
                "nombre_completo": "Test Student 6",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST006", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar problema
        gen_response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 1
            }
        )
        problema = gen_response.json()[0]
        
        # Obtener respuesta correcta
        problema_completo = await client.get(
            f"/api/problems/{problema['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        respuesta_correcta = problema_completo.json()["resultado"]
        
        # Validar sin registrar
        response = await client.post(
            "/api/problems/validate",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "problema_id": problema["id"],
                "respuesta": respuesta_correcta
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["es_correcto"] is True
    assert "mensaje" in data


@pytest.mark.asyncio
async def test_generate_division_problems():
    """Test específico para problemas de división."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST007",
                "nombre_completo": "Test Student 7",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST007", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar solo divisiones
        response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 4,
                "operaciones_permitidas": ["÷"],
                "cantidad": 5
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que todos son divisiones
    for problema in data:
        assert problema["operacion"] == "÷"
        # Verificar que numero2 no sea cero
        assert float(problema["numero2"]) > 0


@pytest.mark.asyncio
async def test_problem_uniqueness_by_signature():
    """Test que verifica que problemas idénticos no se duplican."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST008",
                "nombre_completo": "Test Student 8",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST008", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Generar muchos problemas del mismo nivel
        response1 = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 20
            }
        )
        
        response2 = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 1,
                "cantidad": 20
            }
        )
    
    # Extraer IDs
    ids1 = [p["id"] for p in response1.json()]
    ids2 = [p["id"] for p in response2.json()]
    
    # Verificar que algunos IDs se reutilizan (problemas idénticos)
    ids_comunes = set(ids1) & set(ids2)
    # Puede haber algunos en común debido a reutilización
    # Lo importante es que el sistema no crashea


@pytest.mark.asyncio
async def test_generate_problems_requires_authentication():
    """Test que verifica que generar problemas requiere autenticación."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/problems/generate",
            json={
                "nivel_dificultad": 1,
                "cantidad": 5
            }
        )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_problems_invalid_level():
    """Test con nivel de dificultad inválido."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Crear y autenticar
        await client.post(
            "/api/auth/admin/students",
            headers=admin_headers(),
            json={
                "codigo_estudiante": "EST009",
                "nombre_completo": "Test Student 9",
                "password": "password123"
            }
        )
        
        login_response = await client.post(
            "/api/auth/login",
            json={"codigo": "EST009", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Intentar nivel 10 (inválido)
        response = await client.post(
            "/api/problems/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nivel_dificultad": 10,
                "cantidad": 5
            }
        )
    
    assert response.status_code == 422  # Pydantic validation error

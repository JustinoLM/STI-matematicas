"""
Tests básicos para el endpoint principal.
"""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test del endpoint raíz."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_health_check():
    """Test del health check."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

"""Testes dos endpoints de verificação de integridade e saúde da aplicação."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_retorna_200() -> None:
    """Verifica se a rota raiz responde com status 200 e informações da aplicação."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Auto Law" in data["app"]


@pytest.mark.asyncio
async def test_health_ping_retorna_pong() -> None:
    """Verifica se o endpoint leve de ping responde 200."""
    from app.routers.health import router as health_router

    test_app = app
    if not any(getattr(r, "path", None) == "/health/ping" for r in test_app.routes):
        test_app.include_router(health_router)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "pong"}

"""Testes dos endpoints de verificação de integridade e saúde da aplicação."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_retorna_200() -> None:
    """Verifica se a rota raiz responde com status 200 e allowed_phones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Auto Law" in data["app"]
        assert "allowed_phones" in data
        assert data["version"] == "0.2.0"


@pytest.mark.asyncio
async def test_health_ping_retorna_pong() -> None:
    """Verifica se o endpoint leve de ping responde 200 com pong."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "pong"}


@pytest.mark.asyncio
async def test_health_check_estrutura_completa() -> None:
    """Verifica se o endpoint /health retorna o status dos subsistemas da aplicação."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["api"] == "ok"
        assert "postgres" in data
        assert "redis" in data
        assert "kommo" in data
        assert "meta" in data
        assert data["version"] == "0.2.0"


@pytest.mark.asyncio
async def test_health_check_com_servicos_conectados() -> None:
    """Verifica resposta do /health com Redis, Kommo e Meta simulando conexão ativa."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    with (
        patch(
            "app.routers.health.verificar_status_kommo",
            new_callable=AsyncMock,
            return_value={"status": "ok", "subdomain": "liviafranaadv", "conectado": True},
        ),
        patch(
            "app.routers.health.verificar_status_meta",
            new_callable=AsyncMock,
            return_value={"status": "ok", "conectado": True},
        ),
    ):
        # Injeta mock de redis no estado da app para teste
        app.state.redis = mock_redis
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["redis"] == "ok"
            assert data["kommo"] == "ok"
            assert data["meta"] == "ok"

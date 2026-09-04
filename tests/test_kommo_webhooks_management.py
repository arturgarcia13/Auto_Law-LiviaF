"""Testes para gestão, permissões e auto-cura de webhooks do Kommo CRM."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from integrations.kommo import (
    DEFAULT_WEBHOOK_EVENTS,
    criar_webhook,
    garantir_webhook_ativo,
    listar_webhooks,
    modificar_webhook_permissoes,
    remover_webhook,
    testar_ping_webhook,
)

SUBDOMAIN = "liviafranaadv"
MOCK_DESTINATION = "https://quickness-serrated-felt-tip.ngrok-free.dev/kommo/webhook?token=teste123"


@pytest.fixture
def mock_kommo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KOMMO_SUBDOMAIN", SUBDOMAIN)
    monkeypatch.setenv("KOMMO_LONG_LIVED_TOKEN", "fake_token_jwt_123")
    monkeypatch.setenv("KOMMO_WEBHOOK_SECRET", "teste123")
    monkeypatch.setenv("ADMIN_SECRET_TOKEN", "admin_secret_456")


# ==============================================================================
# Testes Unitários de Funções da Integração
# ==============================================================================


@pytest.mark.asyncio
async def test_listar_webhooks_sucesso(mock_kommo_env: None) -> None:
    """Valida listagem de webhooks e filtragem por destino."""
    mock_dados = {
        "_embedded": {
            "webhooks": [
                {
                    "id": 101,
                    "destination": MOCK_DESTINATION,
                    "settings": ["add_message"],
                    "disabled": False,
                },
                {
                    "id": 102,
                    "destination": "https://outro.dominio.com/webhook",
                    "settings": ["add_lead"],
                    "disabled": True,
                },
            ]
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(200, json=mock_dados)

        # Sem filtro
        todos = await listar_webhooks()
        assert len(todos) == 2
        assert todos[0]["id"] == 101

        # Com filtro
        filtrados = await listar_webhooks(destination=MOCK_DESTINATION)
        assert len(filtrados) == 1
        assert filtrados[0]["destination"] == MOCK_DESTINATION


@pytest.mark.asyncio
async def test_listar_webhooks_sem_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica retorno vazio se token não estiver configurado."""
    monkeypatch.setenv("KOMMO_LONG_LIVED_TOKEN", "")
    monkeypatch.setenv("KOMMO_API_KEY", "")
    monkeypatch.setenv("API_KEY", "")
    res = await listar_webhooks()
    assert res == []


@pytest.mark.asyncio
async def test_criar_webhook_sucesso(mock_kommo_env: None) -> None:
    """Valida criação de webhook com evento padrão add_message."""
    mock_resp = {
        "id": 555,
        "destination": MOCK_DESTINATION,
        "settings": ["add_message"],
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(201, json=mock_resp)

        res = await criar_webhook(destination=MOCK_DESTINATION)
        assert res["ok"] is True
        assert res["status_code"] == 201
        assert res["settings"] == DEFAULT_WEBHOOK_EVENTS
        assert res["destination"] == MOCK_DESTINATION


@pytest.mark.asyncio
async def test_remover_webhook_sucesso(mock_kommo_env: None) -> None:
    """Valida exclusão de webhook na API da Kommo."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = Response(204)

        res = await remover_webhook(destination=MOCK_DESTINATION)
        assert res["ok"] is True
        assert res["status_code"] == 204
        assert res["destination"] == MOCK_DESTINATION


@pytest.mark.asyncio
async def test_modificar_webhook_permissoes(mock_kommo_env: None) -> None:
    """Valida modificação de permissões através do ciclo delete + create."""
    with (
        patch("integrations.kommo.remover_webhook", new_callable=AsyncMock) as mock_del,
        patch("integrations.kommo.criar_webhook", new_callable=AsyncMock) as mock_create,
    ):
        mock_del.return_value = {"ok": True, "status_code": 204}
        mock_create.return_value = {
            "ok": True,
            "status_code": 201,
            "settings": ["add_message", "add_lead"],
        }

        novos_eventos = ["add_message", "add_lead"]
        res = await modificar_webhook_permissoes(MOCK_DESTINATION, events=novos_eventos)

        assert res["ok"] is True
        assert res["events"] == novos_eventos
        mock_del.assert_called_once_with(MOCK_DESTINATION)
        mock_create.assert_called_once_with(MOCK_DESTINATION, events=novos_eventos)


@pytest.mark.asyncio
async def test_testar_ping_webhook_sucesso() -> None:
    """Valida teste de conectividade ping com resposta 200."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json={"status": "ok", "event": "handshake_ping"})

        res = await testar_ping_webhook(MOCK_DESTINATION)
        assert res["ok"] is True
        assert res["status_code"] == 200
        assert "latency_ms" in res


# ==============================================================================
# Testes do Ciclo de Auto-Cura (garantir_webhook_ativo)
# ==============================================================================


@pytest.mark.asyncio
async def test_auto_cura_caso_saudavel(mock_kommo_env: None) -> None:
    """Caso 1: Webhook já existe, está ativo, com add_message e ping ok -> nenhuma alteração."""
    mock_webhook = {
        "id": 101,
        "destination": MOCK_DESTINATION,
        "settings": ["add_message"],
        "disabled": False,
    }

    with (
        patch("integrations.kommo.listar_webhooks", new_callable=AsyncMock) as mock_list,
        patch("integrations.kommo.testar_ping_webhook", new_callable=AsyncMock) as mock_ping,
        patch("integrations.kommo.remover_webhook", new_callable=AsyncMock) as mock_del,
        patch("integrations.kommo.criar_webhook", new_callable=AsyncMock) as mock_create,
    ):
        mock_list.return_value = [mock_webhook]
        mock_ping.return_value = {"ok": True, "status_code": 200, "latency_ms": 15.2}

        res = await garantir_webhook_ativo(MOCK_DESTINATION, required_events=["add_message"])

        assert res["ok"] is True
        assert res["status"] == "healthy"
        assert res["action"] == "none"
        mock_del.assert_not_called()
        mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_auto_cura_caso_inexistente(mock_kommo_env: None) -> None:
    """Caso 2: Webhook não existe na Kommo -> insere e valida."""
    created_obj = {
        "id": 202,
        "destination": MOCK_DESTINATION,
        "settings": ["add_message"],
        "disabled": False,
    }

    with (
        patch("integrations.kommo.listar_webhooks", new_callable=AsyncMock) as mock_list,
        patch("integrations.kommo.testar_ping_webhook", new_callable=AsyncMock) as mock_ping,
        patch("integrations.kommo.criar_webhook", new_callable=AsyncMock) as mock_create,
        patch("integrations.kommo.remover_webhook", new_callable=AsyncMock) as mock_del,
    ):
        # 1ª chamada: não existe; 2ª chamada pós criação: existe
        mock_list.side_effect = [[], [created_obj]]
        mock_ping.return_value = {"ok": True, "status_code": 200, "latency_ms": 20.0}
        mock_create.return_value = {"ok": True, "status_code": 201}

        res = await garantir_webhook_ativo(MOCK_DESTINATION, required_events=["add_message"])

        assert res["ok"] is True
        assert res["status"] == "repaired"
        assert res["action"] == "recreated"
        mock_del.assert_not_called()
        mock_create.assert_called_once_with(MOCK_DESTINATION, events=["add_message"])


@pytest.mark.asyncio
async def test_auto_cura_caso_desativado_ou_sem_add_message(mock_kommo_env: None) -> None:
    """Caso 3: Webhook existe mas está desativado ou sem add_message -> remove, recria e valida."""
    webhook_invalido = {
        "id": 303,
        "destination": MOCK_DESTINATION,
        "settings": ["add_lead"],  # falta add_message!
        "disabled": True,  # e está desativado!
    }
    webhook_corrigido = {
        "id": 304,
        "destination": MOCK_DESTINATION,
        "settings": ["add_message"],
        "disabled": False,
    }

    with (
        patch("integrations.kommo.listar_webhooks", new_callable=AsyncMock) as mock_list,
        patch("integrations.kommo.testar_ping_webhook", new_callable=AsyncMock) as mock_ping,
        patch("integrations.kommo.remover_webhook", new_callable=AsyncMock) as mock_del,
        patch("integrations.kommo.criar_webhook", new_callable=AsyncMock) as mock_create,
    ):
        mock_list.side_effect = [[webhook_invalido], [webhook_corrigido]]
        mock_ping.return_value = {"ok": True, "status_code": 200, "latency_ms": 18.0}
        mock_del.return_value = {"ok": True, "status_code": 204}
        mock_create.return_value = {"ok": True, "status_code": 201}

        res = await garantir_webhook_ativo(MOCK_DESTINATION, required_events=["add_message"])

        assert res["ok"] is True
        assert res["status"] == "repaired"
        assert "webhook_desativado_no_crm" in res["motivos_reparo"]
        mock_del.assert_called_once_with(MOCK_DESTINATION)
        mock_create.assert_called_once_with(MOCK_DESTINATION, events=["add_message"])


# ==============================================================================
# Testes das Rotas Administrativas REST (/admin/kommo/webhooks)
# ==============================================================================


@pytest.mark.asyncio
async def test_admin_rotas_autenticacao(mock_kommo_env: None) -> None:
    """Garante que rotas /admin/kommo/webhooks rejeitam acessos sem token válido."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Sem token
        resp = await ac.get("/admin/kommo/webhooks")
        assert resp.status_code == 401

        # Com token errado
        resp_err = await ac.get("/admin/kommo/webhooks?token=token_invalido")
        assert resp_err.status_code == 401

        # Com token correto via query
        with patch("app.routers.admin.listar_webhooks", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []
            resp_ok = await ac.get("/admin/kommo/webhooks?token=teste123")
            assert resp_ok.status_code == 200


@pytest.mark.asyncio
async def test_admin_criar_e_modificar_webhooks(mock_kommo_env: None) -> None:
    """Testa endpoints POST e PUT administrativos para webhooks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with (
            patch("app.routers.admin.criar_webhook", new_callable=AsyncMock) as mock_create,
            patch(
                "app.routers.admin.modificar_webhook_permissoes", new_callable=AsyncMock
            ) as mock_mod,
        ):
            mock_create.return_value = {"ok": True, "status_code": 201}
            mock_mod.return_value = {"ok": True, "status_code": 201}

            # POST /admin/kommo/webhooks
            payload_create = {"destination": MOCK_DESTINATION, "events": ["add_message"]}
            resp_create = await ac.post("/admin/kommo/webhooks?token=teste123", json=payload_create)
            assert resp_create.status_code == 200
            assert resp_create.json()["status"] == "created"

            # PUT /admin/kommo/webhooks
            payload_update = {
                "destination": MOCK_DESTINATION,
                "events": ["add_message", "add_lead"],
            }
            resp_update = await ac.put("/admin/kommo/webhooks?token=teste123", json=payload_update)
            assert resp_update.status_code == 200
            assert resp_update.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_admin_sync_auto_cura(mock_kommo_env: None) -> None:
    """Testa endpoint POST /admin/kommo/webhooks/sync."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch(
            "app.routers.admin.garantir_webhook_ativo", new_callable=AsyncMock
        ) as mock_garantir:
            mock_garantir.return_value = {
                "ok": True,
                "status": "healthy",
                "action": "none",
                "destination": MOCK_DESTINATION,
            }

            resp = await ac.post(
                "/admin/kommo/webhooks/sync?token=teste123",
                json={"destination": MOCK_DESTINATION, "events": ["add_message"]},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "healthy"

"""Testes de recepção e validação de webhooks do Kommo CRM e Mensageria."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.kommo import KommoMessagePayload, KommoWebhookPayload


@pytest.mark.unit
def test_schema_kommo_payload_texto(mock_kommo_text_payload: dict[str, Any]) -> None:
    """Verifica se o schema do Kommo extrai telefone e mensagem de texto corretamente."""
    payload = KommoMessagePayload.model_validate(mock_kommo_text_payload)
    assert payload.telefone_normalizado == "5511999999999"
    assert payload.texto == "Olá, fui demitido sem justa causa e gostaria de orientação jurídica."
    assert payload.e_audio is False
    assert payload.e_minha_mensagem is False
    assert payload.chat_id == "chat_123456"


@pytest.mark.unit
def test_schema_kommo_payload_audio(mock_kommo_audio_payload: dict[str, Any]) -> None:
    """Verifica detecção e normalização de mensagem de áudio/voz."""
    payload = KommoMessagePayload.model_validate(mock_kommo_audio_payload)
    assert payload.telefone_normalizado == "5521988887777"
    assert payload.e_audio is True
    assert payload.message.media == "https://example.com/audios/audio_teste.ogg"
    assert payload.message.duration == 15
    assert payload.e_minha_mensagem is False


@pytest.mark.unit
def test_schema_kommo_payload_mensagem_propria(
    mock_kommo_outgoing_payload: dict[str, Any],
) -> None:
    """Verifica se mensagens originadas do bot ou operador são identificadas."""
    payload = KommoMessagePayload.model_validate(mock_kommo_outgoing_payload)
    assert payload.e_minha_mensagem is True


@pytest.mark.unit
def test_schema_kommo_webhook_crm(
    mock_kommo_leads_webhook_payload: dict[str, Any],
    mock_kommo_tasks_webhook_payload: dict[str, Any],
) -> None:
    """Verifica parsing de webhooks padrões do Kommo CRM (leads e tarefas)."""
    lead_payload = KommoWebhookPayload.model_validate(mock_kommo_leads_webhook_payload)
    assert lead_payload.leads is not None
    assert "status" in lead_payload.leads

    task_payload = KommoWebhookPayload.model_validate(mock_kommo_tasks_webhook_payload)
    assert task_payload.tasks is not None
    assert "add" in task_payload.tasks


@pytest.mark.asyncio
async def test_endpoint_webhook_kommo_texto(mock_kommo_text_payload: dict[str, Any]) -> None:
    """Testa recepção de mensagem de texto via endpoint /webhook/kommo."""
    transport = ASGITransport(app=app)
    with patch("app.routers.kommo.enviar_mensagem", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "success"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook/kommo", json=mock_kommo_text_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["chat_id"] == "chat_123456"
            mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_webhook_kommo_audio(mock_kommo_audio_payload: dict[str, Any]) -> None:
    """Testa recepção e transcrição de áudio via endpoint /webhook/kommo."""
    transport = ASGITransport(app=app)
    with (
        patch(
            "app.routers.kommo.transcrever_audio",
            new_callable=AsyncMock,
            return_value="Fui demitido semana passada sem receber as verbas rescisórias.",
        ) as mock_transcribe,
        patch("app.routers.kommo.enviar_mensagem", new_callable=AsyncMock) as mock_send,
    ):
        mock_send.return_value = {"status": "success"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook/kommo", json=mock_kommo_audio_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            mock_transcribe.assert_awaited_once_with(
                "https://example.com/audios/audio_teste.ogg"
            )
            mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_webhook_kommo_ignora_mensagem_propria(
    mock_kommo_outgoing_payload: dict[str, Any],
) -> None:
    """Testa se mensagens enviadas pelo próprio operador são ignoradas pelo bot."""
    transport = ASGITransport(app=app)
    with patch("app.routers.kommo.enviar_mensagem", new_callable=AsyncMock) as mock_send:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook/kommo", json=mock_kommo_outgoing_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ignored"
            assert data["reason"] == "outgoing_message"
            mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_filtro_lista_permissao_chat_id(
    mock_kommo_text_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa se ALLOWED_CHAT_IDS bloqueia chats não autorizados e permite o autorizado."""
    transport = ASGITransport(app=app)

    # 1. Configura lista de permissão apenas com o ID 20429066
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "20429066")

    # Chat não autorizado (ex: chat_123456)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_bloqueado = await client.post("/webhook/kommo", json=mock_kommo_text_payload)
        assert res_bloqueado.status_code == 200
        data_bloqueado = res_bloqueado.json()
        assert data_bloqueado["status"] == "ignored"
        assert data_bloqueado["reason"] == "chat_not_in_allowlist"

    # Chat autorizado (chat_id = 20429066)
    payload_autorizado = dict(mock_kommo_text_payload)
    payload_autorizado["chat_id"] = "20429066"
    with patch("app.routers.kommo.enviar_mensagem", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "success"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_permitido = await client.post("/webhook/kommo", json=payload_autorizado)
            assert res_permitido.status_code == 200
            data_permitido = res_permitido.json()
            assert data_permitido["status"] == "ok"
            mock_send.assert_awaited_once()


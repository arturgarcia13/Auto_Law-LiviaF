"""Testes de recepção e validação de webhooks do Kommo CRM, Meta Cloud API e /send."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers.kommo import processar_mensagem_kommo
from app.schemas.kommo import KommoMessagePayload, KommoWebhookPayload
from app.services.deduplication import deduplicator


@pytest.fixture(autouse=True)
def mock_webhook_env() -> Any:
    """Configura variáveis de ambiente mock para os testes de webhooks."""
    with (
        patch.dict(
            "os.environ",
            {
                "KOMMO_WEBHOOK_SECRET": "teste123",
                "ADMIN_SECRET_TOKEN": "admin_token_123",
                "ALLOWED_PHONES": "5511999999999,5521988887777,5585984347149",
                "META_PHONE_NUMBER_ID": "1226609120527127",
                "META_WHATSAPP_TOKEN": "fake_meta_token",
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
            },
        ),
        patch("agent.nodes._get_gemini_client", return_value=None),
    ):
        yield


async def _aguardar_background_tasks() -> None:
    """Aguarda tarefas assíncronas em background disparadas por create_task terminarem."""
    for _ in range(5):
        await asyncio.sleep(0.01)
        tasks = [
            t for t in asyncio.all_tasks()
            if t is not asyncio.current_task() and not t.done()
        ]
        if not tasks:
            break
        await asyncio.gather(*tasks, return_exceptions=True)


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
async def test_endpoint_kommo_webhook_token_invalido(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Testa se o webhook do Kommo rejeita requisições sem token válido (HTTP 401)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/kommo/webhook?token=token_invalido",
            json=mock_kommo_text_payload,
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "unauthorized"


@pytest.mark.asyncio
async def test_endpoint_kommo_webhook_texto_sucesso(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Testa recepção de texto via /kommo/webhook com resposta imediata Fast ACK."""
    transport = ASGITransport(app=app)
    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta_send,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock) as mock_note,
    ):
        mock_meta_send.return_value = {"ok": True, "status": 200, "wamid": "wamid.123"}
        mock_note.return_value = {"ok": True}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/kommo/webhook?token=teste123",
                json=mock_kommo_text_payload,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["received"] is True

            # Aguarda a conclusão da tarefa pesada em background
            await _aguardar_background_tasks()
            mock_meta_send.assert_awaited_once()

    # Valida execução direta síncrona de processar_mensagem_kommo
    deduplicator.clear()
    payload_obj = KommoMessagePayload.model_validate(mock_kommo_text_payload)
    res_direto = await processar_mensagem_kommo(payload_obj)
    assert res_direto["status"] == "ok"
    assert res_direto["telefone"] == "5511999999999"
    assert "response" in res_direto


@pytest.mark.asyncio
async def test_endpoint_kommo_webhook_audio(mock_kommo_audio_payload: dict[str, Any]) -> None:
    """Testa recepção e transcrição de áudio via /kommo/webhook com Fast ACK."""
    transport = ASGITransport(app=app)
    with (
        patch(
            "app.routers.kommo.transcrever_audio",
            new_callable=AsyncMock,
            return_value="Fui demitido semana passada sem justa causa.",
        ) as mock_transcribe,
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta_send,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta_send.return_value = {"ok": True, "status": 200, "wamid": "wamid.456"}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/kommo/webhook?token=teste123",
                json=mock_kommo_audio_payload,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["received"] is True

            # Aguarda a tarefa assíncrona em background
            await _aguardar_background_tasks()
            mock_transcribe.assert_awaited_once_with(
                "https://example.com/audios/audio_teste.ogg"
            )
            mock_meta_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_filtro_allowed_phones(
    mock_kommo_text_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa se ALLOWED_PHONES bloqueia telefones não autorizados e permite os autorizados."""
    transport = ASGITransport(app=app)

    # 1. Configura lista de permissão apenas com um número diferente
    monkeypatch.setenv("ALLOWED_PHONES", "5585984347149")

    # Validação direta da regra de negócio: telefone não autorizado (5511999999999)
    payload_bloqueado = KommoMessagePayload.model_validate(mock_kommo_text_payload)
    res_bloqueado = await processar_mensagem_kommo(payload_bloqueado)
    assert res_bloqueado["status"] == "ignored"
    assert res_bloqueado["reason"] == "phone_not_in_allowlist"

    # Limpa deduplicação para permitir teste isolado do webhook autorizado
    deduplicator.clear()

    # Telefone autorizado (5585984347149) via webhook Fast ACK
    payload_autorizado = dict(mock_kommo_text_payload)
    payload_autorizado["phone"] = "5585984347149"
    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta_send,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta_send.return_value = {"ok": True, "status": 200, "wamid": "wamid.789"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_permitido = await client.post(
                "/kommo/webhook?token=teste123",
                json=payload_autorizado,
            )
            assert res_permitido.status_code == 200
            data_permitido = res_permitido.json()
            assert data_permitido["status"] == "ok"
            assert data_permitido["received"] is True

            await _aguardar_background_tasks()
            mock_meta_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_send_sem_token_bloqueia() -> None:
    """Verifica se /send rejeita disparos sem token de autenticação (HTTP 401)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"to": "5585984347149", "text": "Mensagem não autorizada"}
        response = await client.post("/send", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "unauthorized"


@pytest.mark.asyncio
async def test_endpoint_send_com_token_e_allowlist_sucesso() -> None:
    """Verifica envio de mensagem via /send com token e telefone autorizado."""
    transport = ASGITransport(app=app)
    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta_send,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock) as mock_note,
    ):
        mock_meta_send.return_value = {
            "ok": True,
            "status": 200,
            "wamid": "wamid.SEND_MSG_123",
            "body": {"messages": [{"id": "wamid.SEND_MSG_123"}]},
        }
        mock_note.return_value = {"ok": True}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "to": "5585984347149",
                "text": "Olá! Teste de envio manual",
                "lead_id": 20429066,
            }
            response = await client.post("/send?token=teste123", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["result"]["wamid"] == "wamid.SEND_MSG_123"
            mock_meta_send.assert_awaited_once_with(
                to="5585984347149",
                text="Olá! Teste de envio manual",
                template_name=None,
                template_lang="pt_BR",
                template_params=None,
            )
            mock_note.assert_awaited_once_with(
                lead_id=20429066,
                text="Olá! Teste de envio manual",
                wamid="wamid.SEND_MSG_123",
            )


@pytest.mark.asyncio
async def test_filtro_allowed_chat_id_sem_telefone_resolvido_via_contato() -> None:
    """Verifica se mensagem com ALLOWED_CHAT_ID mas sem telefone busca o contato e processa."""
    transport = ASGITransport(app=app)
    payload = {
        "account": {"subdomain": "liviafranaadv", "id": "36730375"},
        "message": {
            "add": {
                "0": {
                    "id": "msg_teste_chat_id",
                    "chat_id": "5520658f-3626-4c5c-b212-83c479ad6218",
                    "talk_id": "439",
                    "contact_id": "43680556",
                    "text": "Olá, preciso de orientações",
                    "element_id": "20429066",
                    "type": "incoming",
                }
            }
        },
    }

    with (
        patch(
            "app.routers.kommo.buscar_telefone_contato",
            new_callable=AsyncMock,
            return_value="+558584347149",
        ) as mock_buscar_tel,
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock) as mock_note,
        patch.dict(
            "os.environ",
            {
                "ALLOWED_CHAT_ID": "5520658f-3626-4c5c-b212-83c479ad6218",
                "ALLOWED_PHONES": "5585984347149,558584347149",
            },
        ),
    ):
        mock_meta.return_value = {"ok": True, "status": 200, "wamid": "wamid.CHAT_ID_OK"}
        mock_note.return_value = {"ok": True}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ok"
            assert data["received"] is True
            assert data["message_id"] == "msg_teste_chat_id"

            await _aguardar_background_tasks()
            mock_buscar_tel.assert_awaited_once_with("43680556")
            mock_meta.assert_awaited_once()


@pytest.mark.asyncio
async def test_deduplicacao_webhook_mesmo_message_id(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Verifica se mensagem com o mesmo message_id é processada na 1ª vez e ignorada na 2ª."""
    transport = ASGITransport(app=app)
    payload = dict(mock_kommo_text_payload)
    payload["message"] = dict(mock_kommo_text_payload["message"])
    payload["message"]["id"] = "msg_id_duplicada_999"

    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta.return_value = {"ok": True, "status": 200, "wamid": "wamid.dup"}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1ª tentativa -> OK
            r1 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r1.status_code == 200
            d1 = r1.json()
            assert d1["status"] == "ok"
            assert d1["received"] is True
            assert d1["message_id"] == "msg_id_duplicada_999"

            # 2ª tentativa imediata -> Duplicada ignorada
            r2 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["status"] == "ignored"
            assert d2["reason"] == "duplicate_message"
            assert d2["message_id"] == "msg_id_duplicada_999"

            await _aguardar_background_tasks()
            # meta_send foi chamado apenas 1 vez
            mock_meta.assert_awaited_once()


@pytest.mark.asyncio
async def test_deduplicacao_webhook_hash_conteudo(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Verifica se mensagens sem message_id explícito são deduplicadas por hash de conteúdo."""
    transport = ASGITransport(app=app)
    payload = dict(mock_kommo_text_payload)

    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta.return_value = {"ok": True, "status": 200, "wamid": "wamid.dup_hash"}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r1.status_code == 200
            assert r1.json()["status"] == "ok"

            r2 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["status"] == "ignored"
            assert d2["reason"] == "duplicate_message"

            await _aguardar_background_tasks()
            mock_meta.assert_awaited_once()


@pytest.mark.asyncio
async def test_deduplicacao_clear_permite_reprocessamento(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Verifica se limpar o deduplicador permite processar uma mensagem previamente vista."""
    transport = ASGITransport(app=app)
    payload = dict(mock_kommo_text_payload)
    payload["message"] = dict(mock_kommo_text_payload["message"])
    payload["message"]["id"] = "msg_para_limpar_01"

    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta.return_value = {"ok": True, "status": 200, "wamid": "wamid.clear"}

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r1.status_code == 200
            assert r1.json()["status"] == "ok"

            # Limpa o cache
            deduplicator.clear()

            # Processa novamente com sucesso
            r2 = await client.post("/kommo/webhook?token=teste123", json=payload)
            assert r2.status_code == 200
            assert r2.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_langgraph_memoria_conversacional_acumula_mensagens() -> None:
    """Verifica se LangGraph com MemorySaver e add_messages acumula mensagens no thread_id."""
    from langgraph.checkpoint.memory import MemorySaver

    from agent.graph import build_graph

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    thread_id = "5511999999999"
    config = {"configurable": {"thread_id": thread_id}}

    # Turno 1
    input_1 = {
        "telefone": thread_id,
        "fase": "analise_viabilidade",
        "messages": [{"role": "user", "content": "Olá, fui admitido em 2021."}],
    }
    res_1 = await graph.ainvoke(input_1, config=config)
    mensagens_1 = res_1.get("messages", [])
    assert len(mensagens_1) >= 2

    # Turno 2 com a mesma thread
    input_2 = {
        "telefone": thread_id,
        "fase": "analise_viabilidade",
        "messages": [{"role": "user", "content": "E fui demitido semana passada."}],
    }
    res_2 = await graph.ainvoke(input_2, config=config)
    mensagens_2 = res_2.get("messages", [])
    # Deve conter as mensagens acumuladas de ambos os turnos
    assert len(mensagens_2) >= len(mensagens_1) + 2


@pytest.mark.asyncio
async def test_processar_mensagem_kommo_dupla_barreira_ignora_duplicadas(
    mock_kommo_text_payload: dict[str, Any],
) -> None:
    """Verifica se chamadas diretas a processar_mensagem_kommo aplicam a barreira interna."""
    deduplicator.clear()
    payload = KommoMessagePayload.model_validate(mock_kommo_text_payload)
    payload.message_id = "msg_direta_duplicada_test"

    with (
        patch("app.routers.kommo.meta_send", new_callable=AsyncMock) as mock_meta,
        patch("app.routers.kommo.add_kommo_note", new_callable=AsyncMock),
    ):
        mock_meta.return_value = {"ok": True, "status": 200, "wamid": "wamid.barreira"}

        # 1ª execução direta -> Sucesso
        res1 = await processar_mensagem_kommo(payload)
        assert res1["status"] == "ok"
        mock_meta.assert_awaited_once()

        # 2ª execução direta com o mesmo message_id -> Ignorada na barreira interna
        res2 = await processar_mensagem_kommo(payload)
        assert res2["status"] == "ignored"
        assert res2["reason"] == "duplicate_message"
        assert res2["message_id"] == "msg_direta_duplicada_test"
        # meta_send continua tendo sido chamado apenas 1 vez
        mock_meta.assert_awaited_once()



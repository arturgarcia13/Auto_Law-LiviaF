"""Testes unitários e de integração para o cliente Meta WhatsApp Cloud API."""

from typing import Any
from unittest.mock import patch

import pytest
import respx

from integrations.meta import meta_send, verificar_status_meta

PHONE_NUMBER_ID = "1226609120527127"
TOKEN = "fake_meta_token_12345"
GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"


@pytest.fixture(autouse=True)
def mock_meta_env() -> Any:
    """Configura variáveis de ambiente mock para a Meta Cloud API."""
    with patch.dict(
        "os.environ",
        {
            "META_PHONE_NUMBER_ID": PHONE_NUMBER_ID,
            "META_WHATSAPP_TOKEN": TOKEN,
            "GRAPH_VERSION": GRAPH_VERSION,
        },
    ):
        yield


@pytest.mark.asyncio
async def test_meta_send_texto_sucesso() -> None:
    """Verifica envio de mensagem de texto com captura de wamid."""
    recipient = "5585984347149"
    text = "Olá! Como posso ajudar você hoje?"

    mock_response = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": recipient, "wa_id": recipient}],
        "messages": [{"id": "wamid.HBgLNTU4NTk4NDM0NzE0OQUCABEYEkZBRjkyMzYxOTQ0"}],
    }

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(BASE_URL).respond(
            status_code=200,
            json=mock_response,
        )

        res = await meta_send(to=recipient, text=text)
        assert res["ok"] is True
        assert res["status"] == 200
        assert res["wamid"] == "wamid.HBgLNTU4NTk4NDM0NzE0OQUCABEYEkZBRjkyMzYxOTQ0"
        assert res["request"]["type"] == "text"
        assert res["request"]["text"]["body"] == text


@pytest.mark.asyncio
async def test_meta_send_template_sucesso() -> None:
    """Verifica envio de template HSM aprovado com parâmetros de corpo."""
    recipient = "5585984347149"
    template_name = "automacao_formulario_743t0b"
    params = ["Carlos Santos", "Advocacia Trabalhista"]

    mock_response = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": recipient, "wa_id": recipient}],
        "messages": [{"id": "wamid.TEMPLATE_MSG_ID_999"}],
    }

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(BASE_URL).respond(
            status_code=200,
            json=mock_response,
        )

        res = await meta_send(
            to=recipient,
            template_name=template_name,
            template_lang="pt_BR",
            template_params=params,
        )
        assert res["ok"] is True
        assert res["status"] == 200
        assert res["wamid"] == "wamid.TEMPLATE_MSG_ID_999"
        assert res["request"]["type"] == "template"
        assert res["request"]["template"]["name"] == template_name
        assert len(res["request"]["template"]["components"][0]["parameters"]) == 2


@pytest.mark.asyncio
async def test_meta_send_sem_credenciais() -> None:
    """Verifica se lança ValueError caso as credenciais não estejam no ambiente."""
    env_clean = {"META_PHONE_NUMBER_ID": "", "META_WHATSAPP_TOKEN": ""}
    with patch.dict("os.environ", env_clean, clear=True):
        with pytest.raises(
            ValueError,
            match="META_PHONE_NUMBER_ID ou META_WHATSAPP_TOKEN não configurados",
        ):
            await meta_send(to="5585984347149", text="Teste")


@pytest.mark.asyncio
async def test_meta_send_erro_api() -> None:
    """Verifica tratamento gracioso quando a Graph API retorna erro HTTP."""
    recipient = "5585984347149"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(BASE_URL).respond(
            status_code=400,
            json={"error": {"message": "Invalid Parameter", "code": 100}},
        )

        res = await meta_send(to=recipient, text="Teste com erro")
        assert res["ok"] is False
        assert res["status"] == 400
        assert res["wamid"] is None


@pytest.mark.asyncio
async def test_verificar_status_meta() -> None:
    """Verifica a checagem de saúde da Meta Cloud API."""
    status_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(status_url).respond(
            status_code=200,
            json={
                "display_phone_number": "+55 85 9843-4714",
                "verified_name": "Dra. Lívia França Advocacia",
                "id": PHONE_NUMBER_ID,
            },
        )

        info = await verificar_status_meta()
        assert info["status"] == "ok"
        assert info["conectado"] is True
        assert info["verified_name"] == "Dra. Lívia França Advocacia"

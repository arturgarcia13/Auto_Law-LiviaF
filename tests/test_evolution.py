"""Testes de integração com o gateway WhatsApp (Evolution API)."""

import pytest

from integrations.evolution import enviar_texto, verificar_status


@pytest.mark.asyncio
async def test_enviar_texto_retorna_sucesso() -> None:
    """Verifica chamada baseline de envio de texto."""
    result = await enviar_texto("5511999999999", "Mensagem de teste")
    assert result["status"] == "success"
    assert result["number"] == "5511999999999"


@pytest.mark.asyncio
async def test_verificar_status_baseline() -> None:
    """Verifica chamada baseline de status da conexão."""
    status = await verificar_status()
    assert isinstance(status, str)

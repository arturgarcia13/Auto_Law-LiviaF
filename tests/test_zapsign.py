"""Testes de integração com a API da ZapSign."""

import pytest

from integrations.zapsign import criar_documento


@pytest.mark.asyncio
async def test_criar_documento_baseline() -> None:
    """Verifica chamada de geração de documento via template."""
    resultado = await criar_documento({"nome": "Cliente Teste", "cpf": "000.000.000-00"})
    assert "doc_token" in resultado
    assert "sign_url" in resultado

"""Testes de integração com a API v1 do ADVBOX."""

import pytest

from integrations.advbox import criar_cliente, criar_processo


@pytest.mark.asyncio
async def test_criar_cliente_baseline() -> None:
    """Verifica chamada de cadastro de cliente no ADVBOX."""
    cliente_id = await criar_cliente({"nome": "Cliente Teste", "cpf": "000.000.000-00"})
    assert isinstance(cliente_id, int)


@pytest.mark.asyncio
async def test_criar_processo_baseline() -> None:
    """Verifica chamada de abertura de processo trabalhista no ADVBOX."""
    processo_id = await criar_processo({"customer_id": 1, "type_lawsuit_id": 10})
    assert isinstance(processo_id, int)

"""Testes de integração com a API v4 do Kommo CRM."""

import pytest

from integrations.kommo import atualizar_lead, criar_lead


@pytest.mark.asyncio
async def test_criar_lead_baseline() -> None:
    """Verifica assinatura e retorno básico da criação de lead."""
    lead_id = await criar_lead("5511999999999", "Cliente Teste")
    assert isinstance(lead_id, int)


@pytest.mark.asyncio
async def test_atualizar_lead_baseline() -> None:
    """Verifica atualização de etapa do lead."""
    sucesso = await atualizar_lead(123, status_id=456)
    assert sucesso is True

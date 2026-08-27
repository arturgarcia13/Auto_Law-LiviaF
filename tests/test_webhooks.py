"""Testes de recepção e validação de webhooks."""

from typing import Any

import pytest

from app.schemas.evolution import EvolutionWebhookPayload


@pytest.mark.unit
def test_schema_evolution_payload_extrai_telefone(mock_evolution_payload: dict[str, Any]) -> None:
    """Verifica se o schema Pydantic parseia e higieniza o telefone corretamente."""
    payload = EvolutionWebhookPayload.model_validate(mock_evolution_payload)
    assert payload.telefone == "5511999999999"
    assert payload.texto == "Olá, vi o anúncio e fui demitido sem justa causa."
    assert payload.e_minha_mensagem is False

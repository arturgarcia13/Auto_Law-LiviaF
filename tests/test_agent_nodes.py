"""Testes unitários dos nós do grafo de agentes (LangGraph)."""

import pytest

from agent.nodes import transbordo_node, triagem_node
from agent.state import LeadState


@pytest.mark.asyncio
async def test_triagem_node_retorna_fase() -> None:
    """Verifica se o nó de triagem processa o estado sem exceções."""
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "triagem",
        "messages": [],
    }
    result = await triagem_node(state)
    assert result.get("fase") == "triagem"


@pytest.mark.asyncio
async def test_transbordo_node_ativa_flag_humano() -> None:
    """Verifica se o nó de transbordo define humano_ativo como True."""
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "triagem",
        "messages": [],
    }
    result = await transbordo_node(state)
    assert result.get("humano_ativo") is True
    assert result.get("fase") == "transbordo"

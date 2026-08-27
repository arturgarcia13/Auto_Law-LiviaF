"""Montagem e compilação do grafo de estados conversacional (LangGraph)."""

from typing import Any

from agent.state import LeadState


def roteador_fases(state: LeadState) -> str:
    """Determina a próxima transição lógica a partir do estado atual."""
    if state.get("humano_ativo"):
        return "__end__"
    return state.get("fase", "triagem")


def build_graph(checkpointer: Any = None) -> Any:
    """Constrói e compila o StateGraph do LangGraph com suporte a persistência."""
    # A instanciação do StateGraph real será conectada no Sprint 5
    return None

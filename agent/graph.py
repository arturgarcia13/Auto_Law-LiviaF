"""Montagem e compilação do grafo de estados conversacional (LangGraph) para a Dra. Lívia França."""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    analise_viabilidade_node,
    envio_contrato_node,
    lead_qualificado_node,
    leads_entrada_node,
    oferta_contrato_node,
)
from agent.state import LeadState

logger = logging.getLogger(__name__)

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except (ImportError, Exception):  # pragma: no cover
    AsyncPostgresSaver = None  # type: ignore


def roteador_fases(state: LeadState) -> str:
    """Determina o ponto de entrada ou a próxima transição lógica a partir do estado atual."""
    if state.get("humano_ativo"):
        return END

    fase = state.get("fase", "leads_entrada")

    if fase == "leads_entrada":
        return "leads_entrada"
    if fase == "analise_viabilidade":
        return "analise_viabilidade"
    if fase == "lead_qualificado":
        return "lead_qualificado"
    if fase == "oferta_contrato":
        return "oferta_contrato"
    if fase == "envio_contrato":
        return "envio_contrato"
    if fase in ("transbordo", "concluido"):
        return END

    return "analise_viabilidade"


def roteador_pos_analise(state: LeadState) -> str:
    """Roteia o fluxo após a execução da análise de viabilidade."""
    if state.get("humano_ativo") or state.get("motivo_inviabilidade"):
        return END

    if state.get("fase") == "lead_qualificado":
        return "lead_qualificado"

    return END


def roteador_pos_oferta(state: LeadState) -> str:
    """Roteia o fluxo após a apresentação da oferta de contrato."""
    if state.get("aceitou_oferta") or state.get("fase") == "envio_contrato":
        return "envio_contrato"

    return END


def build_graph(checkpointer: Any = None) -> Any:
    """Constrói e compila o StateGraph do LangGraph com suporte a persistência."""
    workflow = StateGraph(LeadState)

    # 1. Registro dos nós do fluxo oficial da Dra. Lívia França
    workflow.add_node("leads_entrada", leads_entrada_node)
    workflow.add_node("analise_viabilidade", analise_viabilidade_node)
    workflow.add_node("lead_qualificado", lead_qualificado_node)
    workflow.add_node("oferta_contrato", oferta_contrato_node)
    workflow.add_node("envio_contrato", envio_contrato_node)

    # 2. Ponto de entrada condicional baseado na fase atual do lead
    workflow.add_conditional_edges(
        START,
        roteador_fases,
        {
            "leads_entrada": "leads_entrada",
            "analise_viabilidade": "analise_viabilidade",
            "lead_qualificado": "lead_qualificado",
            "oferta_contrato": "oferta_contrato",
            "envio_contrato": "envio_contrato",
            END: END,
        },
    )

    # 3. Transições entre etapas
    workflow.add_edge("leads_entrada", "analise_viabilidade")
    workflow.add_conditional_edges(
        "analise_viabilidade",
        roteador_pos_analise,
        {
            "lead_qualificado": "lead_qualificado",
            END: END,
        },
    )
    workflow.add_edge("lead_qualificado", "oferta_contrato")
    workflow.add_conditional_edges(
        "oferta_contrato",
        roteador_pos_oferta,
        {
            "envio_contrato": "envio_contrato",
            END: END,
        },
    )
    workflow.add_edge("envio_contrato", END)

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)

    return workflow.compile()

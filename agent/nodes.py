"""Funções de nós executáveis pelo grafo de estados do LangGraph."""

from typing import Any

from agent.state import LeadState


async def triagem_node(state: LeadState) -> dict[str, Any]:
    """Nó de triagem: analisa o caso trabalhista e qualifica o lead."""
    return {"fase": state.get("fase", "triagem")}


async def coleta_dados_node(state: LeadState) -> dict[str, Any]:
    """Nó de coleta: solicita dados cadastrais para o contrato de honorários."""
    return {"fase": "coleta"}


async def gerar_contrato_node(state: LeadState) -> dict[str, Any]:
    """Nó de geração de contrato: invoca API ZapSign e envia link no WhatsApp."""
    return {"fase": "aguardando_assinatura"}


async def transbordo_node(state: LeadState) -> dict[str, Any]:
    """Nó de transbordo: silencia o bot e notifica a equipe jurídica no CRM."""
    return {"fase": "transbordo", "humano_ativo": True}


async def pos_assinatura_node(state: LeadState) -> dict[str, Any]:
    """Nó pós-assinatura: cadastra cliente e processo no ADVBOX e move lead no Kommo."""
    return {"fase": "concluido"}

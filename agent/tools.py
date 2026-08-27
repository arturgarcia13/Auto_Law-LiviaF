"""Ferramentas (tools) acionáveis pelo modelo LLM no LangGraph."""

from typing import Any


def atualizar_kommo(lead_id: str, etapa: str) -> dict[str, Any]:
    """Atualiza o status ou etapa de um lead no Kommo CRM."""
    return {"status": "updated", "lead_id": lead_id, "etapa": etapa}


def iniciar_coleta(motivo_qualificacao: str) -> dict[str, Any]:
    """Sinaliza que o lead foi qualificado e autoriza transição para coleta cadastral."""
    return {"status": "qualificado", "motivo": motivo_qualificacao}


def acionar_transbordo(motivo: str) -> dict[str, Any]:
    """Transfere o atendimento imediatamente para um advogado humano."""
    return {"status": "transbordo_acionado", "motivo": motivo}


def gerar_contrato_zapsign(dados_contrato: dict[str, Any]) -> dict[str, Any]:
    """Aciona a emissão de contrato e procuração na ZapSign."""
    return {"status": "contrato_solicitado", "dados": dados_contrato}

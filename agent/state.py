"""Definição do estado conversacional do agente (StateGraph TypedDict)."""

from typing import Any, Literal

from typing_extensions import TypedDict

FaseLead = Literal[
    "triagem",  # IA qualificando o caso trabalhista
    "coleta",  # IA coletando dados para o contrato
    "aguardando_assinatura",  # Contrato enviado via ZapSign, aguardando assinatura
    "transbordo",  # Transferido para advogado humano
    "concluido",  # Contrato assinado e cadastrado no ADVBOX e Kommo
]


class LeadState(TypedDict, total=False):
    """Estrutura de dados persistida pelo LangGraph para cada conversa."""

    messages: list[Any]
    telefone: str
    lead_id: str | None
    contato_id: str | None
    fase: FaseLead
    humano_ativo: bool
    dados_triagem: dict[str, Any]
    dados_contrato: dict[str, Any]
    zapsign_doc_token: str | None
    zapsign_sign_url: str | None
    advbox_customer_id: str | None
    advbox_lawsuit_id: str | None
    motivo_transbordo: str | None

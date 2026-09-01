"""Ferramentas (tools) acionáveis pelo modelo LLM e pelo grafo de estados no LangGraph."""

from typing import Any

from langchain_core.tools import tool

from agent.state import FichaTrabalhista, formatar_ficha_oficial


@tool
def qualificar_lead(
    motivo_qualificacao: str,
    ficha: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Qualifica o lead trabalhista como viável e atualiza a Ficha Trabalhista."""
    return {
        "status": "qualificado",
        "motivo": motivo_qualificacao,
        "ficha": ficha or {},
    }


@tool
def registrar_inviabilidade(motivo: str, explicacao_cliente: str = "") -> dict[str, Any]:
    """Registra o caso como inviável juridicamente (ex: prescrição bienal > 2 anos)."""
    return {
        "status": "inviavel",
        "motivo": motivo,
        "explicacao_cliente": explicacao_cliente,
    }


@tool
def aceitar_oferta_contrato(confirmado: bool = True, observacoes: str = "") -> dict[str, Any]:
    """Registra o aceite do cliente à proposta de honorários para envio do contrato."""
    return {
        "status": "aceito" if confirmado else "recusado",
        "confirmado": confirmado,
        "observacoes": observacoes,
    }


@tool
def atualizar_kommo(lead_id: str | int, etapa: str | int) -> dict[str, Any]:
    """Atualiza o status ou etapa de um lead no Kommo CRM."""
    return {
        "status": "updated",
        "lead_id": str(lead_id),
        "etapa": str(etapa),
    }


@tool
def acionar_transbordo(motivo: str) -> dict[str, Any]:
    """Transfere o atendimento imediatamente para um advogado humano, silenciando o bot."""
    return {
        "status": "transbordo_acionado",
        "motivo": motivo,
        "humano_ativo": True,
    }


@tool
def gerar_ficha_oficial(
    ficha: dict[str, Any],
    parecer: str = "Caso viável com benefício econômico identificado.",
) -> str:
    """Compila a Ficha de Qualificação Trabalhista no formato oficial da Dra. Lívia França."""
    typed_ficha: FichaTrabalhista = ficha  # type: ignore[assignment]
    return formatar_ficha_oficial(typed_ficha, parecer=parecer)


# Tools de retrocompatibilidade
@tool
def iniciar_coleta(motivo_qualificacao: str) -> dict[str, Any]:
    """Sinaliza que o lead foi qualificado e autoriza transição para oferta/coleta."""
    return {"status": "qualificado", "motivo": motivo_qualificacao}


@tool
def gerar_contrato_zapsign(dados_contrato: dict[str, Any]) -> dict[str, Any]:
    """Aciona a emissão de contrato e procuração na ZapSign."""
    return {"status": "contrato_solicitado", "dados": dados_contrato}

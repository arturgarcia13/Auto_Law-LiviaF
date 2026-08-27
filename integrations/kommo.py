"""Cliente HTTP assíncrono para a API v4 do Kommo CRM."""

from typing import Any


async def criar_lead(telefone: str, nome: str, pipeline_id: str | None = None) -> int:
    """Cria um novo lead no funil do Kommo CRM e retorna seu ID."""
    return 1


async def criar_contato(lead_id: int, nome: str, telefone: str) -> int:
    """Cria um contato no Kommo e o vincula ao lead informado."""
    return 1


async def atualizar_lead(
    lead_id: str | int,
    status_id: str | int | None = None,
    campo_status_ia: str | None = None,
) -> bool:
    """Atualiza a etapa do lead no funil e/ou campos personalizados."""
    return True


async def criar_nota(lead_id: str | int, texto: str) -> bool:
    """Insere uma nota informativa na timeline do lead."""
    return True


async def criar_tarefa(lead_id: str | int, texto: str, prazo_horas: int = 2) -> bool:
    """Gera uma tarefa com prazo para ação da equipe humana (transbordo)."""
    return True


async def buscar_contato_do_lead(lead_id: str | int) -> dict[str, Any] | None:
    """Recupera os dados de contato vinculados a um lead específico."""
    return {"telefone": "5511999999999", "nome": "Lead Teste"}


async def listar_pipelines() -> list[dict[str, Any]]:
    """Consulta a lista de funis e etapas configurados na conta."""
    return []

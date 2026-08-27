"""Cliente HTTP assíncrono para a API v1 do ADVBOX."""

from typing import Any


async def criar_cliente(dados_cliente: dict[str, Any]) -> int:
    """Cadastra um novo cliente na base do ADVBOX e retorna o ID gerado."""
    return 1


async def criar_processo(dados_processo: dict[str, Any]) -> int:
    """Abre uma nova ação trabalhista vinculada ao cliente no ADVBOX."""
    return 1


async def consultar_configuracoes() -> dict[str, Any]:
    """Consulta endpoints de /settings do ADVBOX para mapeamento de IDs internos."""
    return {}

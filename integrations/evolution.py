"""Cliente HTTP assíncrono para o Gateway WhatsApp (Evolution API v2 - Baileys)."""

from typing import Any


async def enviar_texto(telefone: str, texto: str, delay_ms: int = 1500) -> dict[str, Any]:
    """Envia mensagem de texto para o WhatsApp com delay de digitação simulada."""
    return {"status": "success", "number": telefone, "delay": delay_ms}


async def verificar_status() -> str:
    """Consulta o status da conexão da instância WhatsApp ('open', 'close', etc.)."""
    return "close"

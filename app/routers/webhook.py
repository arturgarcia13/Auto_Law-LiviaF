"""Router para recepção de webhooks de mensagens do WhatsApp (Evolution API)."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/message")
async def receber_mensagem(payload: dict[str, Any]) -> dict[str, str]:
    """Endpoint receptor de eventos de mensageria da Evolution API (MESSAGES_UPSERT)."""
    return {"status": "ok"}

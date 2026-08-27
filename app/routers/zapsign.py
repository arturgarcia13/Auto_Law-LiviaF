"""Router para recepção de webhooks da ZapSign (eventos de assinatura eletrônica)."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["zapsign"])


@router.post("/webhook/zapsign")
async def zapsign_webhook(payload: dict[str, Any]) -> dict[str, str]:
    """Endpoint receptor de eventos da ZapSign (doc_signed)."""
    return {"status": "ok"}

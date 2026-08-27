"""Router para recepção de webhooks do Kommo CRM (eventos de leads e tarefas)."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["kommo"])


@router.post("/webhook/kommo")
async def kommo_webhook(payload: dict[str, Any]) -> dict[str, str]:
    """Endpoint receptor de eventos do Kommo CRM (mudança de etapa e conclusão de transbordo)."""
    return {"status": "ok"}

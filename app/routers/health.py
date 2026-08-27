"""Router de verificação de saúde e disponibilidade dos serviços (Health Check)."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/ping")
async def ping() -> dict[str, str]:
    """Endpoint leve para probes de liveness do Docker e orquestradores."""
    return {"status": "pong"}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Verificação completa de disponibilidade dos subsistemas (API, WhatsApp, Banco)."""
    # Verificação do status real da Evolution API será conectada no Sprint 6
    return {
        "api": "ok",
        "whatsapp": "not_configured",
        "whatsapp_conectado": False,
    }

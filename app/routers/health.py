"""Router de verificação de saúde e disponibilidade dos serviços (Health Check)."""

import os
from typing import Any

from fastapi import APIRouter, Request

from integrations.kommo import verificar_status_kommo
from integrations.meta import verificar_status_meta

router = APIRouter(tags=["health"])


@router.get("/health/ping")
async def ping() -> dict[str, str]:
    """Endpoint leve para probes de liveness do Docker e orquestradores."""
    return {"status": "pong"}


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Verificação completa de disponibilidade dos subsistemas (API, Banco, Redis, Kommo, Meta)."""
    app_state = getattr(request.app, "state", None)

    # 1. Verificação do Redis
    redis_status = "not_configured"
    redis_client = app_state and getattr(app_state, "redis", None)
    if redis_client:
        try:
            pong = await redis_client.ping()
            redis_status = "ok" if pong else "error"
        except Exception:
            redis_status = "error"
    elif os.getenv("REDIS_URL"):
        redis_status = "configured"

    # 2. Verificação do PostgreSQL / Checkpointer
    postgres_status = "not_configured"
    db_pool = app_state and getattr(app_state, "db_pool", None)
    if db_pool:
        try:
            postgres_status = "ok"
        except Exception:
            postgres_status = "error"
    elif os.getenv("DATABASE_URL"):
        postgres_status = "configured"

    # 3. Verificação do Kommo CRM
    kommo_info = await verificar_status_kommo()
    kommo_status = kommo_info.get("status", "not_configured")

    # 4. Verificação da Meta WhatsApp Cloud API
    meta_info = await verificar_status_meta()
    meta_status = meta_info.get("status", "not_configured")

    return {
        "status": "ok",
        "api": "ok",
        "postgres": postgres_status,
        "redis": redis_status,
        "kommo": kommo_status,
        "meta": meta_status,
        "version": "0.2.0",
    }


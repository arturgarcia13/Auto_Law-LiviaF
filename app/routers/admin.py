"""Router administrativo para auditoria, inspeção e gestão de webhooks do Kommo CRM."""

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.schemas.admin_webhook import (
    WebhookActionResponse,
    WebhookCreateRequest,
    WebhookDeleteRequest,
    WebhookSyncRequest,
    WebhookUpdateRequest,
    WebhookVerifyResponse,
)
from integrations.kommo import (
    DEFAULT_WEBHOOK_EVENTS,
    KOMMO_AVAILABLE_WEBHOOK_EVENTS,
    criar_webhook,
    garantir_webhook_ativo,
    listar_webhooks,
    modificar_webhook_permissoes,
    remover_webhook,
    testar_ping_webhook,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _validar_admin_token(
    token_query: str | None = None,
    x_api_key: str | None = None,
    authorization: str | None = None,
    x_kommo_secret: str | None = None,
) -> bool:
    """Valida se o token fornecido confere com ADMIN_SECRET_TOKEN ou KOMMO_WEBHOOK_SECRET."""
    admin_token = (os.getenv("ADMIN_SECRET_TOKEN") or "").strip()
    webhook_secret = (os.getenv("KOMMO_WEBHOOK_SECRET") or "").strip()

    valid_tokens = {t for t in (admin_token, webhook_secret) if t}
    if not valid_tokens:
        return True

    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization[7:].strip()

    candidatos = {
        token_query.strip() if token_query else "",
        x_api_key.strip() if x_api_key else "",
        x_kommo_secret.strip() if x_kommo_secret else "",
        bearer_token,
    }
    return any(c in valid_tokens for c in candidatos if c)


def _verificar_autenticacao(
    token: str = "",
    x_api_key: str | None = None,
    authorization: str | None = None,
    x_kommo_secret: str | None = None,
) -> None:
    if not _validar_admin_token(
        token_query=token,
        x_api_key=x_api_key,
        authorization=authorization,
        x_kommo_secret=x_kommo_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação administrativa ausente ou inválido.",
        )


# ==============================================================================
# Endpoints de Gestão de Webhooks do Kommo CRM
# ==============================================================================


@router.get("/kommo/webhooks", response_model=WebhookActionResponse)
async def admin_listar_webhooks(
    destination: str | None = Query(
        default=None, description="Filtrar por URL de destino específica"
    ),
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> WebhookActionResponse:
    """Lista todos os webhooks registrados na conta Kommo CRM."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    webhooks = await listar_webhooks(destination=destination)
    return WebhookActionResponse(
        ok=True,
        status="ok",
        message=f"{len(webhooks)} webhook(s) encontrado(s).",
        destination=destination,
        data=webhooks,
    )


@router.get("/kommo/webhooks/events")
async def admin_listar_eventos_suportados(
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Retorna os eventos suportados pela API v4 do Kommo CRM e o conjunto padrão."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    return {
        "default_events": DEFAULT_WEBHOOK_EVENTS,
        "available_events": KOMMO_AVAILABLE_WEBHOOK_EVENTS,
    }


@router.post("/kommo/webhooks", response_model=WebhookActionResponse)
async def admin_criar_webhook(
    body: WebhookCreateRequest,
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> WebhookActionResponse:
    """Insere um novo webhook na plataforma Kommo CRM."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    res = await criar_webhook(destination=body.destination, events=body.events)
    if not res.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha ao registrar webhook na Kommo: {res.get('error') or res.get('data')}",
        )
    return WebhookActionResponse(
        ok=True,
        status="created",
        message="Webhook inserido com sucesso na Kommo CRM.",
        destination=body.destination,
        data=res,
    )


@router.put("/kommo/webhooks", response_model=WebhookActionResponse)
async def admin_modificar_webhook(
    body: WebhookUpdateRequest,
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> WebhookActionResponse:
    """Modifica os eventos/permissões de um webhook existente na Kommo CRM."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    res = await modificar_webhook_permissoes(destination=body.destination, events=body.events)
    if not res.get("ok"):
        err_msg = res.get("create_step", {}).get("error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha ao modificar permissões do webhook: {err_msg}",
        )
    return WebhookActionResponse(
        ok=True,
        status="updated",
        message="Permissões do webhook modificadas com sucesso.",
        destination=body.destination,
        data=res,
    )


@router.delete("/kommo/webhooks", response_model=WebhookActionResponse)
async def admin_remover_webhook(
    body: WebhookDeleteRequest,
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> WebhookActionResponse:
    """Remove a subscrição de um webhook na plataforma Kommo CRM."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    res = await remover_webhook(destination=body.destination)
    return WebhookActionResponse(
        ok=res.get("ok", False),
        status="deleted" if res.get("ok") else "error",
        message="Webhook removido com sucesso." if res.get("ok") else "Falha ao remover webhook.",
        destination=body.destination,
        data=res,
    )


@router.get("/kommo/webhooks/verify", response_model=WebhookVerifyResponse)
async def admin_verificar_webhook(
    destination: str = Query(..., description="URL de destino a ser verificada"),
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> WebhookVerifyResponse:
    """Audita a integridade do webhook: presença no CRM, status e ping local/túnel."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)
    webhooks = await listar_webhooks(destination=destination)
    ping = await testar_ping_webhook(destination)

    registrado = len(webhooks) > 0
    webhook_obj = webhooks[0] if registrado else {}
    desativado = webhook_obj.get("disabled", False)
    eventos = webhook_obj.get("settings", [])

    is_ok = registrado and (not desativado) and ping.get("ok", False)
    status_str = "healthy" if is_ok else "unhealthy"

    return WebhookVerifyResponse(
        ok=is_ok,
        status=status_str,
        destination=destination,
        registered=registrado,
        disabled=desativado,
        events=eventos,
        ping=ping,
        details=webhook_obj,
    )


@router.post("/kommo/webhooks/sync")
async def admin_sync_auto_cura_webhook(
    body: WebhookSyncRequest,
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Executa a rotina de auto-cura: verifica, remove se inválido, reinsere e re-testa."""
    _verificar_autenticacao(token=token, x_api_key=x_api_key, authorization=authorization)

    destination = body.destination
    if not destination:
        domain = (os.getenv("NGROK_DOMAIN") or "").strip()
        secret = (os.getenv("KOMMO_WEBHOOK_SECRET") or "").strip()
        if domain:
            scheme = "https://" if not domain.startswith("http") else ""
            query = f"?token={secret}" if secret else ""
            destination = f"{scheme}{domain}/kommo/webhook{query}"

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination não informada e não foi possível derivar de NGROK_DOMAIN no .env",
        )

    res = await garantir_webhook_ativo(destination=destination, required_events=body.events)
    return res


# ==============================================================================
# Endpoints Legados de Inspeção de Conversa
# ==============================================================================


@router.get("/conversation/{telefone}")
async def inspecionar_conversa(telefone: str) -> dict[str, Any]:
    """Inspeciona o estado atual de um lead pelo número de telefone."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )


@router.post("/conversation/{telefone}/reset")
async def resetar_conversa(telefone: str) -> dict[str, Any]:
    """Reseta o estado da conversa e limpa pendências de transbordo."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )


@router.post("/conversation/{telefone}/reativar-bot")
async def reativar_bot(telefone: str) -> dict[str, Any]:
    """Reativa o atendimento automatizado da IA para o lead."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )

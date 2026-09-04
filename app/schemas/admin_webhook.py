"""Schemas Pydantic v2 para administração e auto-cura de webhooks no Kommo CRM."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreateRequest(BaseModel):
    """Payload para registro de um novo webhook na Kommo."""

    model_config = ConfigDict(extra="ignore")

    destination: str = Field(
        ...,
        description="URL de destino completa do webhook",
        examples=["https://exemplo.ngrok-free.dev/kommo/webhook?token=teste123"],
    )
    events: list[str] = Field(
        default=["add_message"],
        description="Lista de eventos a serem inscritos",
        examples=[["add_message"]],
    )


class WebhookUpdateRequest(BaseModel):
    """Payload para alteração de permissões/eventos de webhook existente."""

    model_config = ConfigDict(extra="ignore")

    destination: str = Field(
        ...,
        description="URL de destino do webhook a ser modificado",
    )
    events: list[str] = Field(
        ...,
        description="Nova lista completa de eventos desejados",
        examples=[["add_message"]],
    )


class WebhookDeleteRequest(BaseModel):
    """Payload para exclusão de webhook na Kommo."""

    model_config = ConfigDict(extra="ignore")

    destination: str = Field(
        ...,
        description="URL de destino do webhook a ser removido",
    )


class WebhookSyncRequest(BaseModel):
    """Payload para sincronização e auto-cura de webhook."""

    model_config = ConfigDict(extra="ignore")

    destination: str | None = Field(
        default=None,
        description="URL de destino opcional (se omitida, tenta derivar do ambiente)",
    )
    events: list[str] = Field(
        default=["add_message"],
        description="Eventos exigidos que devem estar ativos",
    )


class WebhookActionResponse(BaseModel):
    """Resposta padrão para ações de webhook."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    status: str
    message: str | None = None
    destination: str | None = None
    data: dict[str, Any] | list[Any] | None = None


class WebhookVerifyResponse(BaseModel):
    """Resposta estruturada de auditoria e verificação de webhook."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    status: str
    destination: str
    registered: bool
    disabled: bool = False
    events: list[str] = Field(default_factory=list)
    ping: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] | None = None

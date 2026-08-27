"""Schemas de validação para payloads e webhooks do Kommo CRM."""

from typing import Any

from pydantic import BaseModel, Field


class KommoWebhookPayload(BaseModel):
    """Payload de webhooks enviado pelo Kommo CRM."""

    leads: dict[str, list[dict[str, Any]]] | None = Field(default=None)
    tasks: dict[str, list[dict[str, Any]]] | None = Field(default=None)
    contacts: dict[str, list[dict[str, Any]]] | None = Field(default=None)

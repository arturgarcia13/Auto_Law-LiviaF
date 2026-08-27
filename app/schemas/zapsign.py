"""Schemas de validação para payloads e webhooks da ZapSign."""

from typing import Any

from pydantic import BaseModel, Field


class ZapSignSigner(BaseModel):
    """Signatário do documento ZapSign."""

    token: str
    name: str
    email: str | None = None
    phone_number: str | None = None
    status: str | None = None


class ZapSignDocument(BaseModel):
    """Informações do documento emitido na ZapSign."""

    token: str
    name: str
    status: str
    signers: list[ZapSignSigner] = Field(default_factory=list)


class ZapSignWebhookPayload(BaseModel):
    """Payload recebido via webhook quando ocorrem eventos no documento."""

    event_type: str | None = Field(default=None, alias="event")
    document: ZapSignDocument | dict[str, Any] | None = None

    @property
    def doc_token(self) -> str | None:
        """Extrai o token identificador do documento."""
        if isinstance(self.document, ZapSignDocument):
            return self.document.token
        if isinstance(self.document, dict):
            return self.document.get("token")
        return None

"""Schemas Pydantic para webhooks da Evolution API (WhatsApp)."""

from typing import Any

from pydantic import BaseModel, Field


class MessageKey(BaseModel):
    """Chave identificadora da mensagem no WhatsApp."""

    remoteJid: str = Field(
        ..., description="Identificador WhatsApp (ex: 5511999999999@s.whatsapp.net)"
    )
    fromMe: bool = Field(
        ..., description="Indica se a mensagem foi enviada pelo próprio bot/escritório"
    )
    id: str = Field(..., description="ID único da mensagem")


class MessageContent(BaseModel):
    """Conteúdo textual ou de mídia da mensagem."""

    conversation: str | None = Field(default=None, description="Texto da mensagem")
    audioMessage: dict[str, Any] | None = Field(
        default=None, description="Metadados de áudio se houver"
    )
    imageMessage: dict[str, Any] | None = Field(
        default=None, description="Metadados de imagem se houver"
    )


class EvolutionData(BaseModel):
    """Corpo de dados do evento MESSAGES_UPSERT."""

    key: MessageKey
    pushName: str | None = Field(
        default=None, description="Nome do perfil do remetente no WhatsApp"
    )
    message: MessageContent
    messageType: str
    messageTimestamp: int


class EvolutionWebhookPayload(BaseModel):
    """Payload completo enviado pela Evolution API."""

    event: str
    instance: str
    data: EvolutionData

    @property
    def telefone(self) -> str:
        """Extrai o número puro de telefone sem o sufixo @s.whatsapp.net."""
        return self.data.key.remoteJid.replace("@s.whatsapp.net", "").replace("@g.us", "")

    @property
    def texto(self) -> str | None:
        """Retorna o texto da mensagem."""
        return self.data.message.conversation

    @property
    def e_minha_mensagem(self) -> bool:
        """Indica se a mensagem foi originada pelo próprio bot."""
        return self.data.key.fromMe

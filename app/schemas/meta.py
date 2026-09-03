"""Schemas de validação Pydantic v2 para disparo de mensagens e templates via Meta Cloud API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    """Payload para requisição de envio de mensagem ou template pelo endpoint /send."""

    model_config = ConfigDict(extra="ignore")

    to: str | None = Field(
        default=None,
        description="Número de telefone do destinatário com DDI (ex: 5585984347149)",
    )
    lead_id: int | None = Field(
        default=None,
        description="ID do lead no Kommo CRM para registro da nota após o envio",
    )
    text: str | None = Field(
        default=None,
        description="Texto da mensagem simples a ser enviada",
    )
    template_name: str | None = Field(
        default=None,
        description="Nome do template pré-aprovado na Meta Cloud API",
    )
    template_lang: str = Field(
        default="pt_BR",
        description="Código do idioma do template (padrão: pt_BR)",
    )
    params: list[str] | None = Field(
        default=None,
        description="Parâmetros para preenchimento dos campos do template",
    )


class SendMessageResponse(BaseModel):
    """Resposta da operação de envio."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = Field(description="Indica se a mensagem foi enviada com sucesso pela Meta")
    result: dict[str, Any] = Field(description="Retorno detalhado da Meta Cloud API")
    note: dict[str, Any] | None = Field(
        default=None,
        description="Status do registro da nota no lead do Kommo CRM",
    )

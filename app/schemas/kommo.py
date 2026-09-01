"""Schemas de validação Pydantic v2 para payloads e webhooks do Kommo CRM."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KommoMessageContent(BaseModel):
    """Conteúdo de uma mensagem recebida ou enviada no Kommo."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(
        default="text",
        description="Tipo de mensagem: text, voice, audio, picture, file, location, contact",
    )
    text: str | None = Field(default=None, description="Texto da mensagem")
    media: str | None = Field(
        default=None, description="URL pública ou token de download do arquivo/áudio"
    )
    duration: int | None = Field(
        default=None, description="Duração do áudio em segundos, se aplicável"
    )
    file_name: str | None = Field(default=None, description="Nome original do arquivo enviado")


class KommoSender(BaseModel):
    """Dados do remetente da mensagem no Kommo (cliente ou operador humano)."""

    model_config = ConfigDict(extra="ignore")

    id: str | int | None = Field(default=None, description="ID do remetente no Kommo")
    name: str | None = Field(default=None, description="Nome do remetente")
    phone: str | None = Field(default=None, description="Telefone formatado ou bruto do remetente")
    email: str | None = Field(default=None, description="E-mail do remetente")
    avatar: str | None = Field(default=None, description="URL do avatar do remetente")
    is_client: bool = Field(
        default=True,
        description="True se enviado pelo lead/cliente, False se enviado pelo escritório/bot",
    )


class KommoContact(BaseModel):
    """Dados de contato cadastrado ou atualizado no Kommo CRM."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = Field(default=None, description="ID do contato no Kommo")
    name: str | None = Field(default=None, description="Nome completo do contato")
    first_name: str | None = Field(default=None, description="Primeiro nome")
    last_name: str | None = Field(default=None, description="Sobrenome")
    responsible_user_id: int | None = Field(default=None, description="ID do usuário responsável")
    custom_fields_values: list[dict[str, Any]] | None = Field(
        default=None, description="Campos personalizados do contato"
    )


class KommoTask(BaseModel):
    """Dados de tarefa de transbordo ou ação operacional no Kommo CRM."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = Field(default=None, description="ID da tarefa no Kommo")
    element_id: int | None = Field(default=None, description="ID do lead ou contato vinculado")
    element_type: int | str | None = Field(default=None, description="Tipo do elemento (2 = lead)")
    complete_till: int | None = Field(
        default=None, description="Timestamp limite de conclusão da tarefa"
    )
    task_type_id: int | None = Field(default=None, description="Tipo da tarefa")
    text: str | None = Field(
        default=None, description="Descrição da tarefa ou motivo de transbordo"
    )
    responsible_user_id: int | None = Field(default=None, description="ID do responsável designado")
    is_completed: bool | None = Field(default=None, description="Status de conclusão da tarefa")


class KommoLead(BaseModel):
    """Dados de lead ou oportunidade no funil do Kommo CRM."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = Field(default=None, description="ID único do lead no CRM")
    name: str | None = Field(default=None, description="Título/nome do card do lead")
    status_id: int | None = Field(default=None, description="ID da etapa do funil")
    pipeline_id: int | None = Field(default=None, description="ID do funil de vendas")
    price: int | float | None = Field(default=None, description="Valor estimado da causa/negócio")
    responsible_user_id: int | None = Field(default=None, description="ID do corretor/advogado")
    custom_fields_values: list[dict[str, Any]] | None = Field(
        default=None, description="Campos personalizados"
    )


class KommoMessagePayload(BaseModel):
    """Payload de evento de mensagem recebida via Kommo Chats / Talks API."""

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="new_message", description="Tipo do evento de mensageria")
    chat_id: str | None = Field(default=None, description="ID da conversa no Kommo Talks")
    talk_id: str | int | None = Field(default=None, description="ID do talk associado")
    lead_id: str | int | None = Field(default=None, description="ID do lead associado no CRM")
    sender: KommoSender | None = Field(default=None, description="Remetente da mensagem")
    message: KommoMessageContent = Field(
        default_factory=KommoMessageContent, description="Conteúdo textual ou mídia da mensagem"
    )
    phone: str | None = Field(default=None, description="Número de telefone do contato")
    conversation_id: str | None = Field(default=None, description="ID da conversa externa")

    @property
    def telefone_normalizado(self) -> str:
        """Extrai apenas os dígitos numéricos do telefone do lead."""
        raw = self.phone or (self.sender.phone if self.sender else "") or ""
        return "".join(c for c in raw if c.isdigit())

    @property
    def e_audio(self) -> bool:
        """Indica se a mensagem recebida é uma gravação de voz ou áudio."""
        return self.message.type in ("voice", "audio", "ptt") or bool(
            self.message.media and not self.message.text
        )

    @property
    def texto(self) -> str | None:
        """Retorna o texto da mensagem se houver."""
        return self.message.text

    @property
    def e_minha_mensagem(self) -> bool:
        """Indica se a mensagem foi enviada pelo próprio bot ou operador do escritório."""
        if self.sender is not None:
            return not self.sender.is_client
        return False


class KommoWebhookPayload(BaseModel):
    """Payload recebido pelos webhooks padrão e de mensageria do Kommo CRM."""

    model_config = ConfigDict(extra="ignore")

    event_type: str | None = Field(default=None, description="Tipo do evento recebido")
    leads: dict[str, list[dict[str, Any]]] | None = Field(
        default=None, description="Eventos de leads (add, status, update, etc.)"
    )
    tasks: dict[str, list[dict[str, Any]]] | None = Field(
        default=None, description="Eventos de tarefas (add, update, complete)"
    )
    contacts: dict[str, list[dict[str, Any]]] | None = Field(
        default=None, description="Eventos de contatos (add, update)"
    )
    message: KommoMessagePayload | dict[str, Any] | None = Field(
        default=None, description="Evento de mensagem unitária se houver"
    )
    messages: list[KommoMessagePayload] | None = Field(
        default=None, description="Lista de eventos de mensagem recebidos"
    )


def is_chat_permitido(
    chat_id: str | int | None = None,
    talk_id: str | int | None = None,
    telefone: str | None = None,
) -> bool:
    """Verifica se o chat_id, talk_id ou telefone está na lista de permissão (whitelist).

    Se ALLOWED_CHAT_IDS não estiver configurada no ambiente (ou for '*' ou vazia),
    permite todos os chats (modo produção).
    Se configurada (ex: ALLOWED_CHAT_IDS=20429066 ou ALLOWED_CHAT_IDS=20429066,20429067),
    apenas os identificadores listados serão processados.
    """
    import os

    allowed_env = (os.getenv("ALLOWED_CHAT_IDS") or "").strip()
    if not allowed_env or allowed_env == "*":
        return True

    allowed_set = {x.strip() for x in allowed_env.split(",") if x.strip()}

    candidatos = [
        str(chat_id).strip() if chat_id is not None else "",
        str(talk_id).strip() if talk_id is not None else "",
        str(telefone).strip() if telefone is not None else "",
    ]
    return any(c in allowed_set for c in candidatos if c)


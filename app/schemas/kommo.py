"""Schemas de validação Pydantic v2 para payloads e webhooks do Kommo CRM."""

import os
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def normalize_phone(raw: str | None) -> str | None:
    """Normaliza o número de telefone extraindo apenas dígitos e garantindo o DDI 55."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    if len(digits) >= 10:
        return f"55{digits}"
    return digits


def is_phone_allowed(phone: str | None) -> bool:
    """Verifica se o telefone está na lista de permissão (ALLOWED_PHONES).

    Se ALLOWED_PHONES não estiver configurada no ambiente (ou for '*' ou vazia),
    permite todos os números (modo produção).
    Se configurada (ex: ALLOWED_PHONES=5585984347149,558596967995),
    apenas os números listados serão aceitos.
    """
    allowed_env = (os.getenv("ALLOWED_PHONES") or "").strip()
    if not allowed_env or allowed_env == "*":
        return True

    normalized_target = normalize_phone(phone)
    if not normalized_target:
        return False

    allowed_list = [normalize_phone(x.strip()) for x in allowed_env.split(",") if x.strip()]
    return normalized_target in [x for x in allowed_list if x]


def is_chat_allowed(chat_id: str | int | None) -> bool:
    """Verifica se o chat_id está explicitamente na lista de permissão ALLOWED_CHAT_ID(S)."""
    if not chat_id:
        return False
    env_str = f"{os.getenv('ALLOWED_CHAT_IDS', '')},{os.getenv('ALLOWED_CHAT_ID', '')}".strip(",")
    if not env_str:
        return False
    allowed_set = {c.strip() for c in env_str.split(",") if c.strip()}
    return str(chat_id).strip() in allowed_set


def is_allowed(
    chat_id: str | int | None = None,
    phone: str | None = None,
    lead_id: str | int | None = None,
) -> bool:
    """Valida se o evento de teste está permitido via ALLOWED_CHAT_ID(S) ou ALLOWED_PHONES."""
    if chat_id and is_chat_allowed(chat_id):
        return True
    if lead_id and is_chat_allowed(str(lead_id)):
        return True
    if phone and is_phone_allowed(phone):
        return True

    # Se nenhuma das restrições foi configurada no .env, opera em modo aberto
    has_chat_env = bool(
        (os.getenv("ALLOWED_CHAT_IDS") or os.getenv("ALLOWED_CHAT_ID") or "").strip()
    )
    has_phone_env = bool((os.getenv("ALLOWED_PHONES") or "").strip())
    if not has_chat_env and not has_phone_env:
        return True

    return False


def is_chat_permitido(
    chat_id: str | int | None = None,
    talk_id: str | int | None = None,
    telefone: str | None = None,
) -> bool:
    """Helper de compatibilidade retrocompatível."""
    return is_allowed(chat_id=chat_id, phone=telefone)


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
    """Payload de evento de mensagem recebida via Kommo CRM."""

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="new_message", description="Tipo do evento de mensageria")
    message_id: str | None = Field(
        default=None, description="ID único da mensagem no Kommo CRM"
    )
    chat_id: str | None = Field(default=None, description="ID da conversa no Kommo")
    talk_id: str | int | None = Field(default=None, description="ID do talk associado")
    lead_id: str | int | None = Field(default=None, description="ID do lead associado no CRM")
    contact_id: str | int | None = Field(default=None, description="ID do contato associado no CRM")
    sender: KommoSender | None = Field(default=None, description="Remetente da mensagem")
    message: KommoMessageContent = Field(
        default_factory=KommoMessageContent, description="Conteúdo textual ou mídia da mensagem"
    )
    phone: str | None = Field(default=None, description="Número de telefone do contato")
    conversation_id: str | None = Field(default=None, description="ID da conversa externa")

    @property
    def telefone_normalizado(self) -> str:
        """Extrai o telefone normalizado com DDI."""
        raw = self.phone or (self.sender.phone if self.sender else "") or ""
        normalized = normalize_phone(raw)
        return normalized or ""

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

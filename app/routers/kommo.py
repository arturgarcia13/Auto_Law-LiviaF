"""Router para recepção e processamento de webhooks do Kommo CRM."""

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Request

from app.schemas.kommo import (
    KommoMessageContent,
    KommoMessagePayload,
    KommoSender,
    KommoWebhookPayload,
    is_chat_permitido,
)
from app.services.audio import transcrever_audio
from app.services.buffer import agrupar_mensagens
from integrations.kommo import enviar_mensagem

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kommo"])


def _unflatten_form_data(form_dict: dict[str, Any]) -> dict[str, Any]:
    """Converte chaves form-urlencoded do Kommo (ex: message[add][0][text]) em dict aninhado de forma segura."""
    result: dict[str, Any] = {}
    for key, value in form_dict.items():
        parts = re.findall(r"[^\[\]]+", key)
        if not parts:
            result[key] = value
            continue
        curr: dict[str, Any] = result
        for part in parts[:-1]:
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]
        curr[parts[-1]] = value

    return result


async def extrair_payload_request(
    request: Request,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extrai e normaliza o payload do request independentemente do Content-Type."""
    if payload is not None and isinstance(payload, dict) and payload:
        return payload

    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            dados = await request.json()
            if isinstance(dados, dict):
                return dados
        except Exception:
            pass

    try:
        form = await request.form()
        if form:
            return _unflatten_form_data(dict(form))
    except Exception:
        pass

    try:
        raw_body = await request.body()
        if raw_body:
            import urllib.parse

            decoded = raw_body.decode("utf-8", errors="ignore").strip()
            if decoded.startswith("{") or decoded.startswith("["):
                dados = json.loads(decoded)
                if isinstance(dados, dict):
                    return dados
            elif "=" in decoded:
                parsed_qs = urllib.parse.parse_qs(decoded)
                flat = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}
                return _unflatten_form_data(flat)
    except Exception:
        pass

    return dict(request.query_params)


def _normalizar_item_mensagem(
    item: dict[str, Any],
    parent_dados: dict[str, Any] | None = None,
) -> KommoMessagePayload | None:
    """Normaliza um dicionário de mensagem do Kommo em um KommoMessagePayload estruturado."""
    parent = parent_dados or {}
    text_val = item.get("text") or item.get("body") or item.get("conversation")
    media_val = item.get("media") or item.get("attachment") or item.get("mediaUrl")

    chat_id = str(
        item.get("chat_id")
        or item.get("talk_id")
        or parent.get("chat_id")
        or parent.get("talk_id")
        or item.get("conversation_id")
        or ""
    )
    phone = str(
        item.get("phone")
        or item.get("telefone")
        or parent.get("phone")
        or parent.get("telefone")
        or ""
    )
    lead_id = (
        item.get("element_id")
        or item.get("entity_id")
        or parent.get("element_id")
        or parent.get("entity_id")
    )

    raw_sender = item.get("sender") or parent.get("sender")
    raw_author = item.get("author") or parent.get("author")
    sender_obj = None
    if raw_sender and isinstance(raw_sender, dict):
        try:
            sender_obj = KommoSender.model_validate(raw_sender)
        except Exception:
            sender_obj = None
    elif raw_author and isinstance(raw_author, dict):
        is_client = True
        if str(raw_author.get("type", "")).lower() in ("internal", "user", "bot"):
            is_client = False
        sender_obj = KommoSender(
            id=str(raw_author.get("id", "")),
            name=str(raw_author.get("name", "")),
            is_client=is_client,
        )

    msg_type = str(item.get("type", item.get("message_type", "text")))
    if msg_type in ("incoming", "outgoing"):
        msg_type = "text"
    if media_val and not text_val and msg_type == "text":
        msg_type = (
            "voice"
            if any(ext in str(media_val) for ext in (".ogg", ".opus", ".mp3", ".wav", ".m4a"))
            else "media"
        )

    content = KommoMessageContent(
        type=msg_type,
        text=str(text_val) if text_val is not None else None,
        media=str(media_val) if media_val is not None else None,
    )

    if content.text or content.media or content.type in ("voice", "audio", "ptt"):
        return KommoMessagePayload(
            chat_id=chat_id if chat_id else None,
            talk_id=item.get("talk_id") or parent.get("talk_id"),
            lead_id=lead_id,
            phone=phone if phone else None,
            sender=sender_obj,
            message=content,
        )

    try:
        validated = KommoMessagePayload.model_validate(item)
        if validated.texto or validated.e_audio:
            return validated
    except Exception:
        pass

    return None


def extrair_mensagens_do_payload(dados: dict[str, Any]) -> list[KommoMessagePayload]:
    """Extrai todas as mensagens unitárias do payload em qualquer formato do Kommo CRM."""
    mensagens: list[KommoMessagePayload] = []

    # 1. Estruturas aninhadas do Kommo (ex: message[add], messages[add], message[update])
    for chave in ("message", "messages"):
        if chave in dados and isinstance(dados[chave], dict):
            sub_dict = dados[chave]
            for action in ("add", "update"):
                if action in sub_dict:
                    items = sub_dict[action]
                    if isinstance(items, dict):
                        items = list(items.values())
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                msg = _normalizar_item_mensagem(item, parent_dados=dados)
                                if msg:
                                    mensagens.append(msg)

    # 2. Objeto de mensagem unitária em dados["message"] direto
    if not mensagens and "message" in dados and isinstance(dados["message"], dict):
        msg_obj = dados["message"]
        if any(k in msg_obj for k in ("text", "body", "media", "attachment", "conversation")):
            msg = _normalizar_item_mensagem(msg_obj, parent_dados=dados)
            if msg:
                mensagens.append(msg)

    # 3. Formato direto no root (ex: webhook Talks/Evolution legado)
    if not mensagens:
        msg = _normalizar_item_mensagem(dados)
        if msg:
            mensagens.append(msg)

    return mensagens


async def processar_mensagem_kommo(
    msg_payload: KommoMessagePayload,
    app_state: Any = None,
) -> dict[str, Any]:
    """Processa uma mensagem unitária recebida do Kommo Talks/Chats."""
    if msg_payload.e_minha_mensagem:
        logger.info("ℹ️ [MENSAGEM BOT/OPERADOR] Mensagem própria ignorada (não é de cliente).")
        return {"status": "ignored", "reason": "outgoing_message"}

    telefone = msg_payload.telefone_normalizado
    chat_id = msg_payload.chat_id or msg_payload.talk_id or telefone

    logger.info(
        "📩 [NOVA MENSAGEM RECEBIDA] Chat ID: %s | Telefone: %s | Tipo: %s",
        chat_id,
        telefone or "N/A",
        msg_payload.message.type,
    )

    # Filtro de lista de permissão (Whitelist de Testes)
    if not is_chat_permitido(
        chat_id=msg_payload.chat_id,
        talk_id=msg_payload.talk_id,
        telefone=telefone,
    ):
        logger.warning(
            "🛑 [FILTRO ALLOWLIST] Chat=%s Tel=%s BLOQUEADO (fora de ALLOWED_CHAT_IDS).",
            chat_id,
            telefone,
        )
        return {
            "status": "ignored",
            "reason": "chat_not_in_allowlist",
            "chat_id": chat_id,
            "telefone": telefone,
        }

    logger.info("✅ [FILTRO ALLOWLIST] Chat ID=%s PERMITIDO para processamento.", chat_id)

    # 1. Obtenção do texto ou transcrição de áudio
    if msg_payload.e_audio and msg_payload.message.media:
        logger.info("🎙️ [ÁUDIO RECEBIDO] Iniciando transcrição via Google Gemini Flash STT...")
        transcricao = await transcrever_audio(msg_payload.message.media)
        texto_recebido = f"[Áudio Transcrito]: {transcricao}"
        logger.info("🎙️ [ÁUDIO TRANSCRIÇÃO SUCESSO] Texto: '%s'", transcricao)
    else:
        texto_recebido = msg_payload.texto or ""

    if not texto_recebido.strip():
        logger.warning("⚠️ [MENSAGEM VAZIA] Nenhum texto ou mídia extraído da mensagem.")
        return {"status": "ignored", "reason": "empty_message"}

    logger.info("💬 [MENSAGEM DO CLIENTE] '%s'", texto_recebido)

    # 2. Buffer Redis para agregação de rajadas
    texto_acumulado = await agrupar_mensagens(telefone, texto_recebido)
    if texto_acumulado != texto_recebido:
        logger.info("⏱️ [BUFFER RAJADA] Mensagens agrupadas: '%s'", texto_acumulado)

    thread_id = telefone or str(chat_id) or str(msg_payload.talk_id) or "default_thread"

    # 3. Invocação do agente de IA (LangGraph)
    resposta_ia = (
        "Olá! Sou a assistente jurídica da Dra. Lívia França. "
        "Recebi sua mensagem e estamos analisando seu caso."
    )
    if app_state and getattr(app_state, "graph", None):
        try:
            logger.info("🧠 [LANGGRAPH] Invocando agente para thread=%s...", thread_id)
            input_data = {
                "telefone": thread_id,
                "chat_id": chat_id,
                "lead_id": msg_payload.lead_id,
                "messages": [{"role": "user", "content": texto_acumulado}],
            }
            config = {"configurable": {"thread_id": thread_id}}
            graph_res = await app_state.graph.ainvoke(input_data, config=config)
            if isinstance(graph_res, dict):
                fase_pos = graph_res.get("fase", "analise_viabilidade")
                logger.info("📌 [LANGGRAPH ESTADO] Fase atual do funil: '%s'", fase_pos)
                if "messages" in graph_res and graph_res["messages"]:
                    last_msg = graph_res["messages"][-1]
                    if isinstance(last_msg, dict):
                        resposta_ia = str(last_msg.get("content") or "")
                    else:
                        resposta_ia = str(getattr(last_msg, "content", None) or last_msg)
        except Exception as exc:
            logger.error("❌ [LANGGRAPH ERRO] Falha ao invocar agente: %s", exc, exc_info=True)

    logger.info("🤖 [RESPOSTA DA IA — DRA. LÍVIA FRANÇA]:\n%s", resposta_ia)

    # 4. Envio da resposta via API de Mensageria do Kommo
    target_id = msg_payload.talk_id or chat_id
    if target_id:
        logger.info("📤 [ENVIANDO AO KOMMO] Disparando resposta para ID=%s...", target_id)
        recipient_id = str(msg_payload.sender.id) if (msg_payload.sender and msg_payload.sender.id) else None
        recipient_name = msg_payload.sender.name if msg_payload.sender else None
        retorno_envio = await enviar_mensagem(
            chat_id=target_id,
            texto=resposta_ia,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            recipient_phone=telefone,
        )
        status_envio = (
            retorno_envio.get("status", "ok") if isinstance(retorno_envio, dict) else "ok"
        )
        logger.info("✅ [RESPOSTA ENVIADA AO KOMMO] Status: %s", status_envio)

    return {
        "status": "ok",
        "text": resposta_ia,
        "message": resposta_ia,
        "messages": [
            {
                "type": "text",
                "text": resposta_ia,
            }
        ],
        "chat_id": chat_id,
        "telefone": telefone,
        "resposta": resposta_ia,
    }


@router.post("/webhook/kommo")
async def kommo_webhook(request: Request) -> dict[str, Any]:
    """Endpoint receptor principal de eventos e webhooks do Kommo CRM."""
    client_ip = request.client.host if request.client else "unknown"
    logger.info("⚡ [WEBHOOK INCOMING] POST /webhook/kommo | IP: %s", client_ip)

    dados = await extrair_payload_request(request)
    if not dados:
        logger.info("🤝 [WEBHOOK HANDSHAKE] Ping de verificação do Kommo recebido com sucesso.")
        return {"status": "ok", "event": "handshake_ping"}

    logger.info(
        "📦 [PAYLOAD RECEBIDO] %s",
        json.dumps(dados, ensure_ascii=False, default=str),
    )

    app_state = getattr(request.app, "state", None)

    # Extrai todas as mensagens contidas no payload (diretas ou aninhadas)
    mensagens = extrair_mensagens_do_payload(dados)
    if mensagens:
        if len(mensagens) == 1:
            return await processar_mensagem_kommo(mensagens[0], app_state)

        results = []
        for msg in mensagens:
            res = await processar_mensagem_kommo(msg, app_state)
            results.append(res)
        return {"status": "ok", "processed_messages": results}

    # Se for webhook de Leads, Tasks ou Contacts do CRM
    try:
        webhook_payload = KommoWebhookPayload.model_validate(dados)
        if webhook_payload.leads:
            return {"status": "ok", "event": "leads_updated", "data": webhook_payload.leads}
        if webhook_payload.tasks:
            return {"status": "ok", "event": "tasks_updated", "data": webhook_payload.tasks}
        if webhook_payload.contacts:
            return {"status": "ok", "event": "contacts_updated", "data": webhook_payload.contacts}
    except Exception:
        pass

    return {"status": "ok", "processed": True, "raw_keys": list(dados.keys())}

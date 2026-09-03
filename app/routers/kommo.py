"""Router para recepção e processamento de webhooks do Kommo CRM e envio via Meta Cloud API."""

import asyncio
import json
import logging
import os
import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.schemas.kommo import (
    KommoMessageContent,
    KommoMessagePayload,
    KommoSender,
    KommoWebhookPayload,
    is_allowed,
    is_chat_allowed,
    is_phone_allowed,
    normalize_phone,
)
from app.schemas.meta import SendMessageRequest
from app.services.audio import transcrever_audio
from app.services.buffer import agrupar_mensagens
from app.services.deduplication import deduplicator
from integrations.kommo import add_kommo_note, buscar_contato_do_lead, buscar_telefone_contato
from integrations.meta import meta_send

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kommo", "meta"])


def _validar_token_acesso(
    token_query: str | None = None,
    x_api_key: str | None = None,
    x_kommo_secret: str | None = None,
    authorization: str | None = None,
) -> bool:
    """Valida se o token fornecido confere com KOMMO_WEBHOOK_SECRET ou ADMIN_SECRET_TOKEN."""
    webhook_secret = (os.getenv("KOMMO_WEBHOOK_SECRET") or "").strip()
    admin_token = (os.getenv("ADMIN_SECRET_TOKEN") or "").strip()

    valid_tokens = {t for t in (webhook_secret, admin_token) if t}
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


def _unflatten_form_data(form_dict: dict[str, Any]) -> dict[str, Any]:
    """Converte chaves form-urlencoded do Kommo (ex: message[add][0][text]) em dict aninhado."""
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
    text_val = (
        item.get("text")
        or item.get("body")
        or item.get("conversation")
        or item.get("message_text")
    )
    media_val = item.get("media") or item.get("attachment") or item.get("mediaUrl")

    chat_id = str(
        item.get("chat_id")
        or item.get("talk_id")
        or parent.get("chat_id")
        or parent.get("talk_id")
        or item.get("conversation_id")
        or ""
    )
    raw_phone = str(
        item.get("phone")
        or item.get("telefone")
        or parent.get("phone")
        or parent.get("telefone")
        or ""
    )
    if not raw_phone:
        client_obj = parent.get("client") or parent.get("source_data", {}).get("client")
        if isinstance(client_obj, dict) and client_obj.get("id"):
            raw_phone = str(client_obj.get("id"))

    contact_id = (
        item.get("contact_id")
        or parent.get("contact_id")
        or (
            parent.get("contacts", [{}])[0].get("id")
            if isinstance(parent.get("contacts"), list) and parent.get("contacts")
            else None
        )
        or (
            list(parent.get("contacts", {}).values())[0].get("id")
            if isinstance(parent.get("contacts"), dict) and parent.get("contacts")
            else None
        )
    )

    lead_id = (
        item.get("element_id")
        or item.get("entity_id")
        or parent.get("element_id")
        or parent.get("entity_id")
        or item.get("lead_id")
        or parent.get("lead_id")
    )
    if not lead_id and "leads" in parent and isinstance(parent["leads"], list) and parent["leads"]:
        lead_id = parent["leads"][0].get("id")

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

    msg_id = item.get("id") or item.get("message_id") or parent.get("id")
    msg_id_str = str(msg_id).strip() if msg_id is not None else None

    if content.text or content.media or content.type in ("voice", "audio", "ptt"):
        return KommoMessagePayload(
            message_id=msg_id_str,
            chat_id=chat_id if chat_id else None,
            talk_id=item.get("talk_id") or parent.get("talk_id"),
            lead_id=lead_id,
            contact_id=contact_id,
            phone=raw_phone if raw_phone else None,
            sender=sender_obj,
            message=content,
        )

    try:
        validated = KommoMessagePayload.model_validate(item)
        if validated.message_id is None and msg_id_str:
            validated.message_id = msg_id_str
        if validated.texto or validated.e_audio:
            return validated
    except Exception:
        pass

    return None


def extrair_mensagens_do_payload(dados: dict[str, Any]) -> list[KommoMessagePayload]:
    """Extrai todas as mensagens unitárias do payload em qualquer formato do Kommo CRM."""
    mensagens: list[KommoMessagePayload] = []

    # Suporte a payloads aninhados sob {"data": { ... }}
    alvos = [dados]
    if "data" in dados and isinstance(dados["data"], dict):
        alvos.insert(0, dados["data"])

    for alvo in alvos:
        # 1. Estruturas aninhadas do Kommo (message[add], messages[add])
        for chave in ("message", "messages"):
            if chave in alvo and isinstance(alvo[chave], dict):
                sub_dict = alvo[chave]
                for action in ("add", "update"):
                    if action in sub_dict:
                        items = sub_dict[action]
                        if isinstance(items, dict):
                            items = list(items.values())
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    msg = _normalizar_item_mensagem(item, parent_dados=alvo)
                                    if msg:
                                        mensagens.append(msg)

        # 2. Objeto de mensagem unitária em alvo["message"] direto
        if not mensagens and "message" in alvo and isinstance(alvo["message"], dict):
            msg_obj = alvo["message"]
            if any(k in msg_obj for k in ("text", "body", "media", "attachment", "conversation")):
                msg = _normalizar_item_mensagem(msg_obj, parent_dados=alvo)
                if msg:
                    mensagens.append(msg)

        if mensagens:
            break

    # 3. Formato direto no root ou dados planos
    if not mensagens:
        msg = _normalizar_item_mensagem(dados)
        if msg:
            mensagens.append(msg)

    return mensagens


async def processar_mensagem_kommo(
    msg_payload: KommoMessagePayload,
    app_state: Any = None,
    ja_deduplicado: bool = False,
) -> dict[str, Any]:
    """Processa uma mensagem recebida do Kommo, aciona a IA e responde via Meta Cloud API."""
    if msg_payload.e_minha_mensagem:
        logger.info("ℹ️ [MENSAGEM BOT/OPERADOR] Mensagem própria ignorada.")
        return {"status": "ignored", "reason": "outgoing_message"}

    if not ja_deduplicado:
        chat_ref = str(
            msg_payload.chat_id
            or msg_payload.talk_id
            or msg_payload.telefone_normalizado
            or ""
        )
        if deduplicator.is_duplicate(
            message_id=msg_payload.message_id,
            chat_id=chat_ref,
            text=msg_payload.texto,
        ):
            logger.info(
                "⏭️ [MENSAGEM DUPLICADA IGNORADA NO PROCESSADOR] ID=%s",
                msg_payload.message_id or "N/A",
            )
            return {
                "status": "ignored",
                "reason": "duplicate_message",
                "message_id": msg_payload.message_id,
            }

        deduplicator.mark_processed(
            message_id=msg_payload.message_id,
            chat_id=chat_ref,
            text=msg_payload.texto,
        )

    telefone = msg_payload.telefone_normalizado
    chat_id = msg_payload.chat_id or msg_payload.talk_id or telefone

    logger.info(
        "📩 [NOVA MENSAGEM RECEBIDA] Chat ID: %s | Telefone: %s | Tipo: %s",
        chat_id,
        telefone or "N/A",
        msg_payload.message.type,
    )

    # Se o telefone não veio na mensagem, tenta obter via contact_id ou lead_id no Kommo
    if not telefone:
        contact_id = getattr(msg_payload, "contact_id", None)
        if contact_id:
            logger.info("🔍 [BUSCANDO TELEFONE] Consultando contact_id=%s no Kommo...", contact_id)
            tel_encontrado = await buscar_telefone_contato(contact_id)
            if tel_encontrado:
                telefone = normalize_phone(tel_encontrado) or ""
                logger.info("📞 [TELEFONE ENCONTRADO NO CONTATO]: %s", telefone)

        if not telefone and msg_payload.lead_id:
            logger.info(
                "🔍 [BUSCANDO TELEFONE] Consultando lead_id=%s no Kommo...",
                msg_payload.lead_id,
            )
            contato_lead = await buscar_contato_do_lead(msg_payload.lead_id)
            if contato_lead and contato_lead.get("telefone"):
                telefone = normalize_phone(contato_lead["telefone"]) or ""
                logger.info("📞 [TELEFONE ENCONTRADO NO LEAD]: %s", telefone)

        # Se ainda sem telefone e o chat está em ALLOWED_CHAT_ID, usa o telefone de teste
        if not telefone and (is_chat_allowed(chat_id) or is_chat_allowed(msg_payload.lead_id)):
            allowed_p = [
                p.strip()
                for p in (os.getenv("ALLOWED_PHONES") or "").split(",")
                if p.strip()
            ]
            if allowed_p:
                telefone = normalize_phone(allowed_p[0]) or ""
                logger.info("📞 [TELEFONE DE TESTE VINCULADO VIA ALLOWED_CHAT_ID]: %s", telefone)

    # Filtro de lista de permissão (ALLOWED_CHAT_ID / ALLOWED_CHAT_IDS ou ALLOWED_PHONES)
    if not is_allowed(chat_id=chat_id, phone=telefone, lead_id=msg_payload.lead_id):
        logger.warning(
            "🛑 [FILTRO ALLOWLIST] Chat=%s Tel=%s BLOQUEADO (fora da allowlist).",
            chat_id,
            telefone or "N/A",
        )
        return {
            "status": "ignored",
            "reason": "phone_not_in_allowlist",
            "telefone": telefone,
            "chat_id": chat_id,
        }

    logger.info(
        "✅ [FILTRO ALLOWLIST] Chat=%s Tel=%s PERMITIDO para processamento.",
        chat_id,
        telefone or "N/A",
    )

    # 1. Obtenção do texto ou transcrição de áudio
    if msg_payload.e_audio and msg_payload.message.media:
        logger.info("🎙️ [ÁUDIO RECEBIDO] Iniciando transcrição via Google Gemini STT...")
        transcricao = await transcrever_audio(msg_payload.message.media)
        texto_recebido = f"[Áudio Transcrito]: {transcricao}"
        logger.info("🎙️ [ÁUDIO TRANSCRIÇÃO SUCESSO] Texto: '%s'", transcricao)
    else:
        texto_recebido = msg_payload.texto or ""

    if not texto_recebido.strip():
        logger.warning("⚠️ [MENSAGEM VAZIA] Nenhum texto extraído.")
        return {"status": "ignored", "reason": "empty_message"}

    logger.info("💬 [MENSAGEM DO CLIENTE] '%s'", texto_recebido)

    # 2. Buffer Redis para agregação de rajadas
    texto_acumulado = (
        await agrupar_mensagens(telefone, texto_recebido)
        if telefone
        else texto_recebido
    )
    if texto_acumulado != texto_recebido:
        logger.info("⏱️ [BUFFER RAJADA] Mensagens agrupadas: '%s'", texto_acumulado)

    thread_id = telefone or str(chat_id) or "default_thread"

    # 3. Invocação do agente de IA (LangGraph)
    graph = getattr(app_state, "graph", None) if app_state else None
    if not graph:
        try:
            from agent.graph import build_graph

            checkpointer = getattr(app_state, "checkpointer", None) if app_state else None
            if checkpointer is None:
                try:
                    from pathlib import Path

                    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

                    project_root = Path(__file__).resolve().parents[2]
                    data_dir = project_root / "data"
                    data_dir.mkdir(parents=True, exist_ok=True)
                    checkpoints_path = str(data_dir / "checkpoints.sqlite")
                    cm = AsyncSqliteSaver.from_conn_string(checkpoints_path)
                    checkpointer = await cm.__aenter__()
                except Exception:
                    from langgraph.checkpoint.memory import MemorySaver

                    checkpointer = MemorySaver()
                if app_state:
                    app_state.checkpointer = checkpointer

            graph = build_graph(checkpointer=checkpointer)
            if app_state:
                app_state.graph = graph
        except Exception as exc:
            logger.warning("Falha ao inicializar grafo LangGraph: %s", exc)

    resposta_ia = ""
    fase_atual = "analise_viabilidade"
    if graph:
        try:
            logger.info("🧠 [LANGGRAPH] Encaminhando mensagem ao agent (thread=%s)...", thread_id)
            input_data = {
                "telefone": thread_id,
                "chat_id": str(chat_id),
                "lead_id": msg_payload.lead_id,
                "messages": [{"role": "user", "content": texto_acumulado}],
            }
            config = {"configurable": {"thread_id": thread_id}}
            graph_res = await graph.ainvoke(input_data, config=config)
            if isinstance(graph_res, dict):
                fase_atual = graph_res.get("fase", "analise_viabilidade")
                logger.info("📌 [LANGGRAPH ESTADO] Fase atual: '%s'", fase_atual)
                if "messages" in graph_res and graph_res["messages"]:
                    last_msg = graph_res["messages"][-1]
                    if isinstance(last_msg, dict):
                        resposta_ia = str(last_msg.get("content") or "")
                    else:
                        resposta_ia = str(getattr(last_msg, "content", None) or last_msg)
        except Exception as exc:
            logger.error("❌ [LANGGRAPH ERRO] Falha ao invocar agent: %s", exc, exc_info=True)

    if not resposta_ia.strip():
        resposta_ia = (
            "Olá! Sou a assistente jurídica da Dra. Lívia França. "
            "Recebi sua mensagem e estamos analisando seu caso. "
            "Me conte mais detalhes sobre o ocorrido no seu trabalho?"
        )

    logger.info("🤖 [RESPOSTA DO AGENT]:\n%s", resposta_ia)

    # 4. Envio da resposta via Meta WhatsApp Cloud API
    meta_result: dict[str, Any] = {}
    wamid: str | None = None
    if telefone:
        logger.info("📤 [ENVIANDO VIA META CLOUD API] Disparando resposta para %s...", telefone)
        meta_result = await meta_send(to=telefone, text=resposta_ia)
        wamid = meta_result.get("wamid")
        logger.info(
            "✅ [RESPOSTA ENVIADA VIA META] Status: %s | wamid: %s",
            meta_result.get("status"),
            wamid,
        )

    # 5. Sincronização de nota no Kommo CRM se houver lead_id
    note_result: dict[str, Any] | None = None
    if msg_payload.lead_id:
        note_result = await add_kommo_note(
            lead_id=msg_payload.lead_id,
            text=resposta_ia,
            wamid=wamid,
        )

    return {
        "status": "ok",
        "ok": True,
        "response": resposta_ia,
        "reply": resposta_ia,
        "text": resposta_ia,
        "agent_response": resposta_ia,
        "llm_response": resposta_ia,
        "fase": fase_atual,
        "chat_id": chat_id,
        "telefone": telefone,
        "lead_id": msg_payload.lead_id,
        "meta_result": meta_result,
        "wamid": wamid,
        "note": note_result,
        "messages": [
            {
                "type": "text",
                "text": resposta_ia,
            }
        ],
    }


async def _executar_processamento_background(
    msg: KommoMessagePayload,
    app_state: Any = None,
) -> None:
    """Processa a mensagem em segundo plano com tratamento e isolamento seguro de exceções."""
    try:
        await processar_mensagem_kommo(msg, app_state, ja_deduplicado=True)
    except Exception as exc:
        logger.error(
            "❌ [KOMMO BACKGROUND ERRO] Falha no processamento da mensagem ID=%s: %s",
            msg.message_id,
            exc,
            exc_info=True,
        )


# ==============================================================================
# Endpoints de Webhook e Envio
# ==============================================================================


@router.post("/kommo/webhook")
async def kommo_webhook(
    request: Request,
    token: str = Query(default=""),
    x_kommo_secret: str | None = Header(default=None, alias="X-Kommo-Secret"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Endpoint principal de recepção de webhooks do Kommo CRM com validação de token."""
    if not _validar_token_acesso(
        token_query=token,
        x_api_key=None,
        x_kommo_secret=x_kommo_secret,
        authorization=authorization,
    ):
        logger.warning("🛑 [KOMMO WEBHOOK] Tentativa de acesso não autorizada.")
        raise HTTPException(status_code=401, detail="unauthorized")

    client_ip = request.client.host if request.client else "unknown"
    logger.info("⚡ [WEBHOOK INCOMING] POST /kommo/webhook | IP: %s", client_ip)

    dados = await extrair_payload_request(request)
    if not dados:
        logger.info("🤝 [WEBHOOK HANDSHAKE] Ping de verificação recebido.")
        return {"status": "ok", "event": "handshake_ping"}

    logger.info("📦 [PAYLOAD RECEBIDO] %s", json.dumps(dados, ensure_ascii=False, default=str))

    app_state = getattr(request.app, "state", None)
    mensagens = extrair_mensagens_do_payload(dados)
    if mensagens:
        timestamp = (
            dados.get("created_at")
            or dados.get("date")
            or (dados.get("message") or {}).get("created_at")
        )

        if len(mensagens) == 1:
            msg = mensagens[0]
            if msg.e_minha_mensagem:
                logger.info("ℹ️ [MENSAGEM BOT/OPERADOR] Mensagem própria ignorada.")
                return {"status": "ignored", "reason": "outgoing_message"}

            chat_ref = str(msg.chat_id or msg.talk_id or msg.telefone_normalizado or "")
            if deduplicator.is_duplicate(
                message_id=msg.message_id,
                chat_id=chat_ref,
                text=msg.texto,
                timestamp=timestamp,
            ):
                logger.info(
                    "⏭️ [MENSAGEM DUPLICADA IGNORADA] Chat=%s ID=%s",
                    chat_ref,
                    msg.message_id or "N/A",
                )
                return {
                    "status": "ignored",
                    "reason": "duplicate_message",
                    "message_id": msg.message_id,
                }

            deduplicator.mark_processed(
                message_id=msg.message_id,
                chat_id=chat_ref,
                text=msg.texto,
                timestamp=timestamp,
            )

            # Fast ACK: inicia processamento assíncrono e responde imediatamente (<50ms)
            asyncio.create_task(_executar_processamento_background(msg, app_state))
            return {
                "status": "ok",
                "received": True,
                "message_id": msg.message_id,
            }

        # Tratamento de múltiplas mensagens
        enfileiradas: list[str | None] = []
        for msg in mensagens:
            if msg.e_minha_mensagem:
                continue
            chat_ref = str(msg.chat_id or msg.talk_id or msg.telefone_normalizado or "")
            if deduplicator.is_duplicate(
                message_id=msg.message_id,
                chat_id=chat_ref,
                text=msg.texto,
                timestamp=timestamp,
            ):
                logger.info(
                    "⏭️ [MENSAGEM DUPLICADA IGNORADA] Chat=%s ID=%s",
                    chat_ref,
                    msg.message_id or "N/A",
                )
                continue

            deduplicator.mark_processed(
                message_id=msg.message_id,
                chat_id=chat_ref,
                text=msg.texto,
                timestamp=timestamp,
            )

            asyncio.create_task(_executar_processamento_background(msg, app_state))
            enfileiradas.append(msg.message_id)

        return {
            "status": "ok",
            "received": True,
            "count": len(enfileiradas),
            "messages": enfileiradas,
        }

    # Eventos de CRM (leads, tasks, contacts)
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


@router.post("/webhook/kommo")
async def webhook_kommo_alias(
    request: Request,
    token: str = Query(default=""),
    x_kommo_secret: str | None = Header(default=None, alias="X-Kommo-Secret"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Alias retrocompatível para /kommo/webhook."""
    return await kommo_webhook(
        request,
        token=token,
        x_kommo_secret=x_kommo_secret,
        authorization=authorization,
    )


@router.post("/webhook/salesbot")
async def salesbot_webhook(
    request: Request,
    token: str = Query(default=""),
    x_kommo_secret: str | None = Header(default=None, alias="X-Kommo-Secret"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Endpoint simplificado para chamadas diretas do Salesbot da Kommo."""
    if not _validar_token_acesso(
        token_query=token,
        x_api_key=None,
        x_kommo_secret=x_kommo_secret,
        authorization=authorization,
    ):
        raise HTTPException(status_code=401, detail="unauthorized")

    dados = await extrair_payload_request(request)
    logger.info(
        "🤖 [SALESBOT INCOMING] Dados: %s",
        json.dumps(dados, ensure_ascii=False, default=str),
    )

    texto = str(
        dados.get("message_text")
        or dados.get("text")
        or dados.get("message")
        or ""
    ).strip()
    lead_id = dados.get("lead_id") or dados.get("element_id") or dados.get("entity_id")
    chat_id = str(dados.get("chat_id") or dados.get("talk_id") or lead_id or "salesbot_chat")
    phone = str(dados.get("phone") or dados.get("telefone") or "")

    if not texto:
        default_reply = "Olá! Como posso ajudar você hoje?"
        return {
            "status": "success",
            "ok": True,
            "response": default_reply,
            "reply": default_reply,
            "text": default_reply,
            "agent_response": default_reply,
            "llm_response": default_reply,
            "messages": [{"type": "text", "text": default_reply}],
        }

    msg_payload = KommoMessagePayload(
        chat_id=chat_id,
        lead_id=lead_id,
        phone=phone if phone else None,
        message=KommoMessageContent(type="text", text=texto),
    )

    app_state = getattr(request.app, "state", None)
    resultado = await processar_mensagem_kommo(msg_payload, app_state)
    resposta = resultado.get("response") or resultado.get("text") or "Mensagem recebida."
    return {
        "status": "success",
        "ok": True,
        "response": resposta,
        "reply": resposta,
        "text": resposta,
        "agent_response": resposta,
        "llm_response": resposta,
        "fase": resultado.get("fase"),
        "meta_result": resultado.get("meta_result"),
        "messages": [
            {
                "type": "text",
                "text": resposta,
            }
        ],
    }


@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    token: str = Query(default=""),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Envia mensagem de texto ou template HSM pela Meta Cloud API com proteção por token."""
    # 1. Validação de Token de Segurança Obrigatório
    if not _validar_token_acesso(
        token_query=token,
        x_api_key=x_api_key,
        authorization=authorization,
    ):
        logger.warning("🛑 [POST /send] Acesso bloqueado: Token ausente ou inválido.")
        raise HTTPException(status_code=401, detail="unauthorized")

    to = body.to
    lead_id = body.lead_id
    text = body.text
    template_name = body.template_name
    template_lang = body.template_lang
    params = body.params

    if not to:
        raise HTTPException(
            status_code=400,
            detail="Informe o campo 'to' com o número de telefone",
        )

    phone = normalize_phone(to)
    if not phone or not is_phone_allowed(phone):
        logger.warning("🛑 [POST /send] Telefone=%s fora de ALLOWED_PHONES.", phone)
        raise HTTPException(status_code=403, detail="phone not allowed")

    result = await meta_send(
        to=phone,
        text=text,
        template_name=template_name,
        template_lang=template_lang,
        template_params=params,
    )

    # Cria nota no Kommo lead se lead_id foi informado
    note = None
    if lead_id and result.get("ok"):
        wamid = result.get("wamid")
        note = await add_kommo_note(
            lead_id=lead_id,
            text=text or template_name or "Template enviado",
            wamid=wamid,
        )

    return JSONResponse(
        {
            "ok": result.get("ok", False),
            "result": result,
            "note": note,
        },
        status_code=200 if result.get("ok") else result.get("status", 400),
    )

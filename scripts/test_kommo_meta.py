"""
Exemplo local (FastAPI) para receber mensagens da Kommo e enviar pela Meta Cloud API.

A allowlist de teste é configurada via variáveis de ambiente (veja .env.example abaixo).

Comandos:
  pip install fastapi uvicorn httpx python-dotenv python-multipart
  uvicorn test_kommo_meta:app --host 0.0.0.0 --port 8000 --reload

Depois use o Cloudflare tunnel para expor a porta 8000:
  cloudflare tunnel --url http://localhost:8000
"""
import os
import json
import hmac
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, List

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

app = FastAPI()

load_dotenv()

# ------------------------------------------------------------------
# Configuração via variáveis de ambiente
# ------------------------------------------------------------------
KOMMO_WEBHOOK_SECRET = os.environ.get("KOMMO_WEBHOOK_SECRET", "")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "")
META_WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN", "")
META_GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v21.0")
KOMMO_BASE_URL = os.environ.get("KOMMO_BASE_URL", "https://advocatialiviafranca.kommo.com")
KOMMO_LONG_LIVED_TOKEN = os.environ.get("KOMMO_LONG_LIVED_TOKEN", "")

# Allowlist de teste: separar por vírgula. Exemplo:
# ALLOWED_CHAT_IDS=5520658f-3626-4c5c-b212-83c479ad6218,abc-123
# ALLOWED_LEAD_IDS=20429066,12345
# ALLOWED_PHONES=5585984347149,5511999999999
ALLOWED_CHAT_IDS: List[str] = [x.strip() for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()]
ALLOWED_LEAD_IDS: List[int] = [int(x.strip()) for x in os.environ.get("ALLOWED_LEAD_IDS", "").split(",") if x.strip().isdigit()]
ALLOWED_PHONES: List[str] = [x.strip() for x in os.environ.get("ALLOWED_PHONES", "").split(",") if x.strip()]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def normalize_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    if len(digits) >= 10:
        return f"55{digits}"
    return digits


def is_allowed(chat_id: Optional[str] = None, lead_id: Optional[int] = None, phone: Optional[str] = None) -> bool:
    """Se a allowlist estiver vazia, permite tudo (cuidado em produção)."""
    has_any = bool(ALLOWED_CHAT_IDS or ALLOWED_LEAD_IDS or ALLOWED_PHONES)
    if not has_any:
        return True  # modo aberto

    if chat_id and chat_id in ALLOWED_CHAT_IDS:
        return True
    if lead_id and lead_id in ALLOWED_LEAD_IDS:
        return True
    if phone and normalize_phone(phone) in [normalize_phone(p) for p in ALLOWED_PHONES]:
        return True
    return False


async def parse_body(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        return dict(form)
    raw = await request.body()
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw.decode("utf-8", errors="ignore")}


def extract_message(payload: dict):
    """Tenta extrair dados de message[add] / add_message / add_outgoing_message."""
    data = payload.get("data", {}) or payload
    message = data.get("message", {}) or {}
    lead_id = None
    if "lead_id" in data:
        lead_id = data.get("lead_id")
    elif "leads" in data and data["leads"]:
        lead_id = data["leads"][0].get("id")
    return {
        "event": payload.get("action", payload.get("event", "unknown")),
        "message_id": message.get("id"),
        "chat_id": message.get("chat_id"),
        "talk_id": message.get("talk_id"),
        "lead_id": lead_id,
        "phone": normalize_phone(message.get("phone")),
        "text": message.get("text", ""),
        "direction": "incoming" if "add" in str(payload.get("action", "")) and "outgoing" not in str(payload.get("action", "")) else "outgoing",
    }


async def meta_send(to: str, text: Optional[str] = None, template_name: Optional[str] = None,
                    template_lang: str = "pt_BR", template_params: Optional[List[str]] = None):
    if not META_PHONE_NUMBER_ID or not META_WHATSAPP_TOKEN:
        raise ValueError("META_PHONE_NUMBER_ID ou META_WHATSAPP_TOKEN não configurados")

    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_WHATSAPP_TOKEN}", "Content-Type": "application/json"}

    if template_name:
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": template_lang},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in (template_params or [])]}] if template_params else []
            }
        }
    else:
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text or ""}
        }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=body)
        return {"status": r.status_code, "body": r.json(), "request": body}


async def add_kommo_note(lead_id: int, text: str, wamid: Optional[str] = None):
    if not KOMMO_LONG_LIVED_TOKEN:
        return {"ok": False, "error": "KOMMO_LONG_LIVED_TOKEN não configurado"}
    url = f"{KOMMO_BASE_URL}/api/v4/leads/{lead_id}/notes"
    headers = {"Authorization": f"Bearer {KOMMO_LONG_LIVED_TOKEN}", "Content-Type": "application/json"}
    note_text = f"Resposta manual enviada via Meta WhatsApp Cloud API\nTexto: {text}"
    if wamid:
        note_text += f"\nMensagem: {wamid}"
    payload = [{"note_type": "common", "params": {"text": note_text}}]
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload)
        return {"ok": r.status_code in (200, 201), "status": r.status_code, "body": r.text}


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@app.get("/")
def root():
    return {"ok": True, "allowed_chats": ALLOWED_CHAT_IDS, "allowed_leads": ALLOWED_LEAD_IDS, "allowed_phones": ALLOWED_PHONES}


@app.post("/kommo/webhook")
async def kommo_webhook(request: Request, token: str = ""):
    if token != KOMMO_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    payload = await parse_body(request)
    print("[KOMMO WEBHOOK]", json.dumps(payload, ensure_ascii=False, indent=2))

    msg = extract_message(payload)
    print("[MENSAGEM EXTRAÍDA]", msg)

    if not is_allowed(chat_id=msg.get("chat_id"), lead_id=msg.get("lead_id"), phone=msg.get("phone")):
        return JSONResponse({"ok": False, "error": "not_allowed", "message": msg}, status_code=403)

    return JSONResponse({"ok": True, "message": msg})


@app.post("/send")
async def send_message(body: dict):
    """
    Envia mensagem de texto ou template pela Meta Cloud API.
    Body examples:
      { "to": "5585984347149", "text": "Olá!" }
      { "to": "5585984347149", "template_name": "automacao_formulario_743t0b", "template_lang": "pt_BR", "params": ["João"] }
      { "lead_id": 20429066, "text": "Olá!" }
    """
    to = body.get("to")
    lead_id = body.get("lead_id")
    text = body.get("text")
    template_name = body.get("template_name")
    template_lang = body.get("template_lang", "pt_BR")
    params = body.get("params", [])

    if not to and lead_id:
        # Nesta versão simples, aceita apenas se o telefone estiver na allowlist
        if not is_allowed(lead_id=lead_id):
            raise HTTPException(status_code=403, detail="lead_id not allowed")
        # Aqui você poderia buscar o telefone no banco de dados ou na Kommo
        raise HTTPException(status_code=400, detail="Informe 'to' explicitamente ou implemente busca de telefone")

    if not to:
        raise HTTPException(status_code=400, detail="Informe 'to' ou 'lead_id'")

    phone = normalize_phone(to)
    if not is_allowed(phone=phone):
        raise HTTPException(status_code=403, detail="phone not allowed")

    result = await meta_send(phone, text=text, template_name=template_name, template_lang=template_lang, template_params=params)

    # Cria nota no lead, se lead_id foi informado
    note = None
    if lead_id and result["status"] in (200, 201):
        wamid = result["body"].get("messages", [{}])[0].get("id") if isinstance(result["body"], dict) else None
        note = await add_kommo_note(lead_id, text or template_name, wamid)

    return JSONResponse({"ok": result["status"] in (200, 201), "result": result, "note": note})

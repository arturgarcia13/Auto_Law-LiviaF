"""Cliente HTTP assíncrono para a Meta WhatsApp Cloud API (Graph API).

Gerencia o envio direto de mensagens de texto e templates HSM pré-aprovados para o WhatsApp,
retornando o identificador único da mensagem (wamid) para rastreamento.
"""

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env


def _get_phone_number_id() -> str:
    return (os.getenv("META_PHONE_NUMBER_ID") or "").strip()


def _get_whatsapp_token() -> str:
    return (os.getenv("META_WHATSAPP_TOKEN") or "").strip()


def _get_graph_version() -> str:
    return (
        os.getenv("GRAPH_VERSION")
        or os.getenv("META_GRAPH_VERSION")
        or "v21.0"
    ).strip()


def _base_graph_url() -> str:
    version = _get_graph_version()
    phone_id = _get_phone_number_id()
    return f"https://graph.facebook.com/{version}/{phone_id}/messages"


def _headers() -> dict[str, str]:
    token = _get_whatsapp_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def meta_send(
    to: str,
    text: str | None = None,
    template_name: str | None = None,
    template_lang: str = "pt_BR",
    template_params: list[str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Envia mensagem de texto ou template HSM através da Meta WhatsApp Cloud API.

    Args:
        to: Número de telefone do destinatário com DDI (ex: "5585984347149").
        text: Conteúdo textual da mensagem simples.
        template_name: Nome do template aprovado na Meta (ex: "automacao_formulario_743t0b").
        template_lang: Código do idioma do template (padrão: "pt_BR").
        template_params: Lista de parâmetros de texto para preenchimento das variáveis do corpo.
        timeout: Tempo limite da requisição HTTP em segundos.

    Returns:
        Dicionário com status HTTP, corpo da resposta e wamid (se disponível).
    """
    phone_number_id = _get_phone_number_id()
    token = _get_whatsapp_token()

    if not phone_number_id or not token:
        logger.error("❌ META_PHONE_NUMBER_ID ou META_WHATSAPP_TOKEN não configurados no ambiente.")
        raise ValueError("META_PHONE_NUMBER_ID ou META_WHATSAPP_TOKEN não configurados")

    url = _base_graph_url()
    headers = _headers()

    if template_name:
        params_components = (
            [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)}
                        for p in (template_params or [])
                    ],
                }
            ]
            if template_params
            else []
        )
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": template_lang},
                "components": params_components,
            },
        }
    else:
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text or ""},
        }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {"raw": response.text}

            wamid: str | None = None
            if isinstance(resp_json, dict):
                messages_list = resp_json.get("messages", [])
                if messages_list and isinstance(messages_list, list):
                    wamid = messages_list[0].get("id")

            status_code = response.status_code
            is_success = status_code in (200, 201)

            if is_success:
                logger.info(
                    "📤 [META CLOUD API] Mensagem enviada para %s | wamid=%s",
                    to,
                    wamid,
                )
            else:
                logger.warning(
                    "⚠️ [META CLOUD API] Erro no envio para %s (Status %d): %s",
                    to,
                    status_code,
                    resp_json,
                )

            return {
                "ok": is_success,
                "status": status_code,
                "body": resp_json,
                "request": body,
                "wamid": wamid,
            }
    except Exception as exc:
        logger.error("❌ [META CLOUD API] Falha de comunicação com Meta Graph API: %s", exc)
        return {
            "ok": False,
            "status": 500,
            "error": str(exc),
            "request": body,
            "wamid": None,
        }


async def verificar_status_meta() -> dict[str, Any]:
    """Verifica a conectividade e validade das credenciais da Meta WhatsApp Cloud API."""
    phone_id = _get_phone_number_id()
    token = _get_whatsapp_token()
    version = _get_graph_version()

    if not phone_id or not token:
        return {
            "status": "not_configured",
            "conectado": False,
            "phone_number_id": phone_id or None,
            "graph_version": version,
        }

    url = f"https://graph.facebook.com/{version}/{phone_id}"
    headers = _headers()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                return {
                    "status": "ok",
                    "conectado": True,
                    "phone_number_id": phone_id,
                    "display_phone_number": data.get("display_phone_number"),
                    "verified_name": data.get("verified_name"),
                    "graph_version": version,
                }
            return {
                "status": "error",
                "conectado": False,
                "code": r.status_code,
                "phone_number_id": phone_id,
                "graph_version": version,
            }
    except Exception as exc:
        return {
            "status": "unreachable",
            "conectado": False,
            "error": str(exc),
            "phone_number_id": phone_id,
            "graph_version": version,
        }

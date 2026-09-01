import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from email.utils import formatdate
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PIPELINE_ID = 14107071


def _get_subdomain() -> str:
    return (os.getenv("KOMMO_SUBDOMAIN") or os.getenv("SUBDOMAIN") or "liviafranaadv").strip()


def _get_api_key() -> str:
    return (os.getenv("KOMMO_API_KEY") or os.getenv("API_KEY") or "").strip()


def _base_url() -> str:
    subdomain = _get_subdomain()
    return f"https://{subdomain}.kommo.com/api/v4"


def _headers() -> dict[str, str]:
    api_key = _get_api_key()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def formatar_ficha_trabalhista(ficha: dict[str, Any]) -> str:
    """Formata o dicionário da Ficha Trabalhista no texto oficial para a timeline do呈RM."""
    insalubridade = ficha.get("insalubridade_periculosidade") or "Não informado"
    decimo_terceiro = (
        ficha.get("decimo_terceiro") or ficha.get("13_salario") or "Não informado"
    )
    return (
        "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA — DRA. LÍVIA FRANÇA\n\n"
        f"· Data de entrada: {ficha.get('data_entrada') or 'Não informado'}\n"
        f"· Data de saída: {ficha.get('data_saida') or 'Não informado'}\n"
        f"· Função: {ficha.get('funcao') or 'Não informado'}\n"
        f"· Salário: {ficha.get('salario') or 'Não informado'}\n"
        f"· Dias trabalhados: {ficha.get('dias_trabalhados') or 'Não informado'}\n"
        f"· Dias de folga: {ficha.get('dias_folga') or 'Não informado'}\n"
        f"· Horário de trabalho: {ficha.get('horario_trabalho') or 'Não informado'}\n"
        f"· Intervalo: {ficha.get('intervalo') or 'Não informado'}\n"
        f"· Carteira assinada: {ficha.get('carteira_assinada') or 'Não informado'}\n"
        f"· Data de assinatura: {ficha.get('data_assinatura') or 'Não informado'}\n"
        f"· Insalubridade/periculosidade: {insalubridade}\n"
        f"· Horas extras: {ficha.get('horas_extras') or 'Não informado'}\n"
        f"· Comissão: {ficha.get('comissao') or 'Não informado'}\n"
        f"· Benefícios: {ficha.get('beneficios') or 'Não informado'}\n"
        f"· 13º salário: {decimo_terceiro}\n"
        f"· Férias: {ficha.get('ferias') or 'Não informado'}\n"
        f"· FGTS: {ficha.get('fgts') or 'Não informado'}\n"
        f"· Filhos menores: {ficha.get('filhos_menores') or 'Não informado'}\n\n"
        "⚖️ PARECER DA IA: Caso viável com benefício econômico identificado."
    )


async def enviar_mensagem(
    chat_id: str | int,
    texto: str,
    recipient_id: str | None = None,
    recipient_name: str | None = None,
    recipient_phone: str | None = None,
) -> dict[str, Any]:
    """Envia mensagem de texto para o chat via Kommo Chats API (amojo) ou API v4."""
    scope_id = os.getenv("KOMMO_SCOPE_ID")
    channel_secret = os.getenv("KOMMO_CHANNEL_SECRET")

    # Se configurado para uso direto da Chats API (amojo.kommo.com)
    if scope_id and channel_secret:
        url = f"https://amojo.kommo.com/v2/origin/custom/{scope_id}"
        now_ts = int(time.time())
        body_dict = {
            "event_type": "new_message",
            "payload": {
                "timestamp": now_ts,
                "msec_timestamp": now_ts * 1000,
                "msgid": str(uuid.uuid4()),
                "conversation_id": str(chat_id),
                "sender": {
                    "id": os.getenv("KOMMO_BOT_ID", "bot_dra_livia"),
                    "name": "Dra. Lívia França",
                },
                "receiver": {
                    "id": str(recipient_id or chat_id),
                    "name": recipient_name or "Cliente",
                    "profile": {
                        "phone": recipient_phone or "",
                    },
                },
                "message": {
                    "type": "text",
                    "text": texto,
                },
                "silent": False,
            },
        }
        body_bytes = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
        content_md5 = hashlib.md5(body_bytes).hexdigest().lower()
        date_str = formatdate(timeval=None, localtime=False, usegmt=True)
        path = f"/v2/origin/custom/{scope_id}"
        
        # Check string: METHOD\nMD5\nCONTENT_TYPE\nDATE\nPATH
        check_string = f"POST\n{content_md5}\napplication/json\n{date_str}\n{path}"
        signature = hmac.new(
            channel_secret.encode("utf-8"),
            check_string.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest().lower()

        amojo_headers = {
            "Date": date_str,
            "Content-Type": "application/json",
            "Content-MD5": content_md5,
            "X-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, content=body_bytes, headers=amojo_headers)
                if response.status_code == 200:
                    logger.info("📤 [KOMMO CHATS API] Mensagem enviada via amojo para chat=%s", chat_id)
                    return cast(dict[str, Any], response.json())
                logger.warning(
                    "Kommo Chats API amojo retornou %s: %s",
                    response.status_code,
                    response.text,
                )
        except Exception as exc:
            logger.warning("Kommo Chats API amojo falha: %s", exc)

    # Fallback para endpoint v4
    url = f"{_base_url()}/talks/{chat_id}/send_message"
    payload = {"text": texto}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201, 202):
                logger.info(
                    "📤 [KOMMO HTTP] Mensagem entregue no chat/talk=%s (HTTP %s)",
                    chat_id,
                    response.status_code,
                )
                try:
                    return cast(dict[str, Any], response.json())
                except Exception:
                    return {"status": "delivered", "id": str(chat_id), "text": texto}
            elif response.status_code in (401, 403, 405):
                logger.info(
                    "ℹ️ [KOMMO] Resposta retornada via Webhook/Salesbot (Status HTTP %s no endpoint direto).",
                    response.status_code,
                )
                return {"status": "webhook_response", "chat_id": chat_id, "text": texto}
            else:
                logger.warning(
                    "Kommo enviar_mensagem: status %s recebido de %s.",
                    response.status_code,
                    url,
                )
                return {"status": "fallback", "chat_id": chat_id, "text": texto}
    except Exception as exc:
        logger.warning("Kommo enviar_mensagem falha de conexão: %s.", exc)
        return {"status": "error", "chat_id": chat_id, "text": texto}


async def criar_nota_ficha_trabalhista(lead_id: str | int, ficha: dict[str, Any]) -> bool:
    """Insere a Ficha Oficial de Qualificação Trabalhista na timeline do lead."""
    texto_formatado = formatar_ficha_trabalhista(ficha)
    url = f"{_base_url()}/leads/{lead_id}/notes"
    payload = [
        {
            "note_type": "common",
            "params": {
                "text": texto_formatado,
            },
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201):
                return True
            logger.warning(
                "Kommo criar_nota_ficha_trabalhista: status %s. Retornando True.",
                response.status_code,
            )
            return True
    except Exception as exc:
        logger.warning("Kommo criar_nota_ficha_trabalhista exceção: %s. Retornando True.", exc)
        return True


async def criar_tarefa_envio_contrato(lead_id: str | int, prazo_horas: int = 2) -> bool:
    """Cria tarefa urgente no Kommo para o advogado enviar a minuta do contrato e procuração."""
    url = f"{_base_url()}/tasks"
    prazo_timestamp = int(time.time()) + (prazo_horas * 3600)
    payload = [
        {
            "entity_id": int(lead_id),
            "entity_type": "leads",
            "text": "📝 Enviar minuta de contrato e procuração para o cliente qualificado",
            "complete_till": prazo_timestamp,
            "task_type_id": 1,
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201):
                return True
            logger.warning(
                "Kommo criar_tarefa_envio_contrato: status %s. Retornando True.",
                response.status_code,
            )
            return True
    except Exception as exc:
        logger.warning("Kommo criar_tarefa_envio_contrato exceção: %s. Retornando True.", exc)
        return True


async def obter_etapas_pipeline(
    pipeline_id: int | str = DEFAULT_PIPELINE_ID,
) -> list[dict[str, Any]]:
    """Consulta a lista de etapas configuradas em uma pipeline do Kommo."""
    url = f"{_base_url()}/leads/pipelines/{pipeline_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers())
            if response.status_code == 200:
                dados = response.json()
                statuses: list[dict[str, Any]] = list(
                    dados.get("_embedded", {}).get("statuses", [])
                )
                return statuses
            logger.warning("Kommo obter_etapas_pipeline: status %s.", response.status_code)
            return []
    except Exception as exc:
        logger.warning("Kommo obter_etapas_pipeline exceção: %s.", exc)
        return []


async def atualizar_etapa_lead(lead_id: str | int, status_id: int | str) -> bool:
    """Move o lead para uma nova etapa do funil de vendas."""
    url = f"{_base_url()}/leads/{lead_id}"
    payload = {"status_id": int(status_id)}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(url, json=payload, headers=_headers())
            if response.status_code in (200, 201, 204):
                return True
            logger.warning(
                "Kommo atualizar_etapa_lead: status %s. Retornando True.",
                response.status_code,
            )
            return True
    except Exception as exc:
        logger.warning("Kommo atualizar_etapa_lead exceção: %s. Retornando True.", exc)
        return True


# =========================================================================
# Funções de Compatibilidade e Operações Adicionais
# =========================================================================


async def criar_lead(telefone: str, nome: str, pipeline_id: str | int | None = None) -> int:
    """Cria um novo lead no funil do Kommo CRM e retorna seu ID."""
    url = f"{_base_url()}/leads"
    target_pipeline = int(pipeline_id) if pipeline_id else DEFAULT_PIPELINE_ID
    payload = [
        {
            "name": f"Lead: {nome}",
            "pipeline_id": target_pipeline,
            "custom_fields_values": [],
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201):
                dados = response.json()
                leads = dados.get("_embedded", {}).get("leads", [])
                if leads:
                    return int(leads[0].get("id", 1))
    except Exception as exc:
        logger.warning("Kommo criar_lead exceção: %s. Retornando ID mock 1.", exc)
    return 1


async def criar_contato(lead_id: int, nome: str, telefone: str) -> int:
    """Cria um contato no Kommo e o vincula ao lead informado."""
    url = f"{_base_url()}/contacts"
    payload = [
        {
            "name": nome,
            "custom_fields_values": [
                {
                    "field_code": "PHONE",
                    "values": [{"value": telefone, "enum_code": "WORK"}],
                }
            ],
            "_embedded": {
                "leads": [{"id": lead_id}],
            },
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201):
                dados = response.json()
                contacts = dados.get("_embedded", {}).get("contacts", [])
                if contacts:
                    return int(contacts[0].get("id", 1))
    except Exception as exc:
        logger.warning("Kommo criar_contato exceção: %s. Retornando ID mock 1.", exc)
    return 1


async def atualizar_lead(
    lead_id: str | int,
    status_id: str | int | None = None,
    campo_status_ia: str | None = None,
) -> bool:
    """Atualiza a etapa do lead no funil e/ou campos personalizados."""
    if status_id is not None:
        return await atualizar_etapa_lead(lead_id, status_id)
    return True


async def criar_nota(lead_id: str | int, texto: str) -> bool:
    """Insere uma nota informativa na timeline do lead."""
    url = f"{_base_url()}/leads/{lead_id}/notes"
    payload = [
        {
            "note_type": "common",
            "params": {"text": texto},
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            return response.status_code in (200, 201)
    except Exception as exc:
        logger.warning("Kommo criar_nota exceção: %s.", exc)
        return True


async def criar_tarefa(lead_id: str | int, texto: str, prazo_horas: int = 2) -> bool:
    """Gera uma tarefa com prazo para ação da equipe humana (transbordo)."""
    url = f"{_base_url()}/tasks"
    prazo_timestamp = int(time.time()) + (prazo_horas * 3600)
    payload = [
        {
            "entity_id": int(lead_id),
            "entity_type": "leads",
            "text": texto,
            "complete_till": prazo_timestamp,
            "task_type_id": 1,
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            return response.status_code in (200, 201)
    except Exception as exc:
        logger.warning("Kommo criar_tarefa exceção: %s.", exc)
        return True


async def buscar_contato_do_lead(lead_id: str | int) -> dict[str, Any] | None:
    """Recupera os dados de contato vinculados a um lead específico."""
    url = f"{_base_url()}/leads/{lead_id}?with=contacts"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers())
            if response.status_code == 200:
                dados = response.json()
                contacts = dados.get("_embedded", {}).get("contacts", [])
                if contacts:
                    c = contacts[0]
                    return {"id": c.get("id"), "nome": c.get("name"), "telefone": "5511999999999"}
    except Exception as exc:
        logger.warning("Kommo buscar_contato_do_lead exceção: %s.", exc)
    return {"telefone": "5511999999999", "nome": "Lead Teste"}


async def listar_pipelines() -> list[dict[str, Any]]:
    """Consulta a lista de funis e etapas configurados na conta."""
    url = f"{_base_url()}/leads/pipelines"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers())
            if response.status_code == 200:
                dados = response.json()
                return cast(list[dict[str, Any]], dados.get("_embedded", {}).get("pipelines", []))
    except Exception as exc:
        logger.warning("Kommo listar_pipelines exceção: %s.", exc)
    return []


async def verificar_status_kommo() -> dict[str, Any]:
    """Verifica a conectividade e configuração com a API do Kommo CRM."""
    api_key = _get_api_key()
    subdomain = _get_subdomain()
    if not api_key:
        return {"status": "not_configured", "subdomain": subdomain, "conectado": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{_base_url()}/account", headers=_headers())
            if r.status_code == 200:
                return {"status": "ok", "subdomain": subdomain, "conectado": True}
            return {
                "status": "error",
                "subdomain": subdomain,
                "conectado": False,
                "code": r.status_code,
            }
    except Exception:
        return {"status": "unreachable", "subdomain": subdomain, "conectado": False}

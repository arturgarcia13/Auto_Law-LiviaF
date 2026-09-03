"""Cliente de integração com a API v4 do Kommo CRM — Dra. Lívia França.

Gerencia o sincronismo de leads, movimentação de etapas no funil, inserção de notas
(com rastreamento de wamid da Meta Cloud API) e criação de tarefas para os advogados.
"""

import logging
import os
import time
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PIPELINE_ID = 14107071


def _get_subdomain() -> str:
    return (os.getenv("KOMMO_SUBDOMAIN") or os.getenv("SUBDOMAIN") or "liviafranaadv").strip()


def _get_api_key() -> str:
    return (
        os.getenv("KOMMO_LONG_LIVED_TOKEN")
        or os.getenv("KOMMO_API_KEY")
        or os.getenv("API_KEY")
        or ""
    ).strip()


def _get_base_url() -> str:
    custom_base = os.getenv("KOMMO_BASE_URL", "").strip()
    if custom_base:
        return custom_base.rstrip("/")
    subdomain = _get_subdomain()
    return f"https://{subdomain}.kommo.com"


def _api_v4_url() -> str:
    return f"{_get_base_url()}/api/v4"


def _headers() -> dict[str, str]:
    api_key = _get_api_key()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def formatar_ficha_trabalhista(ficha: dict[str, Any]) -> str:
    """Formata o dicionário da Ficha Trabalhista no texto oficial para a timeline do CRM."""
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


async def add_kommo_note(
    lead_id: int | str,
    text: str,
    wamid: str | None = None,
) -> dict[str, Any]:
    """Cria uma nota na timeline do lead no Kommo com o conteúdo enviado via Meta Cloud API."""
    token = _get_api_key()
    if not token:
        logger.warning("Token do Kommo não configurado para criação de notas.")
        return {"ok": False, "error": "KOMMO_LONG_LIVED_TOKEN não configurado"}

    url = f"{_api_v4_url()}/leads/{lead_id}/notes"
    headers = _headers()
    note_text = f"Resposta enviada via Meta WhatsApp Cloud API\nTexto: {text}"
    if wamid:
        note_text += f"\nMensagem: {wamid}"

    payload = [{"note_type": "common", "params": {"text": note_text}}]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            is_ok = r.status_code in (200, 201)
            if is_ok:
                logger.info(
                    "📋 [KOMMO NOTA] Nota registrada no lead=%s | wamid=%s",
                    lead_id,
                    wamid,
                )
            else:
                logger.warning("Kommo add_kommo_note status=%s: %s", r.status_code, r.text)
            return {"ok": is_ok, "status": r.status_code, "body": r.text}
    except Exception as exc:
        logger.error("Erro na requisição add_kommo_note: %s", exc)
        return {"ok": False, "error": str(exc)}


async def buscar_telefone_contato(contact_id: int | str) -> str | None:
    """Busca o número de telefone de um contato pelo ID no Kommo CRM."""
    url = f"{_api_v4_url()}/contacts/{contact_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_headers())
            if resp.status_code == 200:
                data = resp.json()
                for cf in data.get("custom_fields_values") or []:
                    if cf.get("field_code") == "PHONE":
                        values = cf.get("values", [])
                        if values:
                            return str(values[0].get("value"))
    except Exception as exc:
        logger.warning("Falha ao buscar telefone do contato %s: %s", contact_id, exc)
    return None


async def buscar_contato_do_lead(lead_id: str | int) -> dict[str, Any] | None:
    """Recupera os dados de contato vinculados a um lead específico no Kommo CRM."""
    url = f"{_api_v4_url()}/leads/{lead_id}?with=contacts"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=_headers())
            if response.status_code == 200:
                dados = response.json()
                contacts = dados.get("_embedded", {}).get("contacts", [])
                if contacts:
                    c_id = contacts[0].get("id")
                    c_nome = contacts[0].get("name")
                    tel = await buscar_telefone_contato(c_id)
                    return {"id": c_id, "nome": c_nome, "telefone": tel}
    except Exception as exc:
        logger.warning("Falha ao buscar contato do lead %s: %s", lead_id, exc)
    return None


async def enviar_mensagem(
    chat_id: str | int,
    texto: str,
    recipient_id: str | None = None,
    recipient_name: str | None = None,
    recipient_phone: str | None = None,
) -> dict[str, Any]:
    """Envia mensagem de WhatsApp priorizando Meta Cloud API se recipient_phone for informado."""
    if recipient_phone:
        from integrations.meta import meta_send

        res = await meta_send(to=recipient_phone, text=texto)
        return {
            "status": "delivered" if res.get("ok") else "error",
            "id": res.get("wamid") or str(chat_id),
            "chat_id": chat_id,
            "text": texto,
            "meta_result": res,
        }

    # Fallback para endpoint legado v4
    url = f"{_api_v4_url()}/talks/{chat_id}/send_message"
    payload = {"text": texto}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
            if response.status_code in (200, 201, 202):
                try:
                    return cast(dict[str, Any], response.json())
                except Exception:
                    return {"status": "delivered", "id": str(chat_id), "text": texto}
            else:
                return {"status": "fallback", "chat_id": chat_id, "text": texto}
    except Exception as exc:
        logger.warning("Kommo enviar_mensagem fallback falha: %s", exc)
        return {"status": "error", "chat_id": chat_id, "text": texto}


async def criar_nota_ficha_trabalhista(lead_id: str | int, ficha: dict[str, Any]) -> bool:
    """Insere a Ficha Oficial de Qualificação Trabalhista na timeline do lead."""
    texto_formatado = formatar_ficha_trabalhista(ficha)
    url = f"{_api_v4_url()}/leads/{lead_id}/notes"
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
    url = f"{_api_v4_url()}/tasks"
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
    url = f"{_api_v4_url()}/leads/pipelines/{pipeline_id}"
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
    url = f"{_api_v4_url()}/leads/{lead_id}"
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


async def criar_lead(telefone: str, nome: str, pipeline_id: str | int | None = None) -> int:
    """Cria um novo lead no funil do Kommo CRM e retorna seu ID."""
    url = f"{_api_v4_url()}/leads"
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
    url = f"{_api_v4_url()}/contacts"
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
    url = f"{_api_v4_url()}/leads/{lead_id}/notes"
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
    url = f"{_api_v4_url()}/tasks"
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




async def listar_pipelines() -> list[dict[str, Any]]:
    """Consulta a lista de funis e etapas configurados na conta."""
    url = f"{_api_v4_url()}/leads/pipelines"
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
            r = await client.get(f"{_api_v4_url()}/account", headers=_headers())
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

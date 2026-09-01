"""Script de Exploração e Auditoria Integral da Camada 1: Kommo CRM API v4 & Talks.

Executa chamadas diretas a todos os endpoints disponíveis da Kommo, exibe os
responses completos e salva um relatório JSON detalhado e integral em disco.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Adiciona o diretório raiz ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configura codificação UTF-8 para stdout no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

SUBDOMAIN = (os.getenv("KOMMO_SUBDOMAIN") or os.getenv("SUBDOMAIN") or "liviafranaadv").strip()
API_KEY = (os.getenv("KOMMO_API_KEY") or os.getenv("API_KEY") or "").strip()
BASE_URL = f"https://{SUBDOMAIN}.kommo.com/api/v4"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def requisitar(
    client: httpx.AsyncClient,
    metodo: str,
    endpoint: str,
    payload: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Executa requisição HTTP e retorna payload e metadados integrais."""
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith("/") else endpoint
    print(f"\n{'='*80}\n📡 [{metodo}] {url}\n{'='*80}")
    try:
        if metodo.upper() == "GET":
            response = await client.get(url, headers=HEADERS)
        elif metodo.upper() == "POST":
            response = await client.post(url, json=payload, headers=HEADERS)
        elif metodo.upper() == "PATCH":
            response = await client.patch(url, json=payload, headers=HEADERS)
        else:
            response = await client.request(metodo, url, json=payload, headers=HEADERS)

        status = response.status_code
        print(f"Status HTTP: {status}")

        try:
            dados = response.json()
        except Exception:
            dados = {"raw_text": response.text}

        print("Response JSON Integral:")
        print(json.dumps(dados, indent=2, ensure_ascii=False))

        return {
            "endpoint": endpoint,
            "metodo": metodo,
            "url": url,
            "status_http": status,
            "response": dados,
        }
    except Exception as exc:
        print(f"❌ Erro na requisição: {exc}")
        return {
            "endpoint": endpoint,
            "metodo": metodo,
            "url": url,
            "erro": str(exc),
        }


async def main() -> None:
    print(f"🚀 Iniciando Diagnóstico Integral da Kommo CRM API")
    print(f"Subdomínio: {SUBDOMAIN}")
    print(f"Token Configurado: {API_KEY[:10]}...{API_KEY[-10:] if len(API_KEY)>20 else ''}")

    resultados: dict[str, Any] = {
        "subdomain": SUBDOMAIN,
        "base_url": BASE_URL,
        "endpoints": {},
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        # 1. Informações da Conta
        res_account = await requisitar(client, "GET", "/account?with=amojo_id,version")
        resultados["endpoints"]["account"] = res_account

        # 2. Funis e Etapas (Pipelines & Statuses)
        res_pipelines = await requisitar(client, "GET", "/leads/pipelines")
        resultados["endpoints"]["pipelines"] = res_pipelines

        # 3. Campos Personalizados de Leads
        res_custom_fields = await requisitar(client, "GET", "/leads/custom_fields")
        resultados["endpoints"]["custom_fields"] = res_custom_fields

        # 4. Listagem Recente de Leads
        res_leads = await requisitar(client, "GET", "/leads?limit=5&with=contacts")
        resultados["endpoints"]["leads_recentes"] = res_leads

        # 5. Listagem Recente de Conversas (Talks)
        res_talks = await requisitar(client, "GET", "/talks?limit=5")
        resultados["endpoints"]["talks_recentes"] = res_talks

        # 6. Teste de Leitura de Talk Específica (ex: talk_id = 439)
        res_talk_detail = await requisitar(client, "GET", "/talks/439")
        resultados["endpoints"]["talk_439"] = res_talk_detail

        # 7. Teste do Endpoint de Envio de Mensagem (POST /talks/{talk_id}/send_message)
        res_send = await requisitar(
            client,
            "POST",
            "/talks/439/send_message",
            payload={"text": "Diagnóstico de integração da Camada 1: Auto_Law Lívia França."},
        )
        resultados["endpoints"]["send_message_talk_439"] = res_send

        # 8. Teste de Criação de Nota de Ficha na Timeline do Lead (ex: lead_id = 20429066)
        res_note = await requisitar(
            client,
            "POST",
            "/leads/20429066/notes",
            payload=[
                {
                    "note_type": "common",
                    "params": {
                        "text": "📋 [DIAGNÓSTICO CAMADA 1] Verificação de integridade da API de Notas do Kommo."
                    },
                }
            ],
        )
        resultados["endpoints"]["criar_nota_lead_20429066"] = res_note

    # Salva o arquivo de auditoria completo e sem truncamento
    audit_file = ROOT_DIR / "kommo_endpoints_audit.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f" Relatório integral salvo com sucesso em: {audit_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

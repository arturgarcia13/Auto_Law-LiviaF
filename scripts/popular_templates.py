"""Script para consulta e população de etapas da pipeline e templates do Kommo CRM.

1. Consulta a API do Kommo para a pipeline 14107071 e salva os IDs das 5 etapas no .env.
2. Consulta GET /api/v4/chats/templates e salva em app/data/chat_templates.json.
3. Se a API falhar ou estiver indisponível/mock, utiliza templates padrão da Dra. Lívia França.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
TEMPLATES_FILE = BASE_DIR / "app" / "data" / "chat_templates.json"

DEFAULT_PIPELINE_ID = 14107071

# Templates padrão da advocacia trabalhista da Dra. Lívia França
DEFAULT_TEMPLATES: dict[str, str] = {
    "saudacao_inicial": (
        "Olá! Tudo bem? Aqui é do escritório trabalhista da Dra. Lívia França. "
        "Para que possamos te ajudar a buscar os seus direitos, me explique melhor o seu caso."
    ),
    "recepcao": (
        "Olá! tudo bem? Aqui é do escritório trabalhista da Dra. Lívia França.\n\n"
        "Para que possamos te ajudar a buscar os seu direitos, me explique melhor o seu caso.\n\n"
        "Você trabalhou quanto tempo sem carteira assinada?"
    ),
    "analise_viabilidade": (
        "Para entender melhor sua situação, me conte: você foi demitido ou pediu demissão? "
        "E há quanto tempo saiu da empresa?"
    ),
    "solicitar_documentos": (
        "Olá, como está? Você conseguiu separar os documentos que te informei para darmos "
        "continuidade ao seu caso? Se possível, me envie o quanto antes para que possamos "
        "dar prioridade ao seu atendimento."
    ),
    "cobrando_documentacao": (
        "Olá, como está?\n\n"
        "Você conseguiu separar os documentos que te informei para darmos continuidade ao caso?\n\n"
        "Se possível, me envie o quanto antes para darmos prioridade ao seu atendimento.\n\n"
        "Você consegue me enviar os documentos ainda hoje? 😊"
    ),
    "lead_qualificado": (
        "Com base nas informações que você me passou, seu caso tem viabilidade jurídica para "
        "buscarmos seus direitos."
    ),
    "oferta_contrato": (
        "Nosso trabalho é no modelo de êxito (você só paga honorários se e quando receber seus "
        "valores ao final do processo). Gostaria que enviássemos o contrato e procuração?"
    ),
    "explicacao_contrato": (
        "Nosso contrato funciona assim: não há cobrança inicial. Nosso percentual de honorários "
        "é cobrado apenas sobre o valor que você efetivamente receber ao final da ação."
    ),
    "envio_contrato": (
        "Perfeito! Já compilei todas as informações do seu caso. A Dra. Lívia França e nossa "
        "equipe jurídica irão enviar seu contrato e procuração agora para formalizarmos o início."
    ),
    "caso_inviavel": (
        "Analisamos atentamente o seu relato. Infelizmente, pelas regras da legislação trabalhista "
        "e prazos legais, não identificamos viabilidade jurídica para mover uma ação no momento. "
        "Agradecemos muito o seu contato e ficamos à disposição!"
    ),
    "transbordo_humano": (
        "Entendido! Para tratar com o devido cuidado e atenção a esse detalhe específico, estou "
        "transferindo seu atendimento para um de nossos advogados especialistas. Em instantes "
        "falaremos com você por aqui."
    ),
    "escritorio": (
        "Nosso escritório físico fica localizado no endereço: R. 14, 03 - Jereissati I, "
        "Maracanaú - CE, 61900-270. Mas atendemos clientes de todo o Brasil de forma digital "
        "para maior comodidade e agilidade no atendimento."
    ),
    "follow_up_01": (
        "Oi! Tudo bem? Lembrei de você e daquela situação trabalhista que conversamos.\n\n"
        "Queria saber se você conseguiu resolver essa questão ou se ainda ficou pendente.\n\n"
        "Quer me contar como ficou?\n\nAinda precisa de ajuda?"
    ),
    "follow_up_02": (
        "Oi! Passando rapidinho porque lembrei do seu caso esses dias.\n\n"
        "Você conseguiu resolver aquela situação com a empresa e receber o que tinha direito?"
    ),
    "follow_up_03": (
        "Oi, tudo bem? Só queria retomar nosso contato para saber se você conseguiu dar "
        "andamento naquela questão trabalhista.\n\n"
        "Se ainda não resolveu, podemos conversar novamente para ver o que pode ser feito.\n\n"
        "Você ainda precisa de ajuda com isso?"
    ),
    "follow_up_04": (
        "Oi, Vi aqui nossa conversa e não queria deixar seu caso parado sem saber se resolveu.\n\n"
        "Se ainda estiver com aquela situação pendente, podemos retomar e analisar tudo.\n\n"
        "Como ficou essa situação para você?"
    ),
    "follow_up_05": (
        "Oi! Como você não respondeu mais às nossas mensagens, acredito que tenha conseguido "
        "resolver sua situação e receber os direitos trabalhistas devidos.\n\n"
        "De toda forma, se ainda tiver alguma dúvida, pode contar com a gente.\n\n"
        "Posso deixar seu atendimento encerrado por aqui?"
    ),
}

# IDs de fallback das etapas caso a API esteja offline
FALLBACK_STAGE_IDS: dict[str, int] = {
    "KOMMO_STATUS_LEADS_ENTRADA": 108897143,
    "KOMMO_STATUS_ANALISE_VIABILIDADE": 108897147,
    "KOMMO_STATUS_LEAD_QUALIFICADO": 108897151,
    "KOMMO_STATUS_OFERTA_CONTRATO": 108897155,
    "KOMMO_STATUS_ENVIO_CONTRATO": 108897159,
}


def _normalizar_texto(texto: str) -> str:
    """Remove acentuação e padroniza texto em minúsculas com sublinhados."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento.strip().lower())
    return limpo.strip("_")


def obter_credenciais() -> tuple[str, str]:
    """Recupera o subdomínio e a API Key do ambiente ou .env."""
    load_dotenv(dotenv_path=ENV_FILE)
    subdomain = os.getenv("KOMMO_SUBDOMAIN") or os.getenv("SUBDOMAIN") or "liviafranaadv"
    api_key = os.getenv("KOMMO_API_KEY") or os.getenv("API_KEY") or ""
    return subdomain.strip(), api_key.strip()


def atualizar_env_com_etapas(
    etapas_ids: Mapping[str, int | str] | dict[str, Any],
    pipeline_id: int = DEFAULT_PIPELINE_ID,
) -> None:
    """Grava/atualiza as variáveis das etapas no arquivo .env local."""

    linhas: list[str] = []
    if ENV_FILE.exists():
        conteudo = ENV_FILE.read_text(encoding="utf-8")
        linhas = conteudo.splitlines()

    variaveis_para_gravar = {
        "KOMMO_PIPELINE_ID": str(pipeline_id),
        **{k: str(v) for k, v in etapas_ids.items()},
    }

    novas_linhas: list[str] = []
    chaves_ja_processadas: set[str] = set()

    for linha in linhas:
        linha_strip = linha.strip()
        if "=" in linha_strip and not linha_strip.startswith("#"):
            chave, _ = linha_strip.split("=", 1)
            chave = chave.strip()
            if chave in variaveis_para_gravar:
                novas_linhas.append(f"{chave}={variaveis_para_gravar[chave]}")
                chaves_ja_processadas.add(chave)
                continue
        novas_linhas.append(linha)

    # Adicionar chaves faltantes
    chaves_restantes = [k for k in variaveis_para_gravar if k not in chaves_ja_processadas]
    if chaves_restantes:
        if novas_linhas and novas_linhas[-1] != "":
            novas_linhas.append("")
        for k in chaves_restantes:
            novas_linhas.append(f"{k}={variaveis_para_gravar[k]}")

    ENV_FILE.write_text("\n".join(novas_linhas) + "\n", encoding="utf-8")
    logger.info(f"Variáveis de etapas da pipeline gravadas no {ENV_FILE.name} com sucesso.")


def consultar_etapas_pipeline(
    subdomain: str, api_key: str, pipeline_id: int = DEFAULT_PIPELINE_ID
) -> dict[str, int]:
    """Consulta a API do Kommo para obter os IDs das 5 etapas da pipeline."""
    if not api_key:
        logger.warning("API_KEY do Kommo não configurada. Usando etapas padrão de fallback.")
        return FALLBACK_STAGE_IDS

    url = f"https://{subdomain}.kommo.com/api/v4/leads/pipelines/{pipeline_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
        if response.status_code != 200:
            logger.warning(
                f"Falha ao consultar pipeline {pipeline_id}: status={response.status_code}."
            )
            return FALLBACK_STAGE_IDS

        dados = response.json()
        statuses = dados.get("_embedded", {}).get("statuses", [])
        if not statuses:
            logger.warning("Nenhum status encontrado na resposta da API. Usando fallback.")
            return FALLBACK_STAGE_IDS

        # Mapeamento por correspondência de nome ou ordem
        mapeamento: dict[str, int] = {}
        for st in statuses:
            nome_norm = _normalizar_texto(st.get("name", ""))
            st_id = int(st.get("id"))

            if "entrada" in nome_norm and "KOMMO_STATUS_LEADS_ENTRADA" not in mapeamento:
                mapeamento["KOMMO_STATUS_LEADS_ENTRADA"] = st_id
            elif "viabilidade" in nome_norm:
                mapeamento["KOMMO_STATUS_ANALISE_VIABILIDADE"] = st_id
            elif "qualificado" in nome_norm and "KOMMO_STATUS_LEAD_QUALIFICADO" not in mapeamento:
                mapeamento["KOMMO_STATUS_LEAD_QUALIFICADO"] = st_id
            elif "oferta" in nome_norm and "KOMMO_STATUS_OFERTA_CONTRATO" not in mapeamento:
                mapeamento["KOMMO_STATUS_OFERTA_CONTRATO"] = st_id
            elif "envio" in nome_norm and "KOMMO_STATUS_ENVIO_CONTRATO" not in mapeamento:
                mapeamento["KOMMO_STATUS_ENVIO_CONTRATO"] = st_id

        # Preenche com fallback qualquer etapa que não tenha sido encontrada
        for chave, fallback_id in FALLBACK_STAGE_IDS.items():
            if chave not in mapeamento:
                mapeamento[chave] = fallback_id

        return mapeamento

    except Exception as exc:
        logger.warning(f"Erro ao conectar com API do Kommo para pipeline: {exc}. Usando fallback.")
        return FALLBACK_STAGE_IDS


def consultar_e_salvar_templates(subdomain: str, api_key: str) -> dict[str, Any]:
    """Consulta GET /api/v4/chats/templates e salva em app/data/chat_templates.json."""
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    templates_dict = dict(DEFAULT_TEMPLATES)
    raw_list: list[dict[str, Any]] = []

    if api_key:
        url = f"https://{subdomain}.kommo.com/api/v4/chats/templates"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.get(url, headers=headers, timeout=15.0)
            if response.status_code == 200:
                dados = response.json()
                raw_list = dados.get("_embedded", {}).get("chat_templates", [])
                for item in raw_list:
                    nome = item.get("name", "")
                    conteudo = item.get("content", "")
                    if nome and conteudo:
                        chave_norm = _normalizar_texto(nome)
                        templates_dict[chave_norm] = conteudo
                logger.info(f"{len(raw_list)} templates resgatados da API do Kommo com sucesso.")
            else:
                logger.warning(
                    f"Status {response.status_code} ao buscar templates. Usando padrão."
                )
        except Exception as exc:
            logger.warning(f"Erro ao buscar templates da API: {exc}. Usando padrão.")
    else:
        logger.info("API_KEY vazia. Utilizando templates padrão da Dra. Lívia França.")

    resultado_final: dict[str, Any] = {
        "pipeline_id": DEFAULT_PIPELINE_ID,
        "templates": templates_dict,
        "raw_templates": raw_list,
    }

    TEMPLATES_FILE.write_text(
        json.dumps(resultado_final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"Templates salvos em {TEMPLATES_FILE}")
    return resultado_final


def popular_templates(
    pipeline_id: int = DEFAULT_PIPELINE_ID,
) -> tuple[dict[str, int], dict[str, Any]]:
    """Executa o fluxo completo de população de etapas no .env e templates no JSON."""
    subdomain, api_key = obter_credenciais()
    etapas = consultar_etapas_pipeline(subdomain, api_key, pipeline_id)
    atualizar_env_com_etapas(etapas, pipeline_id)
    templates = consultar_e_salvar_templates(subdomain, api_key)
    return etapas, templates


if __name__ == "__main__":
    logger.info("Iniciando populacao de etapas e templates do Kommo CRM...")
    etapas_res, templates_res = popular_templates()
    print("\n[OK] Etapas salvas no .env:")
    for k, v in etapas_res.items():
        print(f"  {k} = {v}")
    print(f"\n[OK] Total de templates mapeados: {len(templates_res.get('templates', {}))}")

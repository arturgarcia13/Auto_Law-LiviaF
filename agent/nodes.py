"""Funções de nós executáveis pelo grafo de estados do LangGraph (Dra. Lívia França)."""

import logging
import os
from typing import Any

from google import genai
from google.genai import types

from agent.prompts import SYSTEM_PROMPT_LIVIA_FRANCA
from agent.state import (
    FichaTrabalhista,
    LeadState,
    criar_ficha_vazia,
    formatar_ficha_oficial,
)
from integrations.kommo import atualizar_lead, criar_nota, criar_tarefa

logger = logging.getLogger(__name__)


def _get_gemini_client() -> genai.Client | None:
    """Retorna o cliente Google Gemini se a chave de API estiver configurada."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key.strip())
    except Exception as exc:
        logger.warning("Falha ao inicializar Gemini Client: %s", exc)
        return None


async def leads_entrada_node(state: LeadState) -> dict[str, Any]:
    """Nó 1: Leads de Entrada.

    Acolhe o lead no WhatsApp com empatia e escuta ativa,
    inicializa a Ficha Trabalhista e avança para a fase de Análise de Viabilidade.
    """
    logger.info("👉 [NÓ 1: LEADS DE ENTRADA] Acolhendo lead e inicializando ficha...")
    ficha_atual: FichaTrabalhista = criar_ficha_vazia()
    if "ficha" in state and isinstance(state["ficha"], dict):
        ficha_atual.update(state["ficha"])

    lead_id = state.get("lead_id")
    if lead_id:
        try:
            logger.info("🔄 [KOMMO] Atualizando lead=%s -> 'analise_viabilidade'", lead_id)
            await atualizar_lead(lead_id, campo_status_ia="analise_viabilidade")
        except Exception as exc:  # pragma: no cover
            logger.warning("Falha ao atualizar lead no Kommo no nó leads_entrada: %s", exc)

    return {
        "fase": "analise_viabilidade",
        "ficha": ficha_atual,
        "humano_ativo": False,
    }


async def analise_viabilidade_node(state: LeadState) -> dict[str, Any]:
    """Nó 2: Análise de Viabilidade.

    Conduz o diálogo conversacional fluido com o Google Gemini Flash,
    investiga dinamicamente os 17 campos da Ficha e responde com acolhimento.
    """
    logger.info("🔍 [NÓ 2: ANÁLISE DE VIABILIDADE] Analisando relato trabalhista...")
    ficha_atual: FichaTrabalhista = criar_ficha_vazia()
    if "ficha" in state and isinstance(state["ficha"], dict):
        ficha_atual.update(state["ficha"])

    lead_id = state.get("lead_id")
    motivo_inviavel = state.get("motivo_inviabilidade")
    messages = list(state.get("messages", []))

    # Constrói o histórico para a API do Gemini
    historico_conteudos: list[types.Content] = []
    for msg in messages:
        if isinstance(msg, dict):
            r = msg.get("role", "user")
            c = str(msg.get("content", ""))
        else:
            r = getattr(msg, "type", "user")
            c = getattr(msg, "content", str(msg))

        gemini_role = "user" if r in ("user", "human") else "model"
        historico_conteudos.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=c)],
            )
        )

    # Invocação do Google Gemini Flash
    client = _get_gemini_client()
    resposta_texto = ""
    if client and historico_conteudos:
        try:
            logger.info(
                "🤖 [CHAMANDO GEMINI FLASH] Enviando histórico de %d mensagens...",
                len(historico_conteudos),
            )
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_LIVIA_FRANCA,
                temperature=0.4,
            )
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=historico_conteudos,
                config=config,
            )
            if response and response.text:
                resposta_texto = response.text.strip()
                logger.info("✅ [GEMINI RESPOSTA GERADA]: '%s'", resposta_texto)
        except Exception as exc:
            logger.error("❌ [GEMINI ERRO]: %s", exc)

    if not resposta_texto:
        # Resposta amigável padrão se Gemini estiver offline ou sem chave
        resposta_texto = (
            "Olá! Tudo bem? Aqui é do escritório trabalhista da Dra. Lívia França. "
            "Para que possamos te orientar da melhor forma, me explique melhor: "
            "o que aconteceu no seu trabalho?"
        )

    messages.append({"role": "assistant", "content": resposta_texto})

    # Caso identificado como inviável
    if motivo_inviavel:
        logger.warning("⚠️ [CASO INVIÁVEL DETECTADO] Motivo: '%s'", motivo_inviavel)
        if lead_id:
            try:
                texto_nota = (
                    f"⚠️ PARECER DA IA — CASO INVIÁVEL (Dra. Lívia França)\n\n"
                    f"Motivo: {motivo_inviavel}\n"
                    f"Orientação: Caso mantido em Análise de Viabilidade para conferência."
                )
                logger.info("📋 [KOMMO NOTA] Registrando inviabilidade no lead=%s...", lead_id)
                await criar_nota(lead_id, texto_nota)
            except Exception as exc:  # pragma: no cover
                logger.warning("Falha ao registrar nota de inviabilidade no Kommo: %s", exc)

        return {
            "fase": "analise_viabilidade",
            "motivo_inviabilidade": motivo_inviavel,
            "ficha": ficha_atual,
            "messages": messages,
            "humano_ativo": False,
        }

    # Se a viabilidade foi confirmada positivamente
    if state.get("fase") == "lead_qualificado":
        logger.info("✅ [CASO QUALIFICADO] Viabilidade positiva confirmada!")
        return {
            "fase": "lead_qualificado",
            "ficha": ficha_atual,
            "motivo_inviabilidade": None,
            "messages": messages,
            "humano_ativo": False,
        }

    # Caso continue em diálogo investigativo
    campos_preenchidos = [k for k, v in ficha_atual.items() if v]
    logger.info(
        "💬 [VIABILIDADE EM ANDAMENTO] %d de 17 campos identificados: %s",
        len(campos_preenchidos),
        campos_preenchidos,
    )
    return {
        "fase": "analise_viabilidade",
        "ficha": ficha_atual,
        "messages": messages,
        "humano_ativo": False,
    }


async def lead_qualificado_node(state: LeadState) -> dict[str, Any]:
    """Nó 3: Lead Qualificado.

    Compila a Ficha Oficial da Dra. Lívia França com os 17 campos,
    insere a Ficha como Nota na timeline do lead no Kommo e transita para 'oferta_contrato'.
    """
    logger.info("⭐ [NÓ 3: LEAD QUALIFICADO] Formatando Ficha Oficial de 17 campos...")
    ficha_atual: FichaTrabalhista = state.get("ficha") or criar_ficha_vazia()
    ficha_formatada = formatar_ficha_oficial(ficha_atual)

    lead_id = state.get("lead_id")
    if lead_id:
        try:
            logger.info("📋 [KOMMO NOTA] Inserindo Ficha Oficial no lead=%s...", lead_id)
            await criar_nota(lead_id, ficha_formatada)
            await atualizar_lead(lead_id, campo_status_ia="oferta_contrato")
        except Exception as exc:  # pragma: no cover
            logger.warning("Falha ao salvar ficha ou atualizar lead no Kommo: %s", exc)

    return {
        "fase": "oferta_contrato",
        "ficha": ficha_atual,
        "humano_ativo": False,
    }


async def oferta_contrato_node(state: LeadState) -> dict[str, Any]:
    """Nó 4: Oferta de Contrato.

    Apresenta a proposta de honorários no modelo de êxito (ad exitum).
    Se o cliente confirmou o aceite (aceitou_oferta = True), transita para 'envio_contrato'.
    Caso contrário, permanece em 'oferta_contrato' prestando esclarecimentos sobre a contratação.
    """
    aceitou = state.get("aceitou_oferta", False)
    status_str = "ACEITO" if aceitou else "AGUARDANDO/ESCLARECENDO"
    logger.info("📝 [NÓ 4: OFERTA DE CONTRATO] Status de aceite: %s", status_str)

    if aceitou:
        logger.info("🎉 [ACEITE CONFIRMADO] Cliente concordou! -> envio_contrato...")
        return {
            "fase": "envio_contrato",
            "aceitou_oferta": True,
            "humano_ativo": False,
        }

    return {
        "fase": "oferta_contrato",
        "aceitou_oferta": False,
        "humano_ativo": False,
    }


async def envio_contrato_node(state: LeadState) -> dict[str, Any]:
    """Nó 5: Envio do Contrato (Entrada do Humano).

    Silencia o bot conversacional (humano_ativo = True),
    cria uma Tarefa de urgência no Kommo para que o advogado humano envie o contrato e procuração,
    e finaliza o atendimento automatizado da IA.
    """
    logger.info("🚨 [NÓ 5: ENVIO CONTRATO] Silenciando bot (humano_ativo=True)...")
    lead_id = state.get("lead_id")
    if lead_id:
        try:
            logger.info("📌 [KOMMO TAREFA] Criando tarefa de contrato (lead=%s)...", lead_id)
            await criar_tarefa(
                lead_id=lead_id,
                texto="📝 Enviar minuta de contrato e procuração para o cliente qualificado",
                prazo_horas=2,
            )
            await atualizar_lead(lead_id, campo_status_ia="envio_contrato")
        except Exception as exc:  # pragma: no cover
            logger.warning("Falha ao criar tarefa no Kommo para envio do contrato: %s", exc)

    return {
        "fase": "envio_contrato",
        "humano_ativo": True,
    }


# ==============================================================================
# Nós de Retrocompatibilidade
# ==============================================================================


async def triagem_node(state: LeadState) -> dict[str, Any]:
    """Nó de triagem legado: redireciona para a lógica de análise de viabilidade."""
    return await analise_viabilidade_node(state)


async def coleta_dados_node(state: LeadState) -> dict[str, Any]:
    """Nó de coleta legado: solicita dados cadastrais para o contrato de honorários."""
    return {"fase": "oferta_contrato"}


async def gerar_contrato_node(state: LeadState) -> dict[str, Any]:
    """Nó de geração de contrato legado."""
    return {"fase": "aguardando_assinatura"}


async def transbordo_node(state: LeadState) -> dict[str, Any]:
    """Nó de transbordo legado: silencia o bot e notifica a equipe jurídica."""
    return {"fase": "transbordo", "humano_ativo": True}


async def pos_assinatura_node(state: LeadState) -> dict[str, Any]:
    """Nó pós-assinatura legado: finaliza ciclo de contratação."""
    return {"fase": "concluido"}

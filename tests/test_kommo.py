"""Testes de integração com a API v4 do Kommo CRM — Dra. Lívia França."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
import respx

from integrations.kommo import (
    add_kommo_note,
    atualizar_etapa_lead,
    atualizar_lead,
    buscar_contato_do_lead,
    criar_contato,
    criar_lead,
    criar_nota,
    criar_nota_ficha_trabalhista,
    criar_tarefa,
    criar_tarefa_envio_contrato,
    enviar_mensagem,
    formatar_ficha_trabalhista,
    listar_pipelines,
    obter_etapas_pipeline,
)

SUBDOMAIN = "liviafranaadv"
BASE_URL = f"https://{SUBDOMAIN}.kommo.com/api/v4"


@pytest.fixture(autouse=True)
def mock_env_kommo() -> Any:
    """Configura variáveis de ambiente mock para os testes do Kommo."""
    with patch.dict(
        "os.environ",
        {
            "KOMMO_SUBDOMAIN": SUBDOMAIN,
            "KOMMO_LONG_LIVED_TOKEN": "fake_jwt_token_12345",
            "META_PHONE_NUMBER_ID": "1226609120527127",
            "META_WHATSAPP_TOKEN": "fake_meta_token",
            "GRAPH_VERSION": "v21.0",
        },
    ):
        yield


@pytest.mark.asyncio
async def test_add_kommo_note_sucesso() -> None:
    """Verifica inserção de nota com wamid no lead da Kommo."""
    lead_id = 20429066
    text = "Olá! Estamos analisando seu caso."
    wamid = "wamid.HBgLNTU4NTk4NDM0NzE0OQUCABEYEkZBRjkyMzYxOTQ0"
    endpoint = f"{BASE_URL}/leads/{lead_id}/notes"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"_embedded": {"notes": [{"id": 12345, "entity_id": lead_id}]}},
        )
        res = await add_kommo_note(lead_id=lead_id, text=text, wamid=wamid)
        assert res["ok"] is True
        assert res["status"] == 200


@pytest.mark.asyncio
async def test_enviar_mensagem_via_meta_quando_telefone_fornecido() -> None:
    """Verifica envio de mensagem priorizando Meta Cloud API se recipient_phone for passado."""
    chat_id = 998877
    texto = "Olá! Como podemos te ajudar?"
    phone = "5585984347149"
    meta_url = "https://graph.facebook.com/v21.0/1226609120527127/messages"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(meta_url).respond(
            status_code=200,
            json={"messages": [{"id": "wamid.12345"}]},
        )
        resposta = await enviar_mensagem(chat_id=chat_id, texto=texto, recipient_phone=phone)
        assert resposta.get("status") == "delivered"
        assert resposta.get("id") == "wamid.12345"


@pytest.mark.asyncio
async def test_enviar_mensagem_fallback_sem_telefone() -> None:
    """Verifica retorno estruturado seguro quando enviado apenas com chat_id (fallback v4)."""
    chat_id = 998877
    texto = "Mensagem legado"
    endpoint = f"{BASE_URL}/talks/{chat_id}/send_message"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"id": 123456, "chat_id": chat_id, "text": texto, "status": "delivered"},
        )
        resposta = await enviar_mensagem(chat_id, texto)
        assert resposta.get("id") == 123456
        assert resposta.get("chat_id") == chat_id


@pytest.mark.asyncio
async def test_formatar_e_criar_nota_ficha_trabalhista() -> None:
    """Verifica formatação completa dos 17 campos e inserção da nota no CRM."""
    lead_id = 554433
    ficha = {
        "data_entrada": "01/02/2021",
        "data_saida": "15/07/2024",
        "funcao": "Operador de Máquinas",
        "salario": "R$ 2.800,00",
        "dias_trabalhados": "Segunda a Sexta (5x2)",
        "dias_folga": "Sábado e Domingo",
        "horario_trabalho": "07h às 17h",
        "intervalo": "30 minutos",
        "carteira_assinada": "Sim, registrada após 6 meses",
        "data_assinatura": "01/08/2021",
        "insalubridade_periculosidade": "Ruído excessivo e óleo mineral sem EPI",
        "horas_extras": "Aproximadamente 10h extras por semana sem pagamento",
        "comissao": "Não recebia",
        "beneficios": "VT pago com desconto de 6%",
        "decimo_terceiro": "Último ano proporcional não quitado",
        "ferias": "2 períodos vencidos",
        "fgts": "Depósitos em atraso e sem multa de 40%",
        "filhos_menores": "2 filhos (4 e 7 anos)",
    }

    texto_formatado = formatar_ficha_trabalhista(ficha)
    assert "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA — DRA. LÍVIA FRANÇA" in texto_formatado
    assert "Operador de Máquinas" in texto_formatado
    assert "R$ 2.800,00" in texto_formatado
    assert "Ruído excessivo" in texto_formatado
    assert "⚖️ PARECER DA IA" in texto_formatado

    endpoint = f"{BASE_URL}/leads/{lead_id}/notes"
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"_embedded": {"notes": [{"id": 789, "entity_id": lead_id}]}},
        )
        sucesso = await criar_nota_ficha_trabalhista(lead_id, ficha)
        assert sucesso is True


@pytest.mark.asyncio
async def test_criar_tarefa_envio_contrato() -> None:
    """Verifica criação de tarefa com prazo para envio de contrato pelo advogado."""
    lead_id = 554433
    endpoint = f"{BASE_URL}/tasks"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"_embedded": {"tasks": [{"id": 456, "entity_id": lead_id}]}},
        )
        sucesso = await criar_tarefa_envio_contrato(lead_id, prazo_horas=2)
        assert sucesso is True


@pytest.mark.asyncio
async def test_obter_etapas_pipeline() -> None:
    """Verifica consulta das etapas da pipeline."""
    pipeline_id = 14107071
    endpoint = f"{BASE_URL}/leads/pipelines/{pipeline_id}"
    statuses_mock = [
        {"id": 108897143, "name": "Etapa de leads de entrada"},
        {"id": 108897147, "name": "Análise de Viabilidade"},
        {"id": 108897151, "name": "Lead Qualificado"},
        {"id": 108897155, "name": "Oferta de Contrato"},
        {"id": 108897159, "name": "Envio do Contrato"},
    ]

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(endpoint).respond(
            status_code=200,
            json={"id": pipeline_id, "_embedded": {"statuses": statuses_mock}},
        )
        etapas = await obter_etapas_pipeline(pipeline_id)
        assert len(etapas) == 5
        assert etapas[0]["id"] == 108897143
        assert etapas[2]["name"] == "Lead Qualificado"


@pytest.mark.asyncio
async def test_atualizar_etapa_lead() -> None:
    """Verifica movimentação de etapa do lead."""
    lead_id = 12345
    status_id = 108897151
    endpoint = f"{BASE_URL}/leads/{lead_id}"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.patch(endpoint).respond(
            status_code=200,
            json={"id": lead_id, "status_id": status_id},
        )
        sucesso = await atualizar_etapa_lead(lead_id, status_id)
        assert sucesso is True


@pytest.mark.asyncio
async def test_criar_lead_baseline() -> None:
    """Verifica assinatura e criação de lead."""
    endpoint = f"{BASE_URL}/leads"
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"_embedded": {"leads": [{"id": 1001}]}},
        )
        lead_id = await criar_lead("5511999999999", "Cliente Teste")
        assert lead_id == 1001


@pytest.mark.asyncio
async def test_criar_contato_baseline() -> None:
    """Verifica assinatura e criação de contato vinculado ao lead."""
    endpoint = f"{BASE_URL}/contacts"
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(endpoint).respond(
            status_code=200,
            json={"_embedded": {"contacts": [{"id": 2001}]}},
        )
        contato_id = await criar_contato(1001, "Cliente Teste", "5511999999999")
        assert contato_id == 2001


@pytest.mark.asyncio
async def test_atualizar_lead_baseline() -> None:
    """Verifica wrapper de atualização de lead com status_id."""
    lead_id = 123
    status_id = 456
    endpoint = f"{BASE_URL}/leads/{lead_id}"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.patch(endpoint).respond(status_code=200, json={"id": lead_id})
        sucesso = await atualizar_lead(lead_id, status_id=status_id)
        assert sucesso is True


@pytest.mark.asyncio
async def test_criar_nota_e_tarefa_baseline() -> None:
    """Verifica funções genéricas de criação de nota e tarefa."""
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post(f"{BASE_URL}/leads/123/notes").respond(status_code=200)
        respx_mock.post(f"{BASE_URL}/tasks").respond(status_code=200)

        sucesso_nota = await criar_nota(123, "Nota de teste")
        assert sucesso_nota is True

        sucesso_tarefa = await criar_tarefa(123, "Tarefa de teste", prazo_horas=3)
        assert sucesso_tarefa is True


@pytest.mark.asyncio
async def test_buscar_contato_do_lead_e_listar_pipelines() -> None:
    """Verifica busca de contato e listagem de pipelines."""
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{BASE_URL}/leads/123?with=contacts").respond(
            status_code=200,
            json={"_embedded": {"contacts": [{"id": 501, "name": "João da Silva"}]}},
        )
        respx_mock.get(f"{BASE_URL}/leads/pipelines").respond(
            status_code=200,
            json={"_embedded": {"pipelines": [{"id": 14107071, "name": "Funil de vendas"}]}},
        )

        contato = await buscar_contato_do_lead(123)
        assert contato is not None
        assert contato.get("id") == 501
        assert contato.get("nome") == "João da Silva"

        pipelines = await listar_pipelines()
        assert len(pipelines) == 1
        assert pipelines[0].get("id") == 14107071

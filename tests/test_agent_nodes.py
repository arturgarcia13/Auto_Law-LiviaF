"""Testes unitários dos nós, ferramentas e grafo de estados do LangGraph (Dra. Lívia França)."""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from agent.graph import (
    build_graph,
    roteador_fases,
    roteador_pos_analise,
    roteador_pos_oferta,
)
from agent.nodes import (
    analise_viabilidade_node,
    coleta_dados_node,
    envio_contrato_node,
    gerar_contrato_node,
    lead_qualificado_node,
    leads_entrada_node,
    oferta_contrato_node,
    pos_assinatura_node,
    transbordo_node,
    triagem_node,
)
from agent.prompts import (
    FORMATO_FICHA_OFICIAL,
    MENSAGEM_ENVIO_CONTRATO,
    PROMPT_OFERTA_HONORARIOS,
    SYSTEM_PROMPT_LIVIA_FRANCA,
)
from agent.state import (
    FichaTrabalhista,
    LeadState,
    criar_ficha_vazia,
    formatar_ficha_oficial,
)
from agent.tools import (
    aceitar_oferta_contrato,
    acionar_transbordo,
    atualizar_kommo,
    gerar_contrato_zapsign,
    gerar_ficha_oficial,
    iniciar_coleta,
    qualificar_lead,
    registrar_inviabilidade,
)

# ==============================================================================
# 1. Testes dos Nós Individuais (Nodes)
# ==============================================================================


@pytest.mark.asyncio
async def test_leads_entrada_node_inicializa_ficha_e_avanca_para_analise() -> None:
    """Verifica se o nó de entrada inicializa a Ficha e avança para analise_viabilidade."""
    state: LeadState = {
        "telefone": "5511999999999",
        "nome_cliente": "Carlos Santos",
        "lead_id": 101,
        "fase": "leads_entrada",
        "messages": [],
    }

    with patch("agent.nodes.atualizar_lead", new_callable=AsyncMock) as mock_atualizar:
        result = await leads_entrada_node(state)

        assert result["fase"] == "analise_viabilidade"
        assert result["humano_ativo"] is False
        assert isinstance(result["ficha"], dict)
        assert "data_entrada" in result["ficha"]
        assert "salario" in result["ficha"]
        mock_atualizar.assert_called_once_with(101, campo_status_ia="analise_viabilidade")


@pytest.mark.asyncio
async def test_analise_viabilidade_node_em_andamento() -> None:
    """Verifica se o diálogo investigativo em andamento mantém a fase analise_viabilidade."""
    ficha_parcial: FichaTrabalhista = {
        "funcao": "Operador de Máquinas",
        "salario": "R$ 2.500,00",
        "carteira_assinada": "Sim",
    }
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "analise_viabilidade",
        "ficha": ficha_parcial,
        "messages": [],
    }

    result = await analise_viabilidade_node(state)
    assert result["fase"] == "analise_viabilidade"
    assert result["humano_ativo"] is False
    assert result["ficha"]["funcao"] == "Operador de Máquinas"
    assert result["ficha"]["salario"] == "R$ 2.500,00"


@pytest.mark.asyncio
async def test_analise_viabilidade_node_caso_inviavel_registra_nota_e_mantem_fase() -> None:
    """Verifica se caso inviável registra nota no Kommo e permanece na fase analise_viabilidade."""
    state: LeadState = {
        "telefone": "5511999999999",
        "lead_id": 202,
        "fase": "analise_viabilidade",
        "motivo_inviabilidade": "Prescrição bienal ultrapassada: demissão ocorreu há 3 anos.",
        "messages": [],
    }

    with patch("agent.nodes.criar_nota", new_callable=AsyncMock) as mock_criar_nota:
        result = await analise_viabilidade_node(state)

        assert result["fase"] == "analise_viabilidade"
        assert "Prescrição bienal" in str(result["motivo_inviabilidade"])
        assert result["humano_ativo"] is False
        mock_criar_nota.assert_called_once()
        texto_nota = mock_criar_nota.call_args[0][1]
        assert "CASO INVIÁVEL" in texto_nota
        assert "Prescrição bienal" in texto_nota


@pytest.mark.asyncio
async def test_analise_viabilidade_node_caso_qualificado_avanca_fase() -> None:
    """Verifica se lead qualificado como viável avança para a fase lead_qualificado."""
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "lead_qualificado",
        "ficha": {
            "funcao": "Motorista",
            "salario": "R$ 3.000,00",
            "horas_extras": "Sim, 2 horas por dia não pagas",
        },
        "messages": [],
    }

    result = await analise_viabilidade_node(state)
    assert result["fase"] == "lead_qualificado"
    assert result["motivo_inviabilidade"] is None


@pytest.mark.asyncio
async def test_lead_qualificado_node_insere_ficha_oficial_no_kommo_e_move_para_oferta() -> None:
    """Verifica se lead qualificado insere a Ficha de 17 campos no Kommo e vai para oferta."""
    ficha_completa: FichaTrabalhista = {
        "data_entrada": "01/02/2021",
        "data_saida": "15/07/2023",
        "funcao": "Auxiliar de Almoxarifado",
        "salario": "R$ 1.800,00",
        "dias_trabalhados": "Segunda a Sábado",
        "dias_folga": "Domingo",
        "horario_trabalho": "07h às 17h",
        "intervalo": "30 minutos",
        "carteira_assinada": "Sim",
        "data_assinatura": "01/02/2021",
        "insalubridade_periculosidade": "Sim, poeira e produtos químicos",
        "horas_extras": "15h mensais não pagas",
        "comissao": "Não",
        "beneficios": "VT e VA",
        "decimo_terceiro": "Pago proporcional",
        "ferias": "1 período vencido não gozado",
        "fgts": "Depósitos em atraso de 8 meses",
        "filhos_menores": "2 filhos (4 e 7 anos)",
    }
    state: LeadState = {
        "telefone": "5511999999999",
        "lead_id": 303,
        "fase": "lead_qualificado",
        "ficha": ficha_completa,
        "messages": [],
    }

    with (
        patch("agent.nodes.criar_nota", new_callable=AsyncMock) as mock_criar_nota,
        patch("agent.nodes.atualizar_lead", new_callable=AsyncMock) as mock_atualizar,
    ):
        result = await lead_qualificado_node(state)

        assert result["fase"] == "oferta_contrato"
        assert result["humano_ativo"] is False

        mock_criar_nota.assert_called_once()
        nota_enviada = mock_criar_nota.call_args[0][1]
        assert "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA — DRA. LÍVIA FRANÇA" in nota_enviada
        assert "Auxiliar de Almoxarifado" in nota_enviada
        assert "Depósitos em atraso de 8 meses" in nota_enviada
        assert "2 filhos (4 e 7 anos)" in nota_enviada
        mock_atualizar.assert_called_once_with(303, campo_status_ia="oferta_contrato")


@pytest.mark.asyncio
async def test_oferta_contrato_node_aguardando_aceite() -> None:
    """Verifica se a oferta de contrato permanece na fase quando o aceite ainda não ocorreu."""
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "oferta_contrato",
        "aceitou_oferta": False,
        "messages": [],
    }

    result = await oferta_contrato_node(state)
    assert result["fase"] == "oferta_contrato"
    assert result["aceitou_oferta"] is False
    assert result["humano_ativo"] is False


@pytest.mark.asyncio
async def test_oferta_contrato_node_aceite_confirmado_avanca_para_envio() -> None:
    """Verifica se com aceite confirmado o nó transita para envio_contrato."""
    state: LeadState = {
        "telefone": "5511999999999",
        "fase": "oferta_contrato",
        "aceitou_oferta": True,
        "messages": [],
    }

    result = await oferta_contrato_node(state)
    assert result["fase"] == "envio_contrato"
    assert result["aceitou_oferta"] is True
    assert result["humano_ativo"] is False


@pytest.mark.asyncio
async def test_envio_contrato_node_silencia_bot_e_cria_tarefa_kommo() -> None:
    """Verifica se o nó de envio de contrato ativa humano_ativo e cria tarefa urgente no CRM."""
    state: LeadState = {
        "telefone": "5511999999999",
        "lead_id": 404,
        "fase": "envio_contrato",
        "messages": [],
    }

    with (
        patch("agent.nodes.criar_tarefa", new_callable=AsyncMock) as mock_criar_tarefa,
        patch("agent.nodes.atualizar_lead", new_callable=AsyncMock) as mock_atualizar,
    ):
        result = await envio_contrato_node(state)

        assert result["fase"] == "envio_contrato"
        assert result["humano_ativo"] is True

        mock_criar_tarefa.assert_called_once_with(
            lead_id=404,
            texto="📝 Enviar minuta de contrato e procuração para o cliente qualificado",
            prazo_horas=2,
        )
        mock_atualizar.assert_called_once_with(404, campo_status_ia="envio_contrato")


# ==============================================================================
# 2. Testes de Retrocompatibilidade de Nós
# ==============================================================================


@pytest.mark.asyncio
async def test_retrocompatibilidade_triagem_e_transbordo_nodes() -> None:
    """Garante compatibilidade com chamadas aos nós legados."""
    state: LeadState = {"telefone": "5511999999999", "fase": "triagem", "messages": []}

    res_triagem = await triagem_node(state)
    assert res_triagem["fase"] == "analise_viabilidade"

    res_coleta = await coleta_dados_node(state)
    assert res_coleta["fase"] == "oferta_contrato"

    res_gerar = await gerar_contrato_node(state)
    assert res_gerar["fase"] == "aguardando_assinatura"

    res_transbordo = await transbordo_node(state)
    assert res_transbordo["fase"] == "transbordo"
    assert res_transbordo["humano_ativo"] is True

    res_pos = await pos_assinatura_node(state)
    assert res_pos["fase"] == "concluido"


# ==============================================================================
# 3. Testes das Tools (Ferramentas)
# ==============================================================================


def test_tools_qualificar_lead() -> None:
    """Verifica invocação da tool qualificar_lead."""
    res = qualificar_lead.invoke(
        {"motivo_qualificacao": "Direito a horas extras e FGTS", "ficha": {"funcao": "Vendedor"}}
    )
    assert res["status"] == "qualificado"
    assert res["motivo"] == "Direito a horas extras e FGTS"
    assert res["ficha"]["funcao"] == "Vendedor"


def test_tools_registrar_inviabilidade() -> None:
    """Verifica invocação da tool registrar_inviabilidade."""
    res = registrar_inviabilidade.invoke(
        {
            "motivo": "Demissão há mais de 2 anos (prescrição bienal)",
            "explicacao_cliente": "Infelizmente o prazo legal de 2 anos já prescreveu.",
        }
    )
    assert res["status"] == "inviavel"
    assert "prescrição" in res["motivo"].lower()


def test_tools_aceitar_oferta_contrato() -> None:
    """Verifica invocação da tool aceitar_oferta_contrato."""
    res_aceito = aceitar_oferta_contrato.invoke({"confirmado": True})
    assert res_aceito["status"] == "aceito"
    assert res_aceito["confirmado"] is True

    res_recusado = aceitar_oferta_contrato.invoke({"confirmado": False})
    assert res_recusado["status"] == "recusado"


def test_tools_gerar_ficha_oficial() -> None:
    """Verifica formatação padrão da Ficha Oficial com todos os 17 campos."""
    ficha = {
        "data_entrada": "10/01/2020",
        "data_saida": "10/01/2023",
        "funcao": "Cozinheiro",
        "salario": "R$ 2.200,00",
        "dias_trabalhados": "6x1",
        "dias_folga": "Terça-feira",
        "horario_trabalho": "15h às 23h30",
        "intervalo": "40 minutos",
        "carteira_assinada": "Sim",
        "data_assinatura": "10/01/2020",
        "insalubridade_periculosidade": "Sim, calor e fogão industrial",
        "horas_extras": "Não pagas",
        "comissao": "Não",
        "beneficios": "Refeição no local e VT",
        "decimo_terceiro": "Pago",
        "ferias": "1 período em dobro",
        "fgts": "Regular",
        "filhos_menores": "1 filho",
    }
    texto = gerar_ficha_oficial.invoke({"ficha": ficha})
    assert "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA — DRA. LÍVIA FRANÇA" in texto
    assert "Cozinheiro" in texto
    assert "fogão industrial" in texto
    assert "1 período em dobro" in texto


def test_tools_atualizar_kommo_e_transbordo() -> None:
    """Verifica tools de Kommo e transbordo."""
    res_kommo = atualizar_kommo.invoke({"lead_id": 123, "etapa": "456"})
    assert res_kommo["status"] == "updated"
    assert res_kommo["lead_id"] == "123"

    res_trans = acionar_transbordo.invoke({"motivo": "Acidente de trabalho grave"})
    assert res_trans["status"] == "transbordo_acionado"
    assert res_trans["humano_ativo"] is True

    res_coleta = iniciar_coleta.invoke({"motivo_qualificacao": "Viabilidade ok"})
    assert res_coleta["status"] == "qualificado"

    res_zap = gerar_contrato_zapsign.invoke({"dados_contrato": {"nome": "Teste"}})
    assert res_zap["status"] == "contrato_solicitado"


# ==============================================================================
# 4. Testes de State e Prompts
# ==============================================================================


def test_criar_ficha_vazia_possui_todos_os_campos() -> None:
    """Verifica se a ficha vazia contém os 17 campos oficiais."""
    ficha = criar_ficha_vazia()
    campos_esperados = [
        "data_entrada",
        "data_saida",
        "funcao",
        "salario",
        "dias_trabalhados",
        "dias_folga",
        "horario_trabalho",
        "intervalo",
        "carteira_assinada",
        "data_assinatura",
        "insalubridade_periculosidade",
        "horas_extras",
        "comissao",
        "beneficios",
        "decimo_terceiro",
        "ferias",
        "fgts",
        "filhos_menores",
    ]
    for campo in campos_esperados:
        assert campo in ficha
        assert ficha[campo] is None  # type: ignore[literal-required]


def test_formatar_ficha_oficial_com_campos_vazios() -> None:
    """Verifica se a formatação trata campos não informados corretamente."""
    texto = formatar_ficha_oficial({})
    assert "· Data de entrada: Não informado" in texto
    assert "· Salário: Não informado" in texto
    assert "⚖️ PARECER DA IA: Caso viável com benefício econômico identificado." in texto


def test_prompts_essenciais_definidos() -> None:
    """Garante que os prompts da Dra. Lívia França contenham as diretrizes fundamentais."""
    assert "Dra. Lívia França" in SYSTEM_PROMPT_LIVIA_FRANCA
    assert "NÃO É UM FORMULÁRIO" in SYSTEM_PROMPT_LIVIA_FRANCA
    assert "prescrição bienal" in SYSTEM_PROMPT_LIVIA_FRANCA.lower()
    assert "ad exitum" in SYSTEM_PROMPT_LIVIA_FRANCA.lower()
    assert "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA" in FORMATO_FICHA_OFICIAL
    assert "êxito" in PROMPT_OFERTA_HONORARIOS.lower()
    assert "Dra. Lívia França" in MENSAGEM_ENVIO_CONTRATO


# ==============================================================================
# 5. Testes do Grafo LangGraph e Roteadores
# ==============================================================================


def test_roteador_fases() -> None:
    """Verifica o roteamento de fases do grafo."""
    assert roteador_fases({"humano_ativo": True}) == "__end__"
    assert roteador_fases({"fase": "leads_entrada"}) == "leads_entrada"
    assert roteador_fases({"fase": "analise_viabilidade"}) == "analise_viabilidade"
    assert roteador_fases({"fase": "lead_qualificado"}) == "lead_qualificado"
    assert roteador_fases({"fase": "oferta_contrato"}) == "oferta_contrato"
    assert roteador_fases({"fase": "envio_contrato"}) == "envio_contrato"
    assert roteador_fases({"fase": "transbordo"}) == "__end__"
    assert roteador_fases({"fase": "concluido"}) == "__end__"


def test_roteadores_condicionais_analise_e_oferta() -> None:
    """Verifica transições condicionais intermediárias."""
    # Pós análise
    assert roteador_pos_analise({"fase": "analise_viabilidade"}) == "__end__"
    assert (
        roteador_pos_analise({"fase": "analise_viabilidade", "motivo_inviabilidade": "Prescrito"})
        == "__end__"
    )
    assert roteador_pos_analise({"fase": "lead_qualificado"}) == "lead_qualificado"

    # Pós oferta
    assert roteador_pos_oferta({"fase": "oferta_contrato", "aceitou_oferta": False}) == "__end__"
    assert (
        roteador_pos_oferta({"fase": "oferta_contrato", "aceitou_oferta": True})
        == "envio_contrato"
    )
    assert roteador_pos_oferta({"fase": "envio_contrato"}) == "envio_contrato"


@pytest.mark.asyncio
async def test_build_graph_execucao_fluxo_completo() -> None:
    """Verifica a compilação e execução end-to-end do grafo através das etapas."""
    checkpointer = MemorySaver()
    app = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "thread_teste_001"}}

    # 1. Entrada inicial do lead
    initial_state: LeadState = {
        "telefone": "5511999999999",
        "nome_cliente": "Maria Aparecida",
        "fase": "leads_entrada",
        "messages": [],
    }

    state_1 = await app.ainvoke(initial_state, config=config)
    assert state_1["fase"] == "analise_viabilidade"
    assert state_1["humano_ativo"] is False

    # 2. Lead é qualificado como viável
    qualificado_state: LeadState = {
        "fase": "lead_qualificado",
        "ficha": {
            "funcao": "Recepcionista",
            "salario": "R$ 1.900,00",
            "horas_extras": "2h diárias",
        },
    }
    state_2 = await app.ainvoke(qualificado_state, config=config)
    assert state_2["fase"] == "oferta_contrato"

    # 3. Lead aceita a oferta de honorários no êxito
    aceite_state: LeadState = {
        "aceitou_oferta": True,
    }
    state_3 = await app.ainvoke(aceite_state, config=config)
    assert state_3["fase"] == "envio_contrato"
    assert state_3["humano_ativo"] is True

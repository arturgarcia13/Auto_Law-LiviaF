"""Definição do estado conversacional do agente (StateGraph TypedDict)."""

from typing import Any, Literal

from typing_extensions import TypedDict

FaseLead = Literal[
    "leads_entrada",  # Nova conversa recebida no WhatsApp
    "analise_viabilidade",  # Diálogo natural, investigação dos 17 campos e análise jurídica
    "lead_qualificado",  # Caso viável confirmado, Ficha Oficial gerada no CRM
    "oferta_contrato",  # Apresentação da proposta de honorários no êxito
    "envio_contrato",  # Humano assume (humano_ativo=True) e tarefa criada no Kommo
    # Fases de compatibilidade
    "triagem",
    "coleta",
    "aguardando_assinatura",
    "transbordo",
    "concluido",
]


class FichaTrabalhista(TypedDict, total=False):
    """Estrutura oficial dos 17 campos de qualificação da Dra. Lívia França."""

    data_entrada: str | None
    data_saida: str | None
    funcao: str | None
    salario: str | None
    dias_trabalhados: str | None
    dias_folga: str | None
    horario_trabalho: str | None
    intervalo: str | None
    carteira_assinada: str | None
    data_assinatura: str | None
    insalubridade_periculosidade: str | None
    horas_extras: str | None
    comissao: str | None
    beneficios: str | None
    decimo_terceiro: str | None
    ferias: str | None
    fgts: str | None
    filhos_menores: str | None


class LeadState(TypedDict, total=False):
    """Estrutura de dados persistida pelo LangGraph para cada conversa de lead."""

    messages: list[Any]
    telefone: str
    nome_cliente: str | None
    lead_id: str | int | None
    contato_id: str | None
    chat_id: str | None
    talk_id: str | int | None
    fase: FaseLead
    humano_ativo: bool
    ficha: FichaTrabalhista
    motivo_inviabilidade: str | None
    aceitou_oferta: bool

    # Campos complementares e retrocompatibilidade
    dados_triagem: dict[str, Any]
    dados_contrato: dict[str, Any]
    zapsign_doc_token: str | None
    zapsign_sign_url: str | None
    advbox_customer_id: str | None
    advbox_lawsuit_id: str | None
    motivo_transbordo: str | None


def criar_ficha_vazia() -> FichaTrabalhista:
    """Cria e retorna uma Ficha Trabalhista vazia com todos os campos padrão."""
    return {
        "data_entrada": None,
        "data_saida": None,
        "funcao": None,
        "salario": None,
        "dias_trabalhados": None,
        "dias_folga": None,
        "horario_trabalho": None,
        "intervalo": None,
        "carteira_assinada": None,
        "data_assinatura": None,
        "insalubridade_periculosidade": None,
        "horas_extras": None,
        "comissao": None,
        "beneficios": None,
        "decimo_terceiro": None,
        "ferias": None,
        "fgts": None,
        "filhos_menores": None,
    }


def formatar_ficha_oficial(
    ficha: FichaTrabalhista | dict[str, Any] | None,
    parecer: str = "Caso viável com benefício econômico identificado.",
) -> str:
    """Gera a formatação oficial da Ficha de Qualificação Trabalhista da Dra. Lívia França."""
    f = ficha or {}

    def _val(chave: str) -> str:
        v = f.get(chave)
        if v is None or v == "":
            return "Não informado"
        return str(v)

    linhas = [
        "📋 FICHA DE QUALIFICAÇÃO TRABALHISTA — DRA. LÍVIA FRANÇA",
        "",
        f"· Data de entrada: {_val('data_entrada')}",
        f"· Data de saída: {_val('data_saida')}",
        f"· Função: {_val('funcao')}",
        f"· Salário: {_val('salario')}",
        f"· Dias trabalhados: {_val('dias_trabalhados')}",
        f"· Dias de folga: {_val('dias_folga')}",
        f"· Horário de trabalho: {_val('horario_trabalho')}",
        f"· Intervalo: {_val('intervalo')}",
        f"· Carteira assinada: {_val('carteira_assinada')}",
        f"· Data de assinatura: {_val('data_assinatura')}",
        f"· Insalubridade/periculosidade: {_val('insalubridade_periculosidade')}",
        f"· Horas extras: {_val('horas_extras')}",
        f"· Comissão: {_val('comissao')}",
        f"· Benefícios: {_val('beneficios')}",
        f"· 13º salário: {_val('decimo_terceiro')}",
        f"· Férias: {_val('ferias')}",
        f"· FGTS: {_val('fgts')}",
        f"· Filhos menores: {_val('filhos_menores')}",
        "",
        f"⚖️ PARECER DA IA: {parecer}",
    ]
    return "\n".join(linhas)

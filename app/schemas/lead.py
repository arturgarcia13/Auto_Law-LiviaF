"""Schemas de validação para dados de triagem e contrato do lead."""

from pydantic import BaseModel, EmailStr, Field


class DadosTriagemTrabalhista(BaseModel):
    """Dados coletados durante a etapa de triagem trabalhista."""

    motivo_acao: str = Field(..., description="Motivo principal da rescisão ou litígio")
    tempo_servico: str | None = Field(
        default=None, description="Tempo total de trabalho na empresa"
    )
    possui_ctps: bool | None = Field(
        default=None, description="Trabalhava com registro em carteira"
    )
    salario_mensal: str | None = Field(default=None, description="Salário mensal aproximado")
    empresa_reclamada: str | None = Field(default=None, description="Nome da empresa/empregador")
    possui_provas: bool | None = Field(
        default=None, description="Possui mensagens, contracheques ou testemunhas"
    )


class DadosContratoHonorarios(BaseModel):
    """Dados cadastrais obrigatórios para preenchimento de minuta contratual e procuração."""

    nome_completo: str = Field(..., min_length=5, description="Nome completo sem abreviações")
    cpf: str = Field(..., description="CPF válido no formato 000.000.000-00 ou numérico")
    rg: str = Field(..., description="RG com órgão emissor e UF")
    data_nascimento: str = Field(..., description="Data de nascimento no formato DD/MM/AAAA")
    estado_civil: str = Field(..., description="Solteiro(a), Casado(a), etc.")
    profissao: str = Field(..., description="Profissão ou cargo exercido")
    endereco_completo: str = Field(..., description="Logradouro, número, bairro, cidade, UF e CEP")
    email: EmailStr = Field(..., description="E-mail para formalização e notificações da ZapSign")

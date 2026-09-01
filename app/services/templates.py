"""Gerenciador de templates de mensagens em memória para o escritório da Dra. Lívia França."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Caminho padrão para o arquivo de templates
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TEMPLATES_PATH = DATA_DIR / "chat_templates.json"

# Templates padrão de fallback integrados no código
FALLBACK_TEMPLATES: dict[str, str] = {
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
}


def _normalizar_chave(chave: str) -> str:
    """Padroniza a chave sem acentos, em minúsculas e separada por sublinhados."""
    nfkd = unicodedata.normalize("NFKD", str(chave))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento.strip().lower())
    return limpo.strip("_")


class TemplateManager:
    """Gerenciador singleton de templates carregados uma única vez em memória."""

    _instance: TemplateManager | None = None
    _templates: dict[str, str] = {}
    _raw_data: dict[str, Any] = {}
    _loaded: bool = False
    _file_path: Path = DEFAULT_TEMPLATES_PATH

    def __new__(cls, file_path: Path | str | None = None) -> TemplateManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._templates = {}
            cls._instance._raw_data = {}
            cls._instance._loaded = False
        return cls._instance

    def __init__(self, file_path: Path | str | None = None) -> None:
        caminho = Path(file_path) if file_path else DEFAULT_TEMPLATES_PATH
        if not self._loaded or caminho != self._file_path:
            self.carregar_templates(caminho)

    def carregar_templates(self, file_path: Path | str | None = None) -> None:
        """Lê o arquivo JSON de templates uma única vez para a memória."""
        caminho = Path(file_path) if file_path else self._file_path
        self._file_path = caminho
        self._templates = dict(FALLBACK_TEMPLATES)
        self._raw_data = {}

        if caminho.exists():
            try:
                conteudo = caminho.read_text(encoding="utf-8")
                dados = json.loads(conteudo)
                self._raw_data = dados if isinstance(dados, dict) else {}

                # Caso 1: JSON estruturado com chave "templates"
                if (
                    isinstance(dados, dict)
                    and "templates" in dados
                    and isinstance(dados["templates"], dict)
                ):
                    for k, v in dados["templates"].items():
                        if isinstance(v, str):
                            self._templates[k] = v
                            self._templates[_normalizar_chave(k)] = v

                # Caso 2: JSON é um dicionário direto chave: valor
                elif isinstance(dados, dict):
                    for k, v in dados.items():
                        if isinstance(v, str):
                            self._templates[k] = v
                            self._templates[_normalizar_chave(k)] = v

                # Caso 3: Extrair de lista em "raw_templates" ou "_embedded"
                raw_list = []
                if isinstance(dados, dict):
                    raw_list = dados.get("raw_templates", []) or dados.get("_embedded", {}).get(
                        "chat_templates", []
                    )
                elif isinstance(dados, list):
                    raw_list = dados

                for item in raw_list:
                    if isinstance(item, dict):
                        nome = item.get("name", "")
                        content = item.get("content", "")
                        if nome and content:
                            self._templates[nome] = content
                            self._templates[_normalizar_chave(nome)] = content

                logger.info(
                    f"TemplateManager: {len(self._templates)} templates carregados de {caminho}"
                )
            except Exception as exc:
                logger.warning(
                    f"TemplateManager: Erro ao carregar {caminho}: {exc}. Usando fallbacks."
                )
        else:
            logger.info(
                f"TemplateManager: Arquivo {caminho} não encontrado. Usando fallbacks padrão."
            )

        self._loaded = True

    def get_texto(self, chave: str, fallback: str = "") -> str:
        """Recupera o texto de um template pela chave ou retorna o fallback."""
        if not self._loaded:
            self.carregar_templates()

        if not chave:
            return fallback

        chave_str = str(chave).strip()
        chave_norm = _normalizar_chave(chave_str)

        # 1. Busca direta pela chave original
        if chave_str in self._templates and self._templates[chave_str]:
            return self._templates[chave_str]

        # 2. Busca pela chave normalizada
        if chave_norm in self._templates and self._templates[chave_norm]:
            return self._templates[chave_norm]

        # 3. Busca nos templates de fallback embutidos
        if chave_norm in FALLBACK_TEMPLATES:
            return FALLBACK_TEMPLATES[chave_norm]

        # 4. Retorna fallback fornecido
        return fallback

    def get(self, chave: str, fallback: str = "") -> str:
        """Alias para get_texto."""
        return self.get_texto(chave, fallback)

    def listar_chaves(self) -> list[str]:
        """Lista todas as chaves disponíveis."""
        if not self._loaded:
            self.carregar_templates()
        return sorted(self._templates.keys())

    def __getitem__(self, chave: str) -> str:
        res = self.get_texto(chave)
        if not res:
            raise KeyError(f"Template '{chave}' não encontrado.")
        return res

    def __contains__(self, chave: str) -> bool:
        chave_str = str(chave).strip()
        chave_norm = _normalizar_chave(chave_str)
        return (
            chave_str in self._templates
            or chave_norm in self._templates
            or chave_norm in FALLBACK_TEMPLATES
        )


# Instância singleton global do TemplateManager
template_manager = TemplateManager()


def get_texto(chave: str, fallback: str = "") -> str:
    """Função utilitária para obter texto do template via singleton global."""
    return template_manager.get_texto(chave, fallback)

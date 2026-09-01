"""Gerenciador de templates de mensagens e prompts da assistente jurídica."""

from typing import Any

from agent.prompts import SYSTEM_PROMPT_COLETA, SYSTEM_PROMPT_TRIAGEM


class TemplateManager:
    """Carrega, valida e renderiza templates de mensagens e prompts do sistema."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {
            "system_triagem": SYSTEM_PROMPT_TRIAGEM,
            "system_coleta": SYSTEM_PROMPT_COLETA,
            "saudacao_padrao": (
                "Olá! Sou a assistente virtual da Dra. Lívia França, advogada "
                "especialista em Direito do Trabalho. Como posso te ajudar hoje?"
            ),
            "audio_recebido": "Recebi seu áudio! Vou processá-lo em instantes. 🎧",
            "lead_qualificado": (
                "Perfeito! Seu caso foi qualificado e nossa equipe jurídica "
                "especializada entrará em contato em breve."
            ),
            "transbordo_humano": (
                "Entendido. Estou transferindo seu atendimento para um de nossos "
                "advogados especialistas. Em breve você receberá um retorno."
            ),
            "nao_qualificado": (
                "Agradecemos o contato. No momento, pelas informações fornecidas, "
                "não identificamos viabilidade para prosseguir com uma ação trabalhista. "
                "Permanecemos à disposição!"
            ),
        }

    def get_template(self, name: str) -> str:
        """Recupera o texto bruto do template pelo nome."""
        return self._templates.get(name, "")

    def render(self, name: str, **kwargs: Any) -> str:
        """Renderiza um template substituindo variáveis informadas."""
        template = self._templates.get(name, "")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def register_template(self, name: str, content: str) -> None:
        """Registra ou sobrescreve um template customizado."""
        self._templates[name] = content

    def list_templates(self) -> list[str]:
        """Lista todos os nomes de templates registrados."""
        return list(self._templates.keys())

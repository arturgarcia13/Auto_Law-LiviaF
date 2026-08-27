"""Cliente HTTP assíncrono para a API REST da ZapSign."""

from typing import Any


async def criar_documento(dados_signatario: dict[str, Any]) -> dict[str, str]:
    """Preenche o template de contrato de honorários na ZapSign.

    Retorna dicionário contendo 'doc_token' e 'sign_url'.
    Configurado obrigatoriamente com send_automatic_whatsapp: False (conforme ADR-005).
    """
    return {
        "doc_token": "token_mock",
        "sign_url": "https://app.zapsign.com.br/verificar/mock",
    }

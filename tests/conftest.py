"""Configurações globais e fixtures compartilhadas do pytest."""

from typing import Any

import pytest


@pytest.fixture
def mock_evolution_payload() -> dict[str, Any]:
    """Payload de exemplo de mensagem recebida via Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "livia-franca",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_TEST_001",
            },
            "pushName": "João da Silva",
            "message": {
                "conversation": "Olá, vi o anúncio e fui demitido sem justa causa.",
            },
            "messageType": "conversation",
            "messageTimestamp": 1724774400,
        },
    }


@pytest.fixture
def mock_zapsign_signed_payload() -> dict[str, Any]:
    """Payload de exemplo de documento assinado na ZapSign."""
    return {
        "event": "doc_signed",
        "document": {
            "token": "doc_token_test_123",
            "name": "Contrato Honorarios - Joao da Silva",
            "status": "signed",
            "signers": [
                {
                    "token": "signer_token_abc",
                    "name": "João da Silva",
                    "status": "signed",
                }
            ],
        },
    }

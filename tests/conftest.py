"""Configurações globais e fixtures compartilhadas do pytest."""

from typing import Any

import pytest


@pytest.fixture
def mock_kommo_text_payload() -> dict[str, Any]:
    """Payload de exemplo de mensagem de texto recebida via Kommo Talks."""
    return {
        "event_type": "new_message",
        "chat_id": "chat_123456",
        "talk_id": "talk_999",
        "phone": "5511999999999",
        "sender": {
            "id": "client_001",
            "name": "João da Silva",
            "phone": "+55 (11) 99999-9999",
            "is_client": True,
        },
        "message": {
            "type": "text",
            "text": "Olá, fui demitido sem justa causa e gostaria de orientação jurídica.",
        },
    }


@pytest.fixture
def mock_kommo_audio_payload() -> dict[str, Any]:
    """Payload de exemplo de mensagem de áudio/voz recebida via Kommo Talks."""
    return {
        "event_type": "new_message",
        "chat_id": "chat_654321",
        "talk_id": "talk_888",
        "phone": "5521988887777",
        "sender": {
            "id": "client_002",
            "name": "Maria Oliveira",
            "phone": "+55 (21) 98888-7777",
            "is_client": True,
        },
        "message": {
            "type": "voice",
            "media": "https://example.com/audios/audio_teste.ogg",
            "duration": 15,
        },
    }


@pytest.fixture
def mock_kommo_outgoing_payload() -> dict[str, Any]:
    """Payload de mensagem enviada pelo próprio escritório/bot (is_client=False)."""
    return {
        "event_type": "new_message",
        "chat_id": "chat_123456",
        "sender": {
            "id": "agent_001",
            "name": "Dra. Lívia Bot",
            "is_client": False,
        },
        "message": {
            "type": "text",
            "text": "Olá! Em que posso ajudar?",
        },
    }


@pytest.fixture
def mock_kommo_leads_webhook_payload() -> dict[str, Any]:
    """Payload padrão do Kommo CRM para eventos de atualização de leads."""
    return {
        "leads": {
            "status": [
                {
                    "id": "778899",
                    "status_id": "142",
                    "pipeline_id": "5001",
                    "old_status_id": "141",
                    "name": "Lead João Silva",
                }
            ]
        }
    }


@pytest.fixture
def mock_kommo_tasks_webhook_payload() -> dict[str, Any]:
    """Payload padrão do Kommo CRM para eventos de tarefas."""
    return {
        "tasks": {
            "add": [
                {
                    "id": "112233",
                    "element_id": "778899",
                    "element_type": 2,
                    "text": "Transbordo Urgente - Contatar lead em 2h",
                }
            ]
        }
    }


@pytest.fixture
def mock_evolution_payload() -> dict[str, Any]:
    """Payload de exemplo legado de mensagem recebida via Evolution API."""
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
    """Payload de exemplo legado de documento assinado na ZapSign."""
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

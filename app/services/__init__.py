"""Serviços e utilitários auxiliares da aplicação."""

from app.services.audio import baixar_audio, transcrever_audio
from app.services.buffer import agrupar_mensagens, get_redis_client, set_redis_client
from app.services.deduplication import MessageDeduplicator, deduplicator, get_deduplicator
from app.services.template_manager import TemplateManager

__all__ = [
    "MessageDeduplicator",
    "TemplateManager",
    "agrupar_mensagens",
    "baixar_audio",
    "deduplicator",
    "get_deduplicator",
    "get_redis_client",
    "set_redis_client",
    "transcrever_audio",
]


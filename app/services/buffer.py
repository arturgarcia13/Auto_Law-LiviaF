"""Serviço de buffer em Redis para agregação de mensagens consecutivas."""

import asyncio
from typing import Any

_redis_client: Any = None


def set_redis_client(client: Any) -> None:
    """Define a instância ativa do cliente Redis."""
    global _redis_client
    _redis_client = client


def get_redis_client() -> Any:
    """Retorna o cliente Redis atualmente configurado."""
    return _redis_client


async def agrupar_mensagens(
    telefone: str,
    nova_mensagem: str,
    janela_segundos: float = 0.5,
) -> str:
    """Acumula mensagens enviadas em rajada dentro de uma janela de tempo.

    Em ambientes com Redis ativo, armazena em buffer temporário.
    Em ambientes sem Redis configurado, retorna a própria mensagem imediatamente.
    """
    if not _redis_client:
        return nova_mensagem

    key = f"buffer:msg:{telefone}"
    try:
        async with asyncio.timeout(0.8):
            await _redis_client.rpush(key, nova_mensagem)
            await _redis_client.expire(key, int(janela_segundos + 5))
            if janela_segundos > 0:
                await asyncio.sleep(janela_segundos)
            mensagens = await _redis_client.lrange(key, 0, -1)
            if mensagens:
                await _redis_client.delete(key)
                decoded = [
                    m.decode("utf-8") if isinstance(m, bytes) else str(m)
                    for m in mensagens
                ]
                return " \n ".join(decoded)
    except Exception:
        pass
    return nova_mensagem

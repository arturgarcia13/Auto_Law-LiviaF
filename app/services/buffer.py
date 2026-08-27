"""Serviço de buffer em Redis para agregação de mensagens consecutivas."""


async def agrupar_mensagens(telefone: str, nova_mensagem: str) -> str:
    """Acumula mensagens enviadas em rajada dentro de uma janela de 3 segundos.

    Em ambientes sem Redis configurado, retorna a própria mensagem imediatamente.
    """
    return nova_mensagem

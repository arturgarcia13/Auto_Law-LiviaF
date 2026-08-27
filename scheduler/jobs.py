"""Jobs periódicos para follow-up de contratos pendentes e higienização de checkpoints."""

from typing import Any


async def verificar_contratos_pendentes(graph: Any = None) -> None:
    """Verifica contratos enviados há mais de 24h e envia lembrete amigável."""
    pass


async def limpar_checkpoints_antigos(pool: Any = None) -> None:
    """Remove checkpoints de conversas inativas há mais de 30 dias."""
    pass


def registrar_jobs(scheduler: Any, graph: Any = None, pool: Any = None) -> None:
    """Registra os jobs no agendador APScheduler durante o startup da aplicação."""
    pass

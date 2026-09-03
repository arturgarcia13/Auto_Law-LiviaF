"""Testes de persistência de memória conversacional do LangGraph com AsyncSqliteSaver."""

from pathlib import Path
from unittest.mock import patch

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.graph import build_graph


@pytest.mark.asyncio
async def test_async_sqlite_saver_persiste_entre_turnos(tmp_path: Path) -> None:
    """Verifica se AsyncSqliteSaver acumula histórico de conversas entre turnos sucessivos."""
    db_file = tmp_path / "checkpoints_test.sqlite"
    thread_id = "5511999990001"
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(str(db_file)) as saver:
        graph = build_graph(checkpointer=saver)

        # Turno 1
        with patch("agent.nodes._get_gemini_client", return_value=None):
            res_1 = await graph.ainvoke(
                {
                    "telefone": thread_id,
                    "fase": "analise_viabilidade",
                    "messages": [
                        {"role": "user", "content": "Olá, trabalhei 3 anos sem carteira assinada."}
                    ],
                },
                config=config,
            )
            assert len(res_1["messages"]) >= 2

            # Turno 2
            res_2 = await graph.ainvoke(
                {
                    "telefone": thread_id,
                    "fase": "analise_viabilidade",
                    "messages": [{"role": "user", "content": "E nunca recebi férias."}],
                },
                config=config,
            )
            assert len(res_2["messages"]) >= len(res_1["messages"]) + 2


@pytest.mark.asyncio
async def test_async_sqlite_saver_persiste_apos_reabertura_banco(tmp_path: Path) -> None:
    """Verifica se o estado sobrevive a reabertura do SQLite (simulando reload do Uvicorn)."""
    db_file = tmp_path / "reload_test.sqlite"
    thread_id = "5511999990002"
    config = {"configurable": {"thread_id": thread_id}}

    # Sessão 1: Inicializa e processa turno 1
    async with AsyncSqliteSaver.from_conn_string(str(db_file)) as saver_1:
        graph_1 = build_graph(checkpointer=saver_1)
        with patch("agent.nodes._get_gemini_client", return_value=None):
            res_1 = await graph_1.ainvoke(
                {
                    "telefone": thread_id,
                    "fase": "analise_viabilidade",
                    "messages": [{"role": "user", "content": "Mensagem da primeira sessão"}],
                },
                config=config,
            )
            total_msgs_sessao_1 = len(res_1["messages"])
            assert total_msgs_sessao_1 >= 2

    # Sessão 2: Nova instância do saver apontando para o mesmo arquivo (como após Uvicorn --reload)
    async with AsyncSqliteSaver.from_conn_string(str(db_file)) as saver_2:
        graph_2 = build_graph(checkpointer=saver_2)
        with patch("agent.nodes._get_gemini_client", return_value=None):
            res_2 = await graph_2.ainvoke(
                {
                    "telefone": thread_id,
                    "fase": "analise_viabilidade",
                    "messages": [{"role": "user", "content": "Mensagem da segunda sessão"}],
                },
                config=config,
            )
            # Deve conter as mensagens da Sessão 1 + as novas mensagens da Sessão 2
            assert len(res_2["messages"]) >= total_msgs_sessao_1 + 2

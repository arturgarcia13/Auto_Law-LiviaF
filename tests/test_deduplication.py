"""Testes unitários do serviço de deduplicação e idempotência de mensagens."""

from unittest.mock import patch

from app.services.deduplication import MessageDeduplicator, get_deduplicator


def test_deduplicator_singleton() -> None:
    """Verifica que MessageDeduplicator opera como classe singleton."""
    d1 = MessageDeduplicator()
    d2 = MessageDeduplicator()
    d3 = get_deduplicator()
    assert d1 is d2
    assert d2 is d3


def test_deduplicacao_por_message_id() -> None:
    """Verifica deduplicação baseada no ID único da mensagem."""
    dedup = MessageDeduplicator()
    dedup.clear()

    # 1ª checagem: não duplicada
    assert dedup.is_duplicate(message_id="msg_100") is False
    assert dedup.check_and_mark(message_id="msg_100") is False

    # 2ª checagem: duplicada
    assert dedup.is_duplicate(message_id="msg_100") is True
    assert dedup.check_and_mark(message_id="msg_100") is True


def test_deduplicacao_por_hash_conteudo() -> None:
    """Verifica deduplicação por hash de (chat_id, texto, timestamp)."""
    dedup = MessageDeduplicator()
    dedup.clear()

    chat = "chat_abc"
    texto = "Olá, gostaria de saber sobre meus direitos."
    ts = 1725320000

    # 1ª checagem: não duplicada
    assert dedup.check_and_mark(chat_id=chat, text=texto, timestamp=ts) is False

    # 2ª checagem: duplicada com mesmos parâmetros
    assert dedup.is_duplicate(chat_id=chat, text=texto, timestamp=ts) is True

    # Parâmetros diferentes não devem ser duplicados
    assert dedup.is_duplicate(chat_id=chat, text="Outro texto", timestamp=ts) is False


def test_deduplicacao_expiracao_ttl() -> None:
    """Verifica expiração temporal baseada no TTL."""
    dedup = MessageDeduplicator(ttl_seconds=900)
    dedup.clear()

    tempo_inicial = 1000.0

    with patch("time.time", return_value=tempo_inicial):
        dedup.mark_processed(message_id="msg_ttl_1")
        assert dedup.is_duplicate(message_id="msg_ttl_1") is True

    # 10 minutos depois (600s) -> ainda dentro do TTL de 900s
    with patch("time.time", return_value=tempo_inicial + 600.0):
        assert dedup.is_duplicate(message_id="msg_ttl_1") is True

    # 16 minutos depois (960s) -> expirado
    with patch("time.time", return_value=tempo_inicial + 960.0):
        assert dedup.is_duplicate(message_id="msg_ttl_1") is False


def test_deduplicacao_clear() -> None:
    """Verifica limpeza completa de cache com clear()."""
    dedup = MessageDeduplicator()
    dedup.clear()

    dedup.mark_processed(message_id="msg_limpar")
    assert dedup.is_duplicate(message_id="msg_limpar") is True

    dedup.clear()
    assert dedup.is_duplicate(message_id="msg_limpar") is False


def test_deduplicacao_parametros_vazios() -> None:
    """Verifica comportamento defensivo com parâmetros nulos."""
    dedup = MessageDeduplicator()
    dedup.clear()

    assert dedup.is_duplicate(message_id=None, chat_id=None, text=None) is False
    assert dedup.check_and_mark(message_id=None, chat_id=None, text=None) is False


def test_deduplicacao_persistente_l2_recupera_apos_limpar_l1() -> None:
    """Verifica se chave no SQLite L2 é resgatada mesmo após o cache L1 ser esvaziado."""
    dedup = MessageDeduplicator()
    dedup.clear()

    dedup.mark_processed(message_id="msg_l2_persist")

    # Simula reinício de processo ou esvaziamento apenas da memória RAM (L1)
    dedup._cache.clear()
    assert len(dedup._cache) == 0

    # Deve consultar o SQLite L2, confirmar duplicidade e repopular L1
    assert dedup.is_duplicate(message_id="msg_l2_persist") is True
    assert "msg_id:msg_l2_persist" in dedup._cache


def test_deduplicacao_limpeza_expirados_sqlite() -> None:
    """Verifica se chaves expiradas são deletadas do SQLite L2."""
    dedup = MessageDeduplicator(ttl_seconds=100)
    dedup.clear()

    tempo_base = 2000.0

    with patch("time.time", return_value=tempo_base):
        dedup.mark_processed(message_id="msg_expira_sqlite")
        assert dedup.is_duplicate(message_id="msg_expira_sqlite") is True

    # 150 segundos depois -> expirado tanto no L1 quanto no SQLite
    with patch("time.time", return_value=tempo_base + 150.0):
        # Esvazia L1 para forçar busca no SQLite
        dedup._cache.clear()
        assert dedup.is_duplicate(message_id="msg_expira_sqlite") is False

        # Verifica que a tabela SQLite está vazia
        with dedup._lock:
            cur = dedup._conn.cursor()
            cur.execute("SELECT count(*) FROM processed_keys")
            count = cur.fetchone()[0]
            assert count == 0


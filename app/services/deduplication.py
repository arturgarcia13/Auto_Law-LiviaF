"""Serviço de deduplicação e idempotência de mensagens recebidas via CRM / Webhooks."""

import hashlib
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MessageDeduplicator:
    """Controlador de deduplicação em dois níveis (L1 em memória + L2 SQLite persistente).

    Garante que mensagens reenviadas pela Kommo (retentativas por timeout)
    ou mensagens disparadas em rajada/concorrência não sejam processadas
    duas vezes pela IA, mesmo sob reloads ou reinicializações do servidor.
    """

    _instance: "MessageDeduplicator | None" = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageDeduplicator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        ttl_seconds: int = 900,
        db_path: str | Path | None = None,
    ) -> None:
        """Inicializa deduplicador com cache L1 e storage persistente SQLite L2."""
        self.ttl_seconds = ttl_seconds
        if not hasattr(self, "_initialized"):
            self._cache: dict[str, float] = {}
            self._lock = threading.Lock()

            if db_path is not None:
                self.db_path = Path(db_path)
            else:
                project_root = Path(__file__).resolve().parents[2]
                data_dir = project_root / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = data_dir / "deduplication.sqlite"

            self._init_db()
            self._initialized = True

    def _init_db(self) -> None:
        """Inicializa a conexão com o banco SQLite e garante a tabela de chaves processadas."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
        )
        with self._lock:
            with self._conn:
                self._conn.execute("PRAGMA journal_mode=WAL;")
                self._conn.execute("PRAGMA synchronous=NORMAL;")
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS processed_keys (
                        key TEXT PRIMARY KEY,
                        expires_at REAL
                    )
                    """
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_processed_keys_expires "
                    "ON processed_keys (expires_at)"
                )

    def _cleanup_expired(self, now: float) -> None:
        """Remove entradas expiradas do cache em memória L1 e do storage SQLite L2."""
        expired_keys = [k for k, exp in self._cache.items() if exp <= now]
        for k in expired_keys:
            del self._cache[k]

        try:
            with self._lock:
                with self._conn:
                    self._conn.execute(
                        "DELETE FROM processed_keys WHERE expires_at <= ?",
                        (now,),
                    )
        except Exception as exc:
            logger.warning("Falha na limpeza de chaves expiradas no SQLite: %s", exc)

    def _gerar_chaves(
        self,
        message_id: str | int | None = None,
        chat_id: str | int | None = None,
        text: str | None = None,
        timestamp: Any = None,
    ) -> list[str]:
        """Gera as chaves únicas de rastreamento para a mensagem."""
        chaves: list[str] = []

        if message_id is not None and str(message_id).strip():
            chaves.append(f"msg_id:{str(message_id).strip()}")

        if chat_id is not None or text is not None:
            raw_chat = str(chat_id or "").strip()
            raw_text = str(text or "").strip()
            raw_ts = str(timestamp or "").strip()
            conteudo = f"{raw_chat}:{raw_text}:{raw_ts}"
            digest = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
            chaves.append(f"hash:{digest}")

        return chaves

    def is_duplicate(
        self,
        message_id: str | int | None = None,
        chat_id: str | int | None = None,
        text: str | None = None,
        timestamp: Any = None,
    ) -> bool:
        """Verifica se a mensagem já foi registrada no cache recente ou no SQLite sem expirar."""
        now = time.time()
        self._cleanup_expired(now)

        chaves = self._gerar_chaves(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
        )
        if not chaves:
            return False

        # 1. Busca no L1 (memória)
        for chave in chaves:
            exp = self._cache.get(chave)
            if exp is not None and exp > now:
                return True

        # 2. Busca no L2 (SQLite persistente)
        try:
            with self._lock:
                cursor = self._conn.cursor()
                for chave in chaves:
                    cursor.execute(
                        "SELECT expires_at FROM processed_keys WHERE key = ? AND expires_at > ?",
                        (chave, now),
                    )
                    row = cursor.fetchone()
                    if row is not None:
                        # Popula L1 para altíssima performance nas próximas consultas
                        self._cache[chave] = float(row[0])
                        return True
        except Exception as exc:
            logger.warning("Falha ao consultar duplicidade no SQLite: %s", exc)

        return False

    def mark_processed(
        self,
        message_id: str | int | None = None,
        chat_id: str | int | None = None,
        text: str | None = None,
        timestamp: Any = None,
    ) -> None:
        """Registra as chaves da mensagem no L1 e no SQLite L2 com tempo de expiração TTL."""
        now = time.time()
        self._cleanup_expired(now)

        chaves = self._gerar_chaves(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
        )
        expire_at = now + self.ttl_seconds
        for chave in chaves:
            self._cache[chave] = expire_at

        if chaves:
            try:
                with self._lock:
                    with self._conn:
                        self._conn.executemany(
                            "INSERT OR REPLACE INTO processed_keys (key, expires_at) VALUES (?, ?)",
                            [(k, expire_at) for k in chaves],
                        )
            except Exception as exc:
                logger.warning("Falha ao registrar chaves processadas no SQLite: %s", exc)

    def check_and_mark(
        self,
        message_id: str | int | None = None,
        chat_id: str | int | None = None,
        text: str | None = None,
        timestamp: Any = None,
    ) -> bool:
        """Verifica se a mensagem é duplicada.

        Retorna True se for duplicada (já vista recentemente).
        Retorna False se for nova e a registra no cache.
        """
        if self.is_duplicate(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
        ):
            return True

        self.mark_processed(
            message_id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
        )
        return False

    def clear(self) -> None:
        """Limpa tanto o L1 quanto a tabela SQLite (essencial para isolamento de testes)."""
        self._cache.clear()
        try:
            with self._lock:
                with self._conn:
                    self._conn.execute("DELETE FROM processed_keys")
        except Exception as exc:
            logger.warning("Falha ao limpar processed_keys no SQLite: %s", exc)

    def close(self) -> None:
        """Fecha conexão com banco SQLite."""
        try:
            with self._lock:
                self._conn.close()
        except Exception:
            pass


# Instância global singleton
deduplicator: MessageDeduplicator = MessageDeduplicator()


def get_deduplicator() -> MessageDeduplicator:
    """Retorna a instância singleton do MessageDeduplicator."""
    return deduplicator


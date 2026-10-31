"""Transactional local conversation history, independent of cognitive memory.

This first storage adapter uses SQLite directly. The API does not expose database
connections to the UI, so an ORM can be introduced later only if justified.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class SQLiteConversationStore:
    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as db:
            version = int(db.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError("Database schema is newer than this JARVIS runtime")
            if version == 0:
                db.execute("PRAGMA journal_mode = WAL")
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE messages (
                        position INTEGER PRIMARY KEY AUTOINCREMENT,
                        id TEXT NOT NULL UNIQUE,
                        conversation_id TEXT NOT NULL
                            REFERENCES conversations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL CHECK (
                            status IN ('completed', 'streaming', 'failed', 'interrupted')
                        ),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX idx_messages_conversation
                        ON messages(conversation_id, position);
                    PRAGMA user_version = 1;
                    COMMIT;
                """)

    def create_conversation(self, title: str = "Nova conversa") -> str:
        title = title.strip() or "Nova conversa"
        conversation_id = str(uuid4())
        timestamp = _now()
        with self._connection() as db:
            db.execute(
                "INSERT INTO conversations(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, title, timestamp, timestamp),
            )
        return conversation_id

    def list_conversations(self) -> list[dict]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "ORDER BY updated_at DESC, id DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict | None:
        with self._connection() as db:
            row = db.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_messages(self, conversation_id: str) -> list[dict]:
        if self.get_conversation(conversation_id) is None:
            raise KeyError("Unknown conversation")
        with self._connection() as db:
            rows = db.execute(
                "SELECT id, conversation_id, role, content, status, created_at, updated_at "
                "FROM messages WHERE conversation_id = ? ORDER BY position",
                (conversation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def append_user_message(self, conversation_id: str, content: str) -> str:
        if not content.strip():
            raise ValueError("Message content cannot be empty")
        return self._create_message(conversation_id, "user", content, "completed")

    def begin_assistant_message(self, conversation_id: str) -> str:
        return self._create_message(conversation_id, "assistant", "", "streaming")

    def _create_message(self, conversation_id: str, role: str, content: str, status: str) -> str:
        message_id = str(uuid4())
        timestamp = _now()
        with self._connection() as db:
            if db.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone() is None:
                raise KeyError("Unknown conversation")
            db.execute(
                "INSERT INTO messages(id, conversation_id, role, content, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, conversation_id, role, content, status, timestamp, timestamp),
            )
            db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
        return message_id

    def append_assistant_delta(self, message_id: str, delta: str) -> None:
        if not delta:
            return
        timestamp = _now()
        with self._connection() as db:
            updated = db.execute(
                "UPDATE messages SET content = content || ?, updated_at = ? "
                "WHERE id = ? AND role = 'assistant' AND status = 'streaming'",
                (delta, timestamp, message_id),
            )
            if updated.rowcount != 1:
                raise ValueError("Assistant message is not streaming")
            db.execute(
                "UPDATE conversations SET updated_at = ? "
                "WHERE id = (SELECT conversation_id FROM messages WHERE id = ?)",
                (timestamp, message_id),
            )

    def end_assistant_message(self, message_id: str, *, successful: bool) -> None:
        status = "completed" if successful else "failed"
        with self._connection() as db:
            updated = db.execute(
                "UPDATE messages SET status = ?, updated_at = ? "
                "WHERE id = ? AND role = 'assistant' AND status = 'streaming'",
                (status, _now(), message_id),
            )
            if updated.rowcount != 1:
                raise ValueError("Assistant message is not streaming")

    def interrupt_inflight_messages(self) -> int:
        """Conservatively mark previous uncompleted replies after a process restart."""
        with self._connection() as db:
            updated = db.execute(
                "UPDATE messages SET status = 'interrupted', updated_at = ? "
                "WHERE role = 'assistant' AND status = 'streaming'",
                (_now(),),
            )
            return updated.rowcount

    def completed_context(self, conversation_id: str, *, limit: int = 20) -> list[dict]:
        if limit < 1:
            raise ValueError("Context limit must be positive")
        if self.get_conversation(conversation_id) is None:
            raise KeyError("Unknown conversation")
        with self._connection() as db:
            rows = db.execute(
                "SELECT role, content FROM (SELECT role, content, position FROM messages "
                "WHERE conversation_id = ? AND status = 'completed' "
                "ORDER BY position DESC LIMIT ?) ORDER BY position",
                (conversation_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

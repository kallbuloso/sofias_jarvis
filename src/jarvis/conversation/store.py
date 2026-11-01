"""Transactional local conversation history, independent of cognitive memory.

This first storage adapter uses SQLite directly. The API does not expose database
connections to the UI, so an ORM can be introduced later only if justified.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

SCHEMA_VERSION = 5


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
                version = 1
            if version == 1:
                db.execute("""
                    CREATE TABLE cognitive_write_operations (
                        id TEXT PRIMARY KEY,
                        service_url TEXT NOT NULL,
                        payload_json TEXT,
                        status TEXT NOT NULL CHECK (
                            status IN ('prepared','in_flight','confirmed','unknown','rejected')
                        ),
                        memory_id TEXT,
                        error_code TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                db.execute("PRAGMA user_version = 2")
                version = 2
            if version == 2:
                # Keep prior Create journal records; do not change their identities.
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN operation_kind TEXT NOT NULL DEFAULT 'create'")
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN target_memory_id TEXT")
                db.execute("""
                    CREATE TABLE IF NOT EXISTS tb02_test_memories (
                        memory_id TEXT PRIMARY KEY,
                        root_memory_id TEXT NOT NULL,
                        service_url TEXT NOT NULL,
                        marker TEXT NOT NULL,
                        scope TEXT NOT NULL CHECK (scope = 'project:jarvis'),
                        memory_type TEXT NOT NULL CHECK (memory_type = 'semantic'),
                        lifecycle TEXT NOT NULL CHECK (
                            lifecycle IN ('active','superseded','forgotten')
                        ),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                db.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_tb02_mutation_pending
                    ON cognitive_write_operations(target_memory_id)
                    WHERE target_memory_id IS NOT NULL
                    AND status IN ('prepared','in_flight','unknown')
                """)
                db.execute("PRAGMA user_version = 3")
                version = 3
            if version == 3:
                # Durable consent metadata stays after operation payload scrubbing.
                # Historical rows remain NULL; never synthesize retroactive approval.
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN confirmation_ref TEXT")
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN confirmation_method TEXT")
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN confirmation_conversation_id TEXT")
                db.execute("ALTER TABLE cognitive_write_operations ADD COLUMN confirmed_by_user_at TEXT")
                db.execute("""
                    CREATE UNIQUE INDEX idx_cognitive_confirmation_ref
                    ON cognitive_write_operations(confirmation_ref)
                    WHERE confirmation_ref IS NOT NULL
                """)
                db.execute("PRAGMA user_version = 4")
                version = 4
            if version == 4:
                # Metadata only: no chunk text or user prompt is copied here.
                db.execute("""
                    CREATE TABLE message_knowledge_evidence (
                        assistant_message_id TEXT PRIMARY KEY
                            REFERENCES messages(id) ON DELETE CASCADE,
                        query_id TEXT,
                        dataset TEXT NOT NULL CHECK (dataset = 'jarvis-knowledge'),
                        retrieval_status TEXT NOT NULL CHECK (
                            retrieval_status IN (
                                'RESULTS_FOUND','NO_RESULTS','UNAVAILABLE','NOT_ATTEMPTED'
                            )
                        ),
                        references_json TEXT NOT NULL,
                        retrieved_at TEXT NOT NULL
                    )
                """)
                db.execute("PRAGMA user_version = 5")

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

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete only local transcript/evidence for the exact conversation.

        Cognitive Memory and immutable operational journal remain untouched.
        SQLite cascades message_knowledge_evidence through messages.
        """
        try:
            conversation_id = str(UUID(conversation_id))
        except (TypeError, ValueError, AttributeError):
            return False
        with self._connection() as db:
            removed = db.execute(
                "DELETE FROM conversations WHERE id=?", (conversation_id,),
            )
            return removed.rowcount == 1

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
            items = [dict(row) for row in rows]
            if items:
                evidence = db.execute(
                    "SELECT k.assistant_message_id,k.query_id,k.dataset,"
                    "k.retrieval_status,k.references_json,k.retrieved_at "
                    "FROM message_knowledge_evidence k "
                    "JOIN messages m ON m.id=k.assistant_message_id "
                    "WHERE m.conversation_id=?",
                    (conversation_id,),
                ).fetchall()
                index = {item["id"]: item for item in items}
                for item in evidence:
                    index[item["assistant_message_id"]]["knowledgeEvidence"] = {
                        "queryId": item["query_id"],
                        "dataset": item["dataset"],
                        "knowledgeStatus": item["retrieval_status"],
                        "references": json.loads(item["references_json"]),
                        "retrievedAt": item["retrieved_at"],
                    }
            return items

    def save_knowledge_evidence(self, assistant_message_id: str, *,
                                dataset: str, knowledge_status: str,
                                query_id: str | None, references: list[dict]) -> None:
        """Save bounded verified reference metadata on the exact assistant message.

        Never store chunks, quotes, arbitrary URLs or generated citations.
        The caller must supply references validated by KnowledgeAwareTextProvider.
        """
        target = str(UUID(assistant_message_id))
        if target != assistant_message_id or dataset != "jarvis-knowledge":
            raise ValueError("invalid_knowledge_target_or_dataset")
        if knowledge_status not in {
            "RESULTS_FOUND", "NO_RESULTS", "UNAVAILABLE", "NOT_ATTEMPTED"
        }:
            raise ValueError("invalid_knowledge_retrieval_status")
        if query_id is not None:
            if not isinstance(query_id, str) or str(UUID(query_id)) != query_id:
                raise ValueError("invalid_knowledge_query_id")
        if (not isinstance(references, list) or len(references) > 3
                or (knowledge_status != "RESULTS_FOUND" and references)):
            raise ValueError("invalid_knowledge_references")
        safe = []
        for reference in references:
            if not isinstance(reference, dict):
                raise ValueError("invalid_knowledge_reference")
            ids = {}
            for key in ("source_id", "document_id", "chunk_id"):
                value = reference.get(key)
                if not isinstance(value, str) or str(UUID(value)) != value:
                    raise ValueError("invalid_knowledge_reference_identity")
                ids[key] = value
            name = reference.get("source_name")
            if not isinstance(name, str) or len(name) > 200:
                raise ValueError("invalid_knowledge_source_name")
            safe.append({"source_name": name, **ids})
        with self._connection() as db:
            row = db.execute(
                "SELECT role,status FROM messages WHERE id=?", (target,),
            ).fetchone()
            if row is None or row["role"] != "assistant":
                raise ValueError("knowledge_evidence_requires_assistant_message")
            # A single turn may save evidence only once. Duplicate worker events
            # must never silently overwrite attribution for a different reply.
            db.execute(
                "INSERT INTO message_knowledge_evidence "
                "(assistant_message_id,query_id,dataset,retrieval_status,"
                "references_json,retrieved_at) VALUES (?,?,?,?,?,?)",
                (target, query_id, dataset, knowledge_status,
                 json.dumps(safe, ensure_ascii=False, separators=(",", ":")), _now()),
            )

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

    def end_assistant_message(self, message_id: str, *, successful: bool,
                              interrupted: bool = False) -> None:
        status = "interrupted" if interrupted else ("completed" if successful else "failed")
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

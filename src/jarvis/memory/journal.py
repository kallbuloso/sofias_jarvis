"""Local durable intent journal for explicit cognitive Create operations.

The journal is in JARVIS's SQLite operational DB, never in Sofias Memory.
A stale IN_FLIGHT operation is not silently retried after process restart.
Successful/rejected operations shed the original content from this journal.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from jarvis.conversation.store import SQLiteConversationStore, _now


class MemoryOperationJournal:
    def __init__(self, path: Path | str):
        self._store = SQLiteConversationStore(path)

    def prepare(self, operation_id: str, service_url: str, payload: dict) -> None:
        operation_id = str(UUID(operation_id))
        if not service_url.startswith("https://"):
            raise ValueError("invalid_service_url")
        if payload.get("idempotency_key") != operation_id:
            raise ValueError("idempotency_key_mismatch")
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        now = _now()
        with self._store._connection() as db:
            db.execute(
                "INSERT INTO cognitive_write_operations"
                "(id,service_url,payload_json,status,memory_id,error_code,created_at,updated_at)"
                " VALUES (?,?,?,'prepared',NULL,NULL,?,?)",
                (operation_id, service_url, serialized, now, now),
            )

    def claim(self, operation_id: str) -> dict:
        """Claim prepared intent exactly once; never claim UNKNOWN or IN_FLIGHT."""
        operation_id = str(UUID(operation_id))
        with self._store._connection() as db:
            row = db.execute(
                "SELECT service_url,payload_json FROM cognitive_write_operations"
                " WHERE id=? AND status='prepared'",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("operation_not_prepared")
            cursor = db.execute(
                "UPDATE cognitive_write_operations SET status='in_flight',updated_at=?"
                " WHERE id=? AND status='prepared'",
                (_now(), operation_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("operation_claim_failed")
            return {"service_url": row["service_url"], "payload": json.loads(row["payload_json"])}

    def resolve(self, operation_id: str, *, status: str, memory_id: str | None = None,
                error_code: str | None = None) -> None:
        """Only the process that claimed can resolve an IN_FLIGHT operation."""
        if status not in {"confirmed", "unknown", "rejected"}:
            raise ValueError("invalid_operation_status")
        operation_id = str(UUID(operation_id))
        if status == "confirmed":
            if memory_id is None:
                raise ValueError("missing_memory_id")
            memory_id = str(UUID(memory_id))
        else:
            if memory_id is not None:
                raise ValueError("unexpected_memory_id")
        if error_code is not None and (len(error_code) > 80 or not error_code.isupper()):
            raise ValueError("invalid_error_code")
        with self._store._connection() as db:
            cursor = db.execute(
                "UPDATE cognitive_write_operations SET"
                " status=?,memory_id=?,error_code=?,"
                " payload_json=CASE WHEN ?='unknown' THEN payload_json ELSE NULL END,"
                " updated_at=? WHERE id=? AND status='in_flight'",
                (status, memory_id, error_code, status, _now(), operation_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("operation_not_in_flight")

    def get(self, operation_id: str) -> dict | None:
        """Public status never exposes the saved content or provenance."""
        operation_id = str(UUID(operation_id))
        with self._store._connection() as db:
            row = db.execute(
                "SELECT id,status,memory_id,error_code,created_at,updated_at"
                " FROM cognitive_write_operations WHERE id=?",
                (operation_id,),
            ).fetchone()
        return dict(row) if row else None

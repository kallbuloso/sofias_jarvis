"""Local durable journal for explicit cognitive operations and TB-02 test items.

The journal is in JARVIS's SQLite operational DB, never in Sofias Memory.
A stale IN_FLIGHT operation is not silently retried after process restart.
Successful/rejected operations shed the original content from this journal.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from jarvis.conversation.store import SQLiteConversationStore, _now
from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
from jarvis.memory.connection import validate_memory_url


class MemoryOperationJournal:
    def __init__(self, path: Path | str):
        self._store = SQLiteConversationStore(path)

    def prepare(
        self, operation_id: str, service_url: str, payload: dict, *,
        kind: str = "create", target_memory_id: str | None = None,
        confirmation: PersonalMutationAuthorization | None = None,
    ) -> None:
        """Record intent before network effects; restrict test mutations and user-owned targets independently."""
        operation_id = str(UUID(operation_id))
        service_url = validate_memory_url(service_url)
        if payload.get("idempotency_key") != operation_id:
            raise ValueError("idempotency_key_mismatch")
        if kind not in {"create", "test_create", "test_supersede", "test_forget",
                        "user_supersede", "user_forget"}:
            raise ValueError("invalid_operation_kind")
        if kind in {"create", "test_create"} and target_memory_id is not None:
            raise ValueError("unexpected_target")
        if kind in {"test_supersede", "test_forget", "user_supersede", "user_forget"}:
            if target_memory_id is None:
                raise ValueError("test_target_required")
            target_memory_id = str(UUID(target_memory_id))
        if kind == "test_create" and (
            payload.get("scope") != "project:jarvis"
            or payload.get("memory_type") != "semantic"
            or payload.get("provenance", {}).get("source_ref") != f"jarvis-tb02-test:{operation_id}"
        ):
            raise ValueError("invalid_test_create")
        # Bind the consent receipt to this operation in the SAME SQLite commit.
        # Do not store raw typed text, UI token, credential, or personal content.
        confirmation_ref = None
        confirmation_method = None
        confirmation_conversation = None
        confirmed_by_user_at = None
        if kind in {"user_supersede", "user_forget"} and confirmation is None:
            raise ValueError("user_mutation_requires_typed_confirmation")
        if confirmation is not None:
            if not isinstance(confirmation, PersonalMutationAuthorization):
                raise ValueError("invalid_typed_confirmation_receipt")
            expected_action = {
                "user_supersede": "supersede", "user_forget": "forget",
                "create": "create",
            }.get(kind)
            if (expected_action is None or confirmation.action != expected_action
                    or confirmation.target_memory_id != target_memory_id
                    or confirmation.method not in {
                        "desktop_typed", "desktop_approved", "cli_typed",
                        "user_direct_intent"
                    }
                    or (confirmation.method == "user_direct_intent"
                        and (kind != "create" or confirmation.conversation_id is None
                             or confirmation.source_message_id is None))
                    or (confirmation.method != "user_direct_intent"
                        and confirmation.source_message_id is not None)
                    or (confirmation.method == "desktop_approved"
                        and confirmation.conversation_id is None)
                    or (confirmation.method == "desktop_typed"
                        and (kind == "create" or confirmation.conversation_id is None))
                    or (confirmation.method == "cli_typed"
                        and confirmation.conversation_id is not None)):
                raise ValueError("confirmation_does_not_match_operation")
            if confirmation.method == "user_direct_intent":
                # Source message's UUID is a stable, non-replayable operation
                # authority key across process restarts; never use model IDs.
                confirmation_ref = (
                    "user-message:" + str(UUID(confirmation.source_message_id))
                )
            else:
                confirmation_ref = (
                    "user-confirmation:" + str(UUID(confirmation.authorization_id))
                )
            confirmation_method = confirmation.method
            confirmation_conversation = confirmation.conversation_id
            confirmed_by_user_at = _now()
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        now = _now()
        with self._store._connection() as db:
            if confirmation is not None and confirmation.method == "user_direct_intent":
                row = db.execute(
                    "SELECT 1 FROM messages WHERE id=? AND conversation_id=? "
                    "AND role='user' AND status='completed'",
                    (confirmation.source_message_id, confirmation.conversation_id),
                ).fetchone()
                if row is None:
                    raise ValueError("direct_authorization_source_not_found")
            if kind in {"test_supersede", "test_forget"} and target_memory_id is not None:
                row = db.execute(
                    "SELECT service_url,lifecycle,marker FROM tb02_test_memories WHERE memory_id=?",
                    (target_memory_id,),
                ).fetchone()
                if not row or row["service_url"] != service_url or (
                    row["lifecycle"] not in (("active",) if kind == "test_supersede" else ("active", "superseded"))
                ):
                    raise ValueError("target_not_active_test_memory")
                if payload.get("memory_id") != target_memory_id:
                    raise ValueError("test_target_mismatch")
                if kind == "test_supersede" and payload.get("provenance", {}).get("source_ref") != row["marker"]:
                    raise ValueError("test_marker_mismatch")
            if kind in {"user_supersede", "user_forget"}:
                owned = db.execute(
                    "SELECT id FROM cognitive_write_operations "
                    "WHERE memory_id=? AND service_url=? AND status='confirmed' "
                    "AND operation_kind IN ('create','user_supersede') "
                    "ORDER BY updated_at DESC LIMIT 1",
                    (target_memory_id, service_url),
                ).fetchone()
                if owned is None:
                    raise ValueError("target_not_owned_user_memory")
                if payload.get("memory_id") != target_memory_id:
                    raise ValueError("user_target_mismatch")
                if kind == "user_supersede":
                    provenance = payload.get("provenance", {})
                    if (provenance.get("origin_kind") != "user_asserted"
                            or provenance.get("source_system") != "jarvis"
                            or provenance.get("source_ref") != f"memory-operation:{operation_id}"):
                        raise ValueError("invalid_user_supersede_provenance")
                elif set(payload) != {"idempotency_key", "memory_id"}:
                    raise ValueError("invalid_user_forget_payload")
            db.execute(
                "INSERT INTO cognitive_write_operations "
                "(id,service_url,payload_json,status,memory_id,error_code,created_at,updated_at,"
                "operation_kind,target_memory_id,confirmation_ref,confirmation_method,"
                "confirmation_conversation_id,confirmed_by_user_at)"
                " VALUES (?,?,?,'prepared',NULL,NULL,?,?,?,?,?,?,?,?)",
                (operation_id, service_url, serialized, now, now, kind, target_memory_id,
                 confirmation_ref, confirmation_method, confirmation_conversation,
                 confirmed_by_user_at),
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
                "SELECT id,status,memory_id,error_code,created_at,updated_at,"
                "confirmation_ref,confirmation_method,confirmation_conversation_id,"
                "confirmed_by_user_at"
                " FROM cognitive_write_operations WHERE id=?",
                (operation_id,),
            ).fetchone()
        return dict(row) if row else None


    def owned_user_memory(self, memory_id: str, service_url: str) -> dict | None:
        """Owner proof: confirmed personal Create/Supersede in this installation.

        Test memories and foreign memories are intentionally ineligible.
        """
        memory_id = str(UUID(memory_id))
        service_url = validate_memory_url(service_url)
        with self._store._connection() as db:
            row = db.execute(
                "SELECT id, memory_id, service_url, operation_kind FROM cognitive_write_operations "
                "WHERE memory_id=? AND service_url=? AND status='confirmed' "
                "AND operation_kind IN ('create','user_supersede') "
                "ORDER BY updated_at DESC LIMIT 1",
                (memory_id, service_url),
            ).fetchone()
            return dict(row) if row else None

    def has_unresolved_mutation(self, memory_id: str) -> bool:
        return self.has_unresolved_test_mutation(memory_id)

    def test_item(self, memory_id: str) -> dict | None:
        memory_id = str(UUID(memory_id))
        with self._store._connection() as db:
            row = db.execute(
                "SELECT memory_id,root_memory_id,service_url,marker,scope,memory_type,lifecycle"
                " FROM tb02_test_memories WHERE memory_id=?",
                (memory_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_test_items(self) -> list[dict]:
        with self._store._connection() as db:
            rows = db.execute(
                "SELECT memory_id,root_memory_id,service_url,scope,memory_type,lifecycle"
                " FROM tb02_test_memories ORDER BY created_at, memory_id",
            ).fetchall()
            return [dict(row) for row in rows]

    def has_unresolved_test_mutation(self, memory_id: str) -> bool:
        memory_id = str(UUID(memory_id))
        with self._store._connection() as db:
            return db.execute(
                "SELECT 1 FROM cognitive_write_operations "
                "WHERE target_memory_id=? AND status IN ('prepared','in_flight','unknown')",
                (memory_id,),
            ).fetchone() is not None

    @staticmethod
    def _finish_confirmed(db, operation_id: str, memory_id: str, kind: str):
        operation_id = str(UUID(operation_id))
        memory_id = str(UUID(memory_id))
        row = db.execute(
            "SELECT operation_kind,status,service_url,payload_json,target_memory_id"
            " FROM cognitive_write_operations WHERE id=?",
            (operation_id,),
        ).fetchone()
        if row is None or row["status"] != "in_flight" or row["operation_kind"] != kind:
            raise ValueError("test_operation_not_in_flight")
        return row

    def confirm_test_create(self, operation_id: str, memory_id: str) -> None:
        memory_id = str(UUID(memory_id))
        with self._store._connection() as db:
            row = self._finish_confirmed(db, operation_id, memory_id, "test_create")
            payload = json.loads(row["payload_json"])
            marker = f"jarvis-tb02-test:{operation_id}"
            if payload["provenance"]["source_ref"] != marker:
                raise ValueError("invalid_test_marker")
            now = _now()
            db.execute(
                "INSERT INTO tb02_test_memories "
                "(memory_id,root_memory_id,service_url,marker,scope,memory_type,"
                "lifecycle,created_at,updated_at)"
                " VALUES (?,?,?,?,?,?,'active',?,?)",
                (memory_id,memory_id,row["service_url"],marker,"project:jarvis","semantic",now,now),
            )
            db.execute(
                "UPDATE cognitive_write_operations SET status='confirmed',memory_id=?,"
                " payload_json=NULL,updated_at=? WHERE id=? AND status='in_flight'",
                (memory_id,now,str(UUID(operation_id))),
            )

    def confirm_test_supersede(
        self, operation_id: str, old_memory_id: str, replacement_memory_id: str,
    ) -> None:
        old_memory_id = str(UUID(old_memory_id))
        replacement_memory_id = str(UUID(replacement_memory_id))
        if old_memory_id == replacement_memory_id:
            raise ValueError("invalid_replacement_identity")
        with self._store._connection() as db:
            row = self._finish_confirmed(
                db, operation_id, replacement_memory_id, "test_supersede"
            )
            if row["target_memory_id"] != old_memory_id:
                raise ValueError("test_target_mismatch")
            old = db.execute(
                "SELECT * FROM tb02_test_memories WHERE memory_id=? AND lifecycle='active'",
                (old_memory_id,),
            ).fetchone()
            if old is None or old["service_url"] != row["service_url"]:
                raise ValueError("test_target_no_longer_active")
            now = _now()
            db.execute(
                "INSERT INTO tb02_test_memories "
                "(memory_id,root_memory_id,service_url,marker,scope,memory_type,"
                "lifecycle,created_at,updated_at)"
                " VALUES (?,?,?,?,?,?,'active',?,?)",
                (replacement_memory_id,old["root_memory_id"],old["service_url"],
                 old["marker"],old["scope"],old["memory_type"],now,now),
            )
            db.execute(
                "UPDATE tb02_test_memories SET lifecycle='superseded',updated_at=? "
                "WHERE memory_id=? AND lifecycle='active'",
                (now,old_memory_id),
            )
            db.execute(
                "UPDATE cognitive_write_operations SET status='confirmed',memory_id=?,"
                " payload_json=NULL,updated_at=? WHERE id=? AND status='in_flight'",
                (replacement_memory_id,now,str(UUID(operation_id))),
            )

    def confirm_test_forget(self, operation_id: str, memory_id: str) -> None:
        memory_id = str(UUID(memory_id))
        with self._store._connection() as db:
            row = self._finish_confirmed(db, operation_id, memory_id, "test_forget")
            if row["target_memory_id"] != memory_id:
                raise ValueError("test_target_mismatch")
            now = _now()
            updated = db.execute(
                "UPDATE tb02_test_memories SET lifecycle='forgotten',updated_at=? "
                "WHERE memory_id=? AND lifecycle IN ('active','superseded') AND service_url=?",
                (now,memory_id,row["service_url"]),
            )
            if updated.rowcount != 1:
                raise ValueError("test_target_no_longer_active")
            db.execute(
                "UPDATE cognitive_write_operations SET status='confirmed',memory_id=?,"
                " payload_json=NULL,updated_at=? WHERE id=? AND status='in_flight'",
                (memory_id,now,str(UUID(operation_id))),
            )

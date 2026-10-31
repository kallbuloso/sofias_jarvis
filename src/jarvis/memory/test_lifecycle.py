"""Strictly isolated TB-02 disposable Cognitive Memory lifecycle smoke.

NEVER pass a general user's memory ID to a mutation. A target must be:
(1) in this installation's durable local test allowlist;
(2) from the identical configured HTTPS service;
(3) carrying this test's exact provenance marker; and
(4) matching its fixed harmless test text, type and project scope.
All three mutations require a CLI confirmation BEFORE this module is invoked.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError
from jarvis.memory.connection import validate_memory_url
from jarvis.memory.journal import MemoryOperationJournal

TEST_SCOPE = "project:jarvis"
TEST_TYPE = "semantic"
TEST_A = "JARVIS TB-02 TESTE DESCARTAVEL: valor de laboratorio = A."
TEST_B = "JARVIS TB-02 TESTE DESCARTAVEL: valor de laboratorio = B."
TEST_PREFIX = "JARVIS TB-02 TESTE DESCARTAVEL:"
_MARKER_PREFIX = "jarvis-tb02-test:"


class TestMemoryLab:
    """All effects are explicit. This is not a general memory mutation API."""

    __test__ = False

    def __init__(
        self, client: CognitiveMemoryClient,
        journal: MemoryOperationJournal,
        service_url: str,
    ):
        self.client = client
        self.journal = journal
        self.service_url = validate_memory_url(service_url)
        if client.base_url != self.service_url:
            raise ValueError("test_service_mismatch")

    def preview(self, memory_id: str, *, action: str) -> dict:
        """Get + strict local and remote checks, with no mutation."""
        memory_id = str(UUID(memory_id))
        if action not in {"supersede", "forget"}:
            raise ValueError("invalid_test_action")
        row = self.journal.test_item(memory_id)
        if row is None or row["service_url"] != self.service_url:
            raise ValueError("NOT_REGISTERED_TEST_MEMORY")
        if row["scope"] != TEST_SCOPE or row["memory_type"] != TEST_TYPE:
            raise ValueError("INVALID_TEST_REGISTRY")
        allowed = ("active",) if action == "supersede" else ("active", "superseded")
        if row["lifecycle"] not in allowed:
            raise ValueError("TEST_MEMORY_NOT_ELIGIBLE")
        if self.journal.has_unresolved_test_mutation(memory_id):
            raise ValueError("TEST_MUTATION_UNRESOLVED")

        # Never assume local DB alone establishes the remote item identity.
        remote = self.client.get(memory_id)
        provenance = remote.get("provenance")
        marker = row["marker"]
        if (not isinstance(marker, str)
                or not marker.startswith(_MARKER_PREFIX)
                or not isinstance(provenance, dict)
                or provenance.get("source_system") != "jarvis"
                or provenance.get("origin_kind") != "assistant_generated"
                or provenance.get("source_ref") != marker
                or remote.get("scope") != TEST_SCOPE
                or remote.get("memory_type") != TEST_TYPE
                or remote.get("lifecycle") != row["lifecycle"]
                or remote.get("content") not in (TEST_A, TEST_B)):
            raise ValueError("REMOTE_TEST_IDENTITY_MISMATCH")
        if action == "supersede" and remote["content"] != TEST_A:
            raise ValueError("TEST_ALREADY_SUPERSEDED")
        return {
            "memory_id": memory_id, "scope": TEST_SCOPE,
            "lifecycle": remote["lifecycle"], "content": remote["content"],
            "marker": marker,
        }

    def _run(self, op_id: str, command, confirm) -> dict:
        """Exactly one network mutation; no retries even after transport loss."""
        self.journal.claim(op_id)
        try:
            response = command()
            return confirm(response)
        except CognitiveMemoryError as exc:
            state = "unknown" if exc.code == "RESULT_UNKNOWN" else "rejected"
            self.journal.resolve(op_id, status=state, error_code=exc.code)
            return {
                "status": "RESULT_UNKNOWN" if state == "unknown" else exc.code,
                "operation_id": op_id, "retry_automatically": False,
            }
        except Exception:
            # A successful server commit with a bad acknowledgement or a
            # local journal failure must NEVER be treated as a safe retry.
            try:
                self.journal.resolve(op_id, status="unknown", error_code="LOCAL_ERROR")
            except Exception:
                pass
            return {"status": "RESULT_UNKNOWN", "operation_id": op_id,
                    "retry_automatically": False}

    @staticmethod
    def _assert_item(item: dict, *, content: str, marker: str, state: str) -> str:
        if (not isinstance(item, dict)
                or item.get("scope") != TEST_SCOPE
                or item.get("memory_type") != TEST_TYPE
                or item.get("content") != content
                or item.get("lifecycle") != state
                or not isinstance(item.get("provenance"), dict)
                or item["provenance"].get("source_ref") != marker
                or item["provenance"].get("source_system") != "jarvis"
                or item["provenance"].get("origin_kind") != "assistant_generated"):
            raise ValueError("unexpected_test_acknowledgement")
        return str(UUID(item["memory_id"]))

    def create(self) -> dict:
        op_id = str(uuid4())
        marker = f"{_MARKER_PREFIX}{op_id}"
        provenance = {
            "origin_kind": "assistant_generated",
            "source_system": "jarvis",
            "source_ref": marker,
        }
        self.journal.prepare(
            op_id, self.service_url,
            {"idempotency_key": op_id, "memory_type": TEST_TYPE,
             "scope": TEST_SCOPE, "content": TEST_A, "provenance": provenance},
            kind="test_create",
        )

        def confirm(item):
            new_id = self._assert_item(item, content=TEST_A, marker=marker, state="active")
            self.journal.confirm_test_create(op_id, new_id)
            return {"status": "CONFIRMED", "operation_id": op_id,
                    "memory_id": new_id, "scope": TEST_SCOPE, "lifecycle": "active"}

        return self._run(op_id, lambda: self.client.create(
            memory_type=TEST_TYPE, scope=TEST_SCOPE, content=TEST_A,
            provenance=provenance, idempotency_key=op_id,
        ), confirm)

    def supersede(self, memory_id: str) -> dict:
        target = self.preview(memory_id, action="supersede")
        memory_id = target["memory_id"]
        op_id = str(uuid4())
        provenance = {"origin_kind": "assistant_generated",
                      "source_system": "jarvis", "source_ref": target["marker"]}
        self.journal.prepare(
            op_id, self.service_url,
            {"idempotency_key": op_id, "memory_id": memory_id,
             "content": TEST_B, "provenance": provenance},
            kind="test_supersede", target_memory_id=memory_id,
        )

        def confirm(data):
            old = data["old"]
            new = data["replacement"]
            old_id = self._assert_item(old, content=TEST_A, marker=target["marker"],
                                       state="superseded")
            new_id = self._assert_item(new, content=TEST_B, marker=target["marker"],
                                       state="active")
            if old_id != memory_id or old["superseded_by"] != new_id:
                raise ValueError("unexpected_test_lineage")
            self.journal.confirm_test_supersede(op_id, old_id, new_id)
            return {"status": "CONFIRMED", "operation_id": op_id,
                    "old_memory_id": old_id, "replacement_memory_id": new_id}

        return self._run(op_id, lambda: self.client.supersede(
            memory_id, content=TEST_B, provenance=provenance, idempotency_key=op_id,
        ), confirm)

    def forget(self, memory_id: str) -> dict:
        target = self.preview(memory_id, action="forget")
        memory_id = target["memory_id"]
        op_id = str(uuid4())
        self.journal.prepare(
            op_id, self.service_url,
            {"idempotency_key": op_id, "memory_id": memory_id},
            kind="test_forget", target_memory_id=memory_id,
        )

        def confirm(item):
            if (item.get("memory_id") != memory_id
                    or item.get("lifecycle") != "forgotten"
                    or item.get("scope") is not None
                    or item.get("content") is not None):
                raise ValueError("test_forget_not_confirmed")
            self.journal.confirm_test_forget(op_id, memory_id)
            return {"status": "CONFIRMED", "operation_id": op_id,
                    "memory_id": memory_id, "lifecycle": "forgotten"}

        return self._run(op_id, lambda: self.client.forget(
            memory_id, idempotency_key=op_id,
        ), confirm)

"""Disposable TB-02 memory lifecycle with fake service: no VPS writes."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.memory.cognitive import CognitiveMemoryError
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.test_lifecycle import (
    TEST_A, TEST_B, TEST_SCOPE, TEST_TYPE, TestMemoryLab,
)

URL = "https://memory.example"
TEAL_MEMORY = "ab89ac04-7134-49c6-9fa2-2880a296d50a"


class FakeCognitiveClient:
    base_url = URL

    def __init__(self):
        self.items = {}
        self.calls = []
        self.fail = None

    def _fail(self):
        if self.fail is not None:
            raise CognitiveMemoryError(self.fail)

    def get(self, memory_id):
        self.calls.append(("get", memory_id))
        if memory_id not in self.items:
            raise CognitiveMemoryError("MEMORY_NOT_FOUND")
        return dict(self.items[memory_id])

    def create(self, *, memory_type, scope, content, provenance, idempotency_key):
        self.calls.append(("create", idempotency_key))
        self._fail()
        memory_id = str(uuid4())
        item = {"memory_id": memory_id, "memory_type": memory_type, "scope": scope,
                "content": content, "lifecycle": "active", "superseded_by": None,
                "provenance": dict(provenance)}
        self.items[memory_id] = item
        return dict(item)

    def supersede(self, memory_id, *, content, provenance, idempotency_key):
        self.calls.append(("supersede", memory_id))
        self._fail()
        old = self.items[memory_id]
        if old["lifecycle"] != "active":
            raise CognitiveMemoryError("MEMORY_STATE_CONFLICT")
        replacement_id = str(uuid4())
        old["lifecycle"] = "superseded"
        old["superseded_by"] = replacement_id
        replacement = {"memory_id": replacement_id, "memory_type": old["memory_type"],
                       "scope": old["scope"], "content": content, "lifecycle": "active",
                       "provenance": dict(provenance), "superseded_by": None}
        self.items[replacement_id] = replacement
        return {"old": dict(old), "replacement": dict(replacement)}

    def forget(self, memory_id, *, idempotency_key):
        self.calls.append(("forget", memory_id))
        self._fail()
        item = self.items[memory_id]
        item.update(lifecycle="forgotten", scope=None, content=None)
        item["provenance"] = {"origin_kind": "assistant_generated", "source_system": "jarvis",
                              "source_ref": None}
        return dict(item)


@pytest.fixture
def lab(tmp_path):
    path = tmp_path / "state.sqlite3"
    return TestMemoryLab(FakeCognitiveClient(), MemoryOperationJournal(path), URL)


def test_disposable_memory_full_lineage_and_cleanup(lab):
    created = lab.create()
    assert created["status"] == "CONFIRMED"
    root_id = created["memory_id"]
    assert root_id != TEAL_MEMORY
    assert lab.preview(root_id, action="supersede")["content"] == TEST_A

    replaced = lab.supersede(root_id)
    assert replaced["status"] == "CONFIRMED"
    new_id = replaced["replacement_memory_id"]
    assert new_id != root_id
    assert lab.journal.test_item(root_id)["lifecycle"] == "superseded"
    assert lab.journal.test_item(new_id)["lifecycle"] == "active"
    assert lab.preview(new_id, action="forget")["content"] == TEST_B
    with pytest.raises(ValueError, match="TEST_MEMORY_NOT_ELIGIBLE"):
        lab.preview(root_id, action="supersede")

    forgotten_new = lab.forget(new_id)
    assert forgotten_new["status"] == "CONFIRMED"
    assert lab.journal.test_item(new_id)["lifecycle"] == "forgotten"
    assert lab.client.get(new_id)["content"] is None

    forgotten_old = lab.forget(root_id)
    assert forgotten_old["status"] == "CONFIRMED"
    assert lab.journal.test_item(root_id)["lifecycle"] == "forgotten"
    with pytest.raises(ValueError, match="TEST_MEMORY_NOT_ELIGIBLE"):
        lab.preview(new_id, action="forget")
    records = lab.journal.list_test_items()
    assert len(records) == 2 and all(i["lifecycle"] == "forgotten" for i in records)


@pytest.mark.parametrize("action", ["supersede", "forget"])
def test_teal_memory_never_eligible_even_if_remote_record_exists(lab, action):
    lab.client.items[TEAL_MEMORY] = {
        "memory_id": TEAL_MEMORY, "memory_type": "profile", "scope": "global",
        "content": "Para interfaces gráficas, prefiro a cor teal.", "lifecycle": "active",
        "provenance": {"source_system": "jarvis", "origin_kind": "user_asserted",
                       "source_ref": "memory-operation:any"},
    }
    with pytest.raises(ValueError, match="NOT_REGISTERED_TEST_MEMORY"):
        lab.preview(TEAL_MEMORY, action=action)
    assert lab.client.calls == []


def test_remote_marker_changed_blocks_mutation(lab):
    root = lab.create()["memory_id"]
    lab.client.items[root]["provenance"]["source_ref"] = "different"
    before = len(lab.client.calls)
    with pytest.raises(ValueError, match="REMOTE_TEST_IDENTITY_MISMATCH"):
        lab.supersede(root)
    assert not any(op[0] == "supersede" for op in lab.client.calls[before:])


def test_different_memory_service_blocks_local_allowlist(tmp_path, lab):
    root = lab.create()["memory_id"]
    other = FakeCognitiveClient()
    other.base_url = "https://another.example"
    check = TestMemoryLab(other, MemoryOperationJournal(tmp_path / "state.sqlite3"),
                          "https://another.example")
    with pytest.raises(ValueError, match="NOT_REGISTERED_TEST_MEMORY"):
        check.preview(root, action="forget")


def test_server_failure_is_unknown_and_blocks_new_mutations(lab):
    root = lab.create()["memory_id"]
    lab.client.fail = "RESULT_UNKNOWN"
    result = lab.supersede(root)
    assert result["status"] == "RESULT_UNKNOWN"
    assert result["retry_automatically"] is False
    op = lab.journal.get(result["operation_id"])
    assert op["status"] == "unknown"
    with pytest.raises(ValueError, match="TEST_MUTATION_UNRESOLVED"):
        lab.supersede(root)
    assert len([c for c in lab.client.calls if c[0] == "supersede"]) == 1


def test_definitive_rejection_can_be_manually_reexamined(lab):
    root = lab.create()["memory_id"]
    lab.client.fail = "MEMORY_STATE_CONFLICT"
    result = lab.supersede(root)
    assert result["status"] == "MEMORY_STATE_CONFLICT"
    assert lab.journal.get(result["operation_id"])["status"] == "rejected"
    lab.client.fail = None
    assert lab.supersede(root)["status"] == "CONFIRMED"


def test_local_reopen_preserves_lineage_and_conflicts(tmp_path, lab):
    created = lab.create()
    root = created["memory_id"]
    new = lab.supersede(root)["replacement_memory_id"]
    reopened = MemoryOperationJournal(tmp_path / "state.sqlite3")
    assert reopened.test_item(root)["lifecycle"] == "superseded"
    assert reopened.test_item(new)["lifecycle"] == "active"
    with sqlite3.connect(tmp_path / "state.sqlite3") as db:
        # This is a current database reopened, not a historical v3 fixture.
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4


def test_existing_non_test_create_journal_does_not_become_test_allowlist(tmp_path):
    path = tmp_path / "state.sqlite3"
    journal = MemoryOperationJournal(path)
    op = str(uuid4())
    journal.prepare(op, URL, {"idempotency_key": op, "content": "real user preference"})
    journal.claim(op)
    journal.resolve(op, status="confirmed", memory_id=TEAL_MEMORY)
    assert journal.test_item(TEAL_MEMORY) is None
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT operation_kind,target_memory_id FROM cognitive_write_operations WHERE id=?",
            (op,),
        ).fetchone() == ("create", None)

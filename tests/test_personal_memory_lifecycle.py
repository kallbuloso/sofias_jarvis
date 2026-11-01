"""B-01 supervised user-memory lifecycle; fake service, no live mutations."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from jarvis.memory.cognitive import CognitiveMemoryError
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

URL = "https://memory.example"


class FakeClient:
    base_url = URL

    def __init__(self):
        self.memories = {}
        self.calls = []
        self.failure = None

    def get(self, memory_id):
        self.calls.append(("get", memory_id))
        return dict(self.memories[memory_id])

    def supersede(self, memory_id, *, content, provenance, idempotency_key):
        self.calls.append(("supersede", memory_id, idempotency_key))
        if self.failure:
            raise CognitiveMemoryError(self.failure)
        old = self.memories[memory_id]
        new_id = str(uuid4())
        old.update(lifecycle="superseded", superseded_by=new_id)
        replacement = {
            "memory_id": new_id, "memory_type": old["memory_type"],
            "scope": old["scope"], "content": content,
            "lifecycle": "active", "provenance": dict(provenance),
        }
        self.memories[new_id] = replacement
        return {"old": dict(old), "replacement": dict(replacement)}

    def forget(self, memory_id, *, idempotency_key):
        self.calls.append(("forget", memory_id, idempotency_key))
        if self.failure:
            raise CognitiveMemoryError(self.failure)
        item = self.memories[memory_id]
        item.update(content=None, scope=None, lifecycle="forgotten")
        return dict(item)



def typed(action: str, target: str):
    phrase = ("SUBSTITUIR " if action == "supersede" else "ESQUECER ") + target
    return PersonalMutationAuthorization.from_typed_confirmation(
        action=action, target_memory_id=target, phrase=phrase, method="cli_typed",
    )

def owned(journal, client, *, origin="user_asserted", url=URL):
    op = str(uuid4())
    memory_id = str(uuid4())
    payload = {
        "idempotency_key": op, "content": "Prefiro teal",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": f"memory-operation:{op}"},
        "scope": "global", "memory_type": "profile",
    }
    journal.prepare(op, url, payload)
    journal.claim(op)
    journal.resolve(op, status="confirmed", memory_id=memory_id)
    client.memories[memory_id] = {
        "memory_id": memory_id, "memory_type": "profile", "scope": "global",
        "content": "Prefiro teal", "lifecycle": "active",
        "provenance": {"origin_kind": origin, "source_system": "jarvis",
                       "source_ref": f"memory-operation:{op}"},
    }
    return memory_id


@pytest.fixture
def lifecycle(tmp_path):
    client = FakeClient()
    journal = MemoryOperationJournal(tmp_path / "jarvis.sqlite3")
    return PersonalMemoryLifecycle(client, journal, URL)


def test_preview_read_only_and_owned_target(lifecycle):
    memory_id = owned(lifecycle.journal, lifecycle.client)
    result = lifecycle.preview(memory_id, action="forget")
    assert result["scope"] == "global" and result["content"] == "Prefiro teal"
    assert all(call[0] == "get" for call in lifecycle.client.calls)


def test_supersede_then_forget_exact_selected_uuids(lifecycle):
    first_id = owned(lifecycle.journal, lifecycle.client)
    preview = lifecycle.preview(first_id, action="supersede")
    result = lifecycle.supersede(preview, new_content="Prefiro azul",
                                 confirmation=typed("supersede", first_id))
    assert result["status"] == "CONFIRMED"
    second_id = result["replacement_memory_id"]
    assert second_id != first_id
    assert lifecycle.journal.owned_user_memory(second_id, URL)
    assert lifecycle.client.memories[first_id]["lifecycle"] == "superseded"
    assert lifecycle.client.memories[second_id]["content"] == "Prefiro azul"
    deletion = lifecycle.forget(lifecycle.preview(second_id, action="forget"),
                                confirmation=typed("forget", second_id))
    assert deletion["status"] == "CONFIRMED"
    assert lifecycle.client.memories[second_id]["content"] is None
    assert lifecycle.client.memories[first_id]["content"] == "Prefiro teal"
    with pytest.raises(ValueError, match="identity_or_state"):
        lifecycle.preview(second_id, action="forget")


def test_user_mutations_require_local_confirmed_record_and_matching_service(lifecycle, tmp_path):
    arbitrary = str(uuid4())
    lifecycle.client.memories[arbitrary] = {
        "memory_id": arbitrary, "scope": "global", "memory_type": "profile",
        "content": "Do not change me", "lifecycle": "active",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": "memory-operation:foreign"},
    }
    with pytest.raises(ValueError, match="not_owned"):
        lifecycle.preview(arbitrary, action="forget")
    assert lifecycle.client.calls == []
    own = owned(lifecycle.journal, lifecycle.client, url="https://other.example")
    with pytest.raises(ValueError, match="not_owned"):
        lifecycle.preview(own, action="forget")
    assert not any(call[0] == "forget" for call in lifecycle.client.calls)


def test_spoofed_remote_provenance_blocks_before_mutation(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    lifecycle.client.memories[target]["provenance"]["source_ref"] = "memory-operation:spoofed"
    with pytest.raises(ValueError, match="identity_or_state"):
        lifecycle.preview(target, action="supersede")
    assert all(call[0] == "get" for call in lifecycle.client.calls)


def test_remote_state_change_after_confirmation_blocks_mutation(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    preview = lifecycle.preview(target, action="forget")
    lifecycle.client.memories[target]["content"] = "External change"
    with pytest.raises(ValueError, match="memory_changed"):
        lifecycle.forget(preview, confirmation=typed("forget", target))
    assert not any(call[0] == "forget" for call in lifecycle.client.calls)


def test_unknown_result_is_journalled_and_not_replayed(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    preview = lifecycle.preview(target, action="supersede")
    lifecycle.client.failure = "RESULT_UNKNOWN"
    result = lifecycle.supersede(preview, new_content="Cor azul",
                                 confirmation=typed("supersede", target))
    assert result["status"] == "RESULT_UNKNOWN" and result["retry_automatically"] is False
    assert lifecycle.journal.get(result["operation_id"])["status"] == "unknown"
    with pytest.raises(ValueError, match="unresolved"):
        lifecycle.preview(target, action="supersede")
    assert sum(call[0] == "supersede" for call in lifecycle.client.calls) == 1


def test_rejection_clears_payload_and_does_not_mark_unknown(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    lifecycle.client.failure = "MEMORY_STATE_CONFLICT"
    result = lifecycle.forget(lifecycle.preview(target, action="forget"),
                              confirmation=typed("forget", target))
    assert result["status"] == "MEMORY_STATE_CONFLICT"
    with sqlite3.connect(lifecycle.journal._store.path) as db:
        row = db.execute(
            "SELECT status,payload_json FROM cognitive_write_operations WHERE id=?",
            (result["operation_id"],),
        ).fetchone()
    assert row == ("rejected", None)


def test_secret_like_replacement_rejected_without_mutation(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    with pytest.raises(ValueError, match="sensitive"):
        lifecycle.supersede(lifecycle.preview(target, action="supersede"),
                            new_content="Minha senha: 123456789",
                            confirmation=typed("supersede", target))
    assert not any(call[0] == "supersede" for call in lifecycle.client.calls)


def test_test_memories_never_become_user_memories(lifecycle):
    fake_id = str(uuid4())
    op = str(uuid4())
    lifecycle.journal.prepare(
        op, URL,
        {"idempotency_key": op, "scope": "project:jarvis",
         "memory_type": "semantic", "content": "TEST",
         "provenance": {"origin_kind": "assistant_generated",
                        "source_system": "jarvis",
                        "source_ref": f"jarvis-tb02-test:{op}"}},
        kind="test_create",
    )
    lifecycle.journal.claim(op)
    lifecycle.journal.confirm_test_create(op, fake_id)
    with pytest.raises(ValueError, match="not_owned"):
        lifecycle.preview(fake_id, action="forget")


def test_mutations_refuse_missing_or_wrong_confirmation(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    preview = lifecycle.preview(target, action="forget")
    with pytest.raises(TypeError):
        lifecycle.forget(preview)
    wrong = typed("supersede", target)
    with pytest.raises(ValueError, match="mismatched_human_confirmation"):
        lifecycle.forget(preview, confirmation=wrong)
    assert not any(call[0] == "forget" for call in lifecycle.client.calls)


def test_confirmation_survives_payload_scrubbing_and_restart(lifecycle):
    target = owned(lifecycle.journal, lifecycle.client)
    authorization = typed("forget", target)
    result = lifecycle.forget(lifecycle.preview(target, action="forget"),
                              confirmation=authorization)
    assert result["status"] == "CONFIRMED"
    from pathlib import Path
    journal = MemoryOperationJournal(lifecycle.journal._store.path)
    record = journal.get(result["operation_id"])
    assert record["status"] == "confirmed"
    assert record["confirmation_ref"] == "user-confirmation:" + authorization.authorization_id
    assert record["confirmation_method"] == "cli_typed"
    assert record["confirmed_by_user_at"] is not None
    assert record["confirmation_conversation_id"] is None
    with sqlite3.connect(journal._store.path) as db:
        body = db.execute("SELECT payload_json FROM cognitive_write_operations WHERE id=?",
                          (result["operation_id"],)).fetchone()
    assert body[0] is None

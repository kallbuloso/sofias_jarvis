"""B-01 supervised user-memory lifecycle; fake service, no live mutations."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from jarvis.memory.cognitive import CognitiveMemoryError
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.personal_confirmation import PersonalMutationAuthorization, PersonalCreateGate
from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

URL = "https://memory.example"


class FakeClient:
    base_url = URL

    def __init__(self):
        self.memories = {}
        self.calls = []
        self.failure = None

    def create(self, *, memory_type, scope, content, provenance, idempotency_key):
        self.calls.append(("create", scope, idempotency_key))
        if self.failure:
            raise CognitiveMemoryError(self.failure)
        memory_id = str(uuid4())
        memory = {
            "memory_id": memory_id, "memory_type": memory_type,
            "scope": scope, "content": content,
            "lifecycle": "active", "provenance": dict(provenance),
        }
        self.memories[memory_id] = memory
        return dict(memory)

    def get(self, memory_id):
        self.calls.append(("get", memory_id))
        return dict(self.memories[memory_id])

    def recall(self, *, query, scopes, top_k=10, include_superseded=False):
        self.calls.append(("recall", query, tuple(scopes)))
        hits = []
        for memory in self.memories.values():
            if (memory.get("lifecycle") == "active"
                    and memory.get("scope") in scopes):
                hits.append({
                    "memory": dict(memory),
                    "relevance": 0.9,
                    "is_current_truth": True,
                })
        return hits[:top_k]

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


def test_conversational_create_persists_approved_scope_conversation_and_audit(lifecycle):
    conversation = str(uuid4())
    gate = PersonalCreateGate()
    token = gate.offer(content="No projeto JARVIS prefiro Vuetify 3",
                       scope="project:jarvis", conversation_id=conversation)
    pending = gate.consume(token, conversation, "project:jarvis")
    result = lifecycle.create(
        content=pending.content, scope=pending.scope,
        conversation_id=pending.conversation_id, confirmation=pending.authorization,
    )
    assert result["status"] == "CONFIRMED"
    assert result["memory_type"] == "semantic"
    memory = lifecycle.client.memories[result["memory_id"]]
    assert memory["content"] == pending.content
    assert memory["provenance"]["conversation_uuid"] == conversation
    assert memory["provenance"]["source_ref"] == (
        "memory-operation:" + result["operation_id"]
    )
    audit = lifecycle.journal.get(result["operation_id"])
    assert audit["status"] == "confirmed"
    assert audit["confirmation_method"] == "desktop_approved"
    assert audit["confirmation_conversation_id"] == conversation
    assert audit["confirmation_ref"] == (
        "user-confirmation:" + pending.authorization.authorization_id
    )
    assert memory["provenance"]["confirmation_ref"] == audit["confirmation_ref"]
    assert lifecycle.journal.owned_user_memory(result["memory_id"], URL)
    with sqlite3.connect(lifecycle.journal._store.path) as db:
        assert db.execute(
            "SELECT payload_json FROM cognitive_write_operations WHERE id=?",
            (result["operation_id"],),
        ).fetchone()[0] is None


def test_conversational_create_refuses_unapproved_or_sensitive_changes(lifecycle):
    conv = str(uuid4())
    valid = PersonalMutationAuthorization.from_desktop_approval(
        action="create", conversation_id=conv,
    )
    with pytest.raises(ValueError, match="approval"):
        lifecycle.create(content="test", scope="global",
                         conversation_id=str(uuid4()), confirmation=valid)
    with pytest.raises(ValueError, match="sensitive"):
        lifecycle.create(content="Minha senha: 12345678", scope="global",
                         conversation_id=conv, confirmation=valid)
    with pytest.raises(ValueError, match="scope"):
        lifecycle.create(content="test", scope="project:foreign",
                         conversation_id=conv, confirmation=valid)
    assert not lifecycle.client.calls


def test_conversational_create_remote_unknown_never_retries(lifecycle):
    conv = str(uuid4())
    consent = PersonalMutationAuthorization.from_desktop_approval(
        action="create", conversation_id=conv,
    )
    lifecycle.client.failure = "RESULT_UNKNOWN"
    outcome = lifecycle.create(content="Preferência de teste", scope="global",
                               conversation_id=conv, confirmation=consent)
    assert outcome["status"] == "RESULT_UNKNOWN"
    assert outcome["retry_automatically"] is False
    audit = lifecycle.journal.get(outcome["operation_id"])
    assert audit["status"] == "unknown"
    assert audit["confirmation_method"] == "desktop_approved"
    assert sum(c[0] == "create" for c in lifecycle.client.calls) == 1


def test_direct_user_request_create_is_audited_by_original_message(lifecycle):
    from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
    store = lifecycle.journal._store
    conversation = store.create_conversation()
    phrase = ("JARVIS, lembre que no projeto JARVIS "
              "a palavra de teste é morango.")
    source_message = store.append_user_message(conversation, phrase)
    consent = PersonalMutationAuthorization.from_explicit_user_message(
        action="create", conversation_id=conversation, message_id=source_message,
    )
    result = lifecycle.create(
        content="no projeto JARVIS a palavra de teste é morango",
        scope="project:jarvis", conversation_id=conversation,
        confirmation=consent,
    )
    assert result["status"] == "CONFIRMED"
    record = lifecycle.journal.get(result["operation_id"])
    assert record["confirmation_ref"] == "user-message:" + source_message
    assert record["confirmation_method"] == "user_direct_intent"
    assert record["confirmation_conversation_id"] == conversation
    assert record["status"] == "confirmed"
    saved = lifecycle.client.memories[result["memory_id"]]
    assert saved["provenance"]["confirmation_ref"] == record["confirmation_ref"]
    assert saved["provenance"]["source_ref"] == (
        "memory-operation:" + result["operation_id"]
    )
    assert lifecycle.journal.owned_user_memory(result["memory_id"], URL)
    with sqlite3.connect(store.path) as db:
        assert db.execute(
            "SELECT payload_json FROM cognitive_write_operations WHERE id=?",
            (result["operation_id"],),
        ).fetchone()[0] is None
    # Same source message cannot be replayed even after payload scrubbing.
    with pytest.raises(sqlite3.IntegrityError):
        lifecycle.create(
            content="no projeto JARVIS a palavra de teste é morango",
            scope="project:jarvis", conversation_id=conversation,
            confirmation=consent,
        )
    assert sum(call[0] == "create" for call in lifecycle.client.calls) == 1


def test_direct_create_never_accepts_altered_scope_or_content(lifecycle):
    from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
    store = lifecycle.journal._store
    conversation = store.create_conversation()
    message = store.append_user_message(
        conversation, "JARVIS, lembre que no projeto JARVIS prefiro Python."
    )
    consent = PersonalMutationAuthorization.from_explicit_user_message(
        action="create", conversation_id=conversation, message_id=message,
    )
    for content, scope in (
        ("no projeto JARVIS prefiro outra coisa", "project:jarvis"),
        ("no projeto JARVIS prefiro Python", "global"),
    ):
        with pytest.raises(ValueError, match="direct_create_not_authorized"):
            lifecycle.create(content=content, scope=scope,
                             conversation_id=conversation, confirmation=consent)
    assert lifecycle.client.calls == []


def test_direct_create_requires_persisted_exact_user_message(lifecycle):
    from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
    store = lifecycle.journal._store
    conversation = store.create_conversation()
    fake_id = str(uuid4())
    consent = PersonalMutationAuthorization.from_explicit_user_message(
        action="create", conversation_id=conversation, message_id=fake_id,
    )
    with pytest.raises(ValueError, match="direct_create_not_authorized"):
        lifecycle.create(content="prefiro teal", scope="global",
                         conversation_id=conversation, confirmation=consent)
    message = store.append_user_message(
        conversation, "Qual seria a frase 'JARVIS, lembre que prefiro teal'?"
    )
    consent2 = PersonalMutationAuthorization.from_explicit_user_message(
        action="create", conversation_id=conversation, message_id=message,
    )
    with pytest.raises(ValueError, match="direct_create_not_authorized"):
        lifecycle.create(content="prefiro teal", scope="global",
                         conversation_id=conversation, confirmation=consent2)
    assert lifecycle.client.calls == []

def test_natural_target_resolution_uses_only_owned_memory(lifecycle):
    owned_id = owned(lifecycle.journal, lifecycle.client)
    foreign_id = str(uuid4())
    lifecycle.client.memories[foreign_id] = {
        "memory_id": foreign_id, "memory_type": "profile", "scope": "global",
        "content": "Outra preferência", "lifecycle": "active",
        "provenance": {
            "origin_kind": "user_asserted", "source_system": "jarvis",
            "source_ref": "memory-operation:foreign",
        },
    }
    preview = lifecycle.resolve_preview(
        "atualize minha preferência de cor",
        action="supersede", scopes=["global"],
    )
    assert preview["memory_id"] == owned_id
    assert preview["content"] == "Prefiro teal"


def test_natural_target_resolution_fails_closed_when_ambiguous(lifecycle):
    owned(lifecycle.journal, lifecycle.client)
    owned(lifecycle.journal, lifecycle.client)
    with pytest.raises(ValueError, match="memory_target_ambiguous"):
        lifecycle.resolve_preview(
            "esqueça minha preferência",
            action="forget", scopes=["global"],
        )


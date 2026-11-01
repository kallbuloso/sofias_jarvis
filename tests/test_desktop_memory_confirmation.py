"""Memory confirmation: simulate desktop execution without live services."""
from __future__ import annotations

import json
import time
from uuid import uuid4

import pytest
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication
from jarvis.desktop.bridge import JarvisBridge, MemoryMutationWorker
from jarvis.memory import cognitive, personal_lifecycle, connection
from jarvis.secrets.windows import WindowsCredentialStore

class FakeCognitive:
    base_url = "https://memory.example"
    def __init__(self, url, key):
        assert url == self.base_url and key == "FAKE-KEY"
    def diagnose(self):
        return {"status": "COMPATIBLE"}

def prepare(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: "FAKE-KEY")
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeCognitive)

def test_mutation_requires_consumed_confirmation_and_cannot_repeat(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    app = QCoreApplication.instance() or QCoreApplication([])
    bridge = JarvisBridge()
    conv = json.loads(bridge.createConversation())["id"]
    mid = str(uuid4())
    preview = {"memory_id": mid, "scope": "global", "content": "old",
               "source_ref": "memory-operation:owned", "memory_type": "profile",
               "lifecycle": "active"}
    token, phrase = bridge._mutation_gate.offer("supersede", preview, "new", conv)
    calls = []
    def replace(self, confirmed_preview, *, new_content, confirmation):
        assert confirmation.method == "desktop_typed"
        assert confirmation.action == "supersede"
        assert confirmation.target_memory_id == confirmed_preview["memory_id"]
        assert confirmation.conversation_id == conv
        calls.append((confirmed_preview["memory_id"], new_content))
        return {"status": "CONFIRMED", "operation_id": str(uuid4()),
                "replacement_memory_id": str(uuid4())}
    monkeypatch.setattr(personal_lifecycle.PersonalMemoryLifecycle, "supersede", replace)
    assert json.loads(bridge.confirmPersonalMutation(token, "SIM", conv)) == {
        "ok": False, "error": "authorization_invalid_or_expired",
    }
    assert calls == []
    token, phrase = bridge._mutation_gate.offer("supersede", preview, "new", conv)
    assert json.loads(bridge.confirmPersonalMutation(token, phrase, str(uuid4())))["ok"] is False
    assert calls == []
    token, phrase = bridge._mutation_gate.offer("supersede", preview, "new", conv)
    replies = []
    bridge.streamEvent.connect(lambda raw: replies.append(json.loads(raw)))
    accepted = json.loads(bridge.confirmPersonalMutation(token, phrase, conv))
    assert accepted["status"] == "MUTATION_REQUESTED"
    assert json.loads(bridge.confirmPersonalMutation(token, phrase, conv))["ok"] is False
    deadline = time.monotonic() + 5
    try:
        while bridge.active and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
    finally:
        if bridge._mutation_thread is not None:
            bridge._mutation_thread.quit()
            bridge._mutation_thread.wait(3000)
            app.processEvents()
    assert calls == [(mid, "new")]
    assert not bridge.active
    assert len(replies) == 1
    assert replies[0]["type"] == "memory_mutation"
    assert replies[0]["status"] == "CONFIRMED"

def test_cancelled_preview_has_no_mutation(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    bridge = JarvisBridge()
    conv = json.loads(bridge.createConversation())["id"]
    mid = str(uuid4())
    token, phrase = bridge._mutation_gate.offer("forget",
        {"memory_id": mid, "source_ref": "memory-operation:owned"}, "", conv)
    assert json.loads(bridge.cancelPendingPersonalMutation())["status"] == "CANCELLED"
    assert json.loads(bridge.confirmPersonalMutation(token, phrase, conv))["ok"] is False
    assert not bridge.active


def test_desktop_mutation_worker_journals_typed_consent(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    from jarvis.desktop.bridge import MemoryMutationWorker
    from jarvis.config import database_path
    from jarvis.memory.journal import MemoryOperationJournal
    from jarvis.memory.personal_confirmation import PersonalMutationGate

    journal = MemoryOperationJournal(database_path())
    source_op = str(uuid4())
    memory_id = str(uuid4())
    source_ref = "memory-operation:" + source_op
    journal.prepare(source_op, "https://memory.example", {
        "idempotency_key": source_op, "content": "Laranja",
        "memory_type": "semantic", "scope": "project:jarvis",
        "provenance": {"origin_kind": "user_asserted",
                       "source_system": "jarvis", "source_ref": source_ref},
    })
    journal.claim(source_op)
    journal.resolve(source_op, status="confirmed", memory_id=memory_id)
    record = {
        "memory_id": memory_id, "content": "Laranja",
        "memory_type": "semantic", "scope": "project:jarvis",
        "lifecycle": "active",
        "provenance": {"origin_kind": "user_asserted",
                       "source_system": "jarvis", "source_ref": source_ref},
    }
    calls = []

    class FakeService(FakeCognitive):
        def get(self, target):
            calls.append("get")
            assert target == memory_id
            return dict(record)

        def forget(self, target, *, idempotency_key):
            calls.append("forget")
            assert target == memory_id
            assert idempotency_key
            return {**record, "content": None, "scope": None, "lifecycle": "forgotten"}

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeService)
    conversation_id = str(uuid4())
    gate = PersonalMutationGate()
    preview = {**record, "source_ref": source_ref}
    token, phrase = gate.offer("forget", preview, "", conversation_id)
    pending = gate.consume(token, phrase, conversation_id)
    worker = MemoryMutationWorker(pending)
    results = []
    worker.finishedMutation.connect(lambda raw: results.append(json.loads(raw)))
    worker.run()
    assert results[0]["ok"] is True
    assert results[0]["status"] == "CONFIRMED"
    assert calls == ["get", "forget"]
    audit = journal.get(results[0]["operationId"])
    assert audit["status"] == "confirmed"
    assert audit["confirmation_method"] == "desktop_typed"
    assert audit["confirmation_conversation_id"] == conversation_id
    assert audit["confirmation_ref"] == (
        "user-confirmation:" + pending.authorization.authorization_id
    )
    assert audit["confirmed_by_user_at"]

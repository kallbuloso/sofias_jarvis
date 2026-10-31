"""GUI bridge boundary tests (execute only when optional Qt is installed)."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from jarvis.desktop.bridge import JarvisBridge


def test_bridge_allows_conversation_crud_without_exposing_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    created = json.loads(bridge.createConversation())
    assert created["ok"]
    conv = created["id"]
    assert conv in [x["id"] for x in json.loads(bridge.listConversations())["items"]]
    assert json.loads(bridge.listMessages(conv))["items"] == []
    assert json.loads(bridge.listMessages("nonexistent"))["error"] == "unknown_conversation"
    boot = json.loads(bridge.bootstrap())
    assert "credentialConfigured" in boot
    assert not any("api_key" in k.lower() or "secret" in k.lower() for k in boot)


def test_bridge_refuses_missing_model_without_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    conv = json.loads(bridge.createConversation())["id"]
    result = json.loads(bridge.sendMessage(conv, "Olá", " "))
    assert result == {"ok": False, "error": "missing_text_or_model"}
    assert bridge.active is False



def test_bootstrap_reports_memory_configuration_without_leaking_key(tmp_path, monkeypatch):
    from jarvis.memory import connection
    from jarvis.secrets.windows import WindowsCredentialStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url", lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "PRIVATE-TOKEN")
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key", lambda self: "PRIVATE-OPENAI")
    bridge = JarvisBridge()
    boot = json.loads(bridge.bootstrap())
    assert boot["memoryConfigured"] is True
    assert boot["credentialConfigured"] is True
    assert "PRIVATE-TOKEN" not in json.dumps(boot)
    assert "PRIVATE-OPENAI" not in json.dumps(boot)


def test_memory_enabled_rejects_missing_or_malformed_scope_before_thread(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    conversation = json.loads(bridge.createConversation())["id"]
    for scope in ("", "project:Other", "project:jarvis/other", "global,project:other"):
        result = json.loads(bridge.sendMessageWithMemory(conversation, "Qual cor?", "model", scope))
        assert result == {"ok": False, "error": "invalid_memory_scope"}
        assert bridge.active is False


def test_worker_memory_response_is_provenance_bounded(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    from jarvis.desktop.bridge import ReplyWorker
    from jarvis.memory import cognitive, connection
    from jarvis.secrets.windows import WindowsCredentialStore
    from jarvis.conversation.store import SQLiteConversationStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url", lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "MEMORY-SECRET")

    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    conversation = store.create_conversation()
    requests, memory_calls = [], []

    class Responses:
        def create(self, *, model, input, stream):
            requests.append(input)
            yield SimpleNamespace(type="response.output_text.delta", delta="A cor é teal.")
            yield SimpleNamespace(type="response.completed", delta="")

    class FakeMemory:
        def __init__(self, url, key):
            assert (url, key) == ("https://memory.example", "MEMORY-SECRET")
        def recall(self, **kwargs):
            memory_calls.append(kwargs)
            return [{
                "memory": {
                    "memory_id": "ab89ac04-7134-49c6-9fa2-2880a296d50a",
                    "scope": "global", "content": "Prefiro interfaces teal.",
                    "lifecycle": "active", "provenance": {"origin_kind": "user_asserted"},
                },
                "relevance": 0.774, "is_current_truth": True,
            }]

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeMemory)
    monkeypatch.setitem(
        sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda **kw: SimpleNamespace(responses=Responses())),
    )
    worker = ReplyWorker(conversation, "Qual minha cor?", "model", "OPENAI-SECRET", memory_scope="global")
    results = []
    worker.done.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [(conversation, "completed", "", "RESULTS_FOUND")]
    assert memory_calls == [{
        "query": "Qual minha cor?", "scopes": ["global"], "top_k": 5,
        "include_superseded": False,
    }]
    assert len(requests) == 1
    assert requests[0][0]["role"] == "developer"
    assert "Prefiro interfaces teal." in requests[0][2]["content"]
    assert store.completed_context(conversation) == [
        {"role": "user", "content": "Qual minha cor?"},
        {"role": "assistant", "content": "A cor é teal."},
    ]
    assert worker.api_key == ""


def test_worker_without_memory_never_accesses_memory_vault(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    from jarvis.desktop.bridge import ReplyWorker
    from jarvis.secrets.windows import WindowsCredentialStore
    from jarvis.conversation.store import SQLiteConversationStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        WindowsCredentialStore, "get_memory_key",
        lambda self: (_ for _ in ()).throw(AssertionError("memory must be disabled")),
    )
    conversation = SQLiteConversationStore(tmp_path / "jarvis.sqlite3").create_conversation()

    class Responses:
        def create(self, *, model, input, stream):
            assert len(input) == 2
            assert input[0]["role"] == "developer"
            assert "não invente" in input[0]["content"]
            assert input[-1] == {"role": "user", "content": "Oi"}
            yield SimpleNamespace(type="response.output_text.delta", delta="Olá")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda **kw: SimpleNamespace(responses=Responses())))
    worker = ReplyWorker(conversation, "Oi", "model", "OPENAI-SECRET")
    results = []
    worker.done.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [(conversation, "completed", "", "NOT_REQUESTED")]


def test_missing_memory_vault_degrades_without_leaking_key(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    from jarvis.desktop.bridge import ReplyWorker
    from jarvis.memory import connection
    from jarvis.secrets.windows import WindowsCredentialStore
    from jarvis.conversation.store import SQLiteConversationStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url", lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: None)
    conversation = SQLiteConversationStore(tmp_path / "jarvis.sqlite3").create_conversation()

    class Responses:
        def create(self, *, model, input, stream):
            assert '"status":"UNAVAILABLE"' in input[2]["content"]
            yield SimpleNamespace(type="response.output_text.delta", delta="Não consegui consultar a memória.")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda **kw: SimpleNamespace(responses=Responses())))
    worker = ReplyWorker(conversation, "Qual cor?", "model", "OPENAI-SECRET", memory_scope="global")
    results = []
    worker.done.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [(conversation, "completed", "", "UNAVAILABLE")]
    assert worker.api_key == ""



def test_attribution_policy_does_not_claim_disabled_memory(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    from jarvis.desktop.bridge import ReplyWorker
    from jarvis.conversation.store import SQLiteConversationStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = store.create_conversation()
    store.append_user_message(cid, "Olá")
    previous = store.begin_assistant_message(cid)
    store.append_assistant_delta(previous, "Sua cor preferida é teal.")
    store.end_assistant_message(previous, successful=True)

    class Responses:
        def create(self, *, model, input, stream):
            assert input[0]["role"] == "developer"
            assert "do próprio assistente" in input[0]["content"]
            assert input[-2] == {"role": "assistant", "content": "Sua cor preferida é teal."}
            assert input[-1] == {"role": "user", "content": "De onde veio essa preferência?"}
            yield SimpleNamespace(type="response.output_text.delta", delta="Foi mencionado antes, mas não verificado.")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda **kwargs: SimpleNamespace(responses=Responses())))
    worker = ReplyWorker(cid, "De onde veio essa preferência?", "model", "OPENAI-SECRET")
    results = []
    worker.done.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [(cid, "completed", "", "NOT_REQUESTED")]
    assert all(m["role"] != "developer" for m in store.completed_context(cid))

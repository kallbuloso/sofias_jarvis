from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.desktop.bridge import JarvisBridge
from jarvis.inference.profiles import InferenceProfileStore
from jarvis.secrets.windows import WindowsCredentialStore


def _vault(monkeypatch):
    secrets = {}
    monkeypatch.setattr(
        WindowsCredentialStore, "get_openai_key",
        lambda self: "OPENAI-PRIVATE",
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "get_memory_key",
        lambda self: None,
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "get_connection_secret",
        lambda self, connection_id: secrets.get(connection_id),
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "set_connection_secret",
        lambda self, connection_id, secret: secrets.__setitem__(
            connection_id, secret
        ),
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "delete_connection_secret",
        lambda self, connection_id: secrets.pop(connection_id, None),
    )
    return secrets


def _verified_anthropic(path, monkeypatch):
    manager = ConnectionManager(
        ConnectionStore(path),
        WindowsCredentialStore(),
    )
    anthropic = manager.create_ai(
        "anthropic",
        "ANTHROPIC-PRIVATE",
        label="Claude principal",
    )
    manager.set_enabled(anthropic["id"], True)

    class Verifier:
        def inspect(self, secret):
            assert secret == "ANTHROPIC-PRIVATE"
            return {
                "availability": "available",
                "available_models": [
                    {"id": "claude-sonnet-5-5", "lifecycle": "active"}
                ],
            }

    manager._ai_verifiers["anthropic"] = Verifier()
    manager.verify_ai(anthropic["id"])
    return manager, anthropic


def test_current_manual_ai_selector_updates_general_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    _vault(monkeypatch)

    bridge = JarvisBridge()
    initial = json.loads(bridge.bootstrap())
    profiles = InferenceProfileStore(tmp_path / "jarvis.sqlite3")
    general = profiles.get_by_slug("general")

    assert general is not None
    assert general["configuration"]["primary"] == {
        "connection_id": initial["aiConnectionId"],
        "model": initial["model"],
    }

    _, anthropic = _verified_anthropic(
        tmp_path / "jarvis.sqlite3", monkeypatch,
    )
    selected = json.loads(bridge.selectAIConnection(
        "anthropic",
        anthropic["id"],
        "claude-sonnet-5-5",
    ))
    assert selected["ok"] is True

    updated = profiles.get_by_slug("general")
    assert updated["id"] == general["id"]
    assert updated["configuration"]["primary"] == {
        "connection_id": anthropic["id"],
        "model": "claude-sonnet-5-5",
    }


def test_desktop_resolution_uses_conversation_binding_over_global_selection(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    _vault(monkeypatch)

    bridge = JarvisBridge()
    initial = json.loads(bridge.bootstrap())
    assert initial["aiProvider"] == "openai"

    _, anthropic = _verified_anthropic(
        tmp_path / "jarvis.sqlite3", monkeypatch,
    )
    profiles = InferenceProfileStore(tmp_path / "jarvis.sqlite3")
    conversation_profile = profiles.create_profile(
        "conversation-claude",
        "Conversation Claude",
        connection_id=anthropic["id"],
        model="claude-sonnet-5-5",
        requirements={
            "streaming": True,
            "structured_output": True,
        },
        constraints={"locality": "cloud_allowed"},
    )

    conversation_id = json.loads(bridge.createConversation())["id"]
    profiles.bind(
        conversation_profile["id"],
        scope_type="conversation",
        scope_id=conversation_id,
    )

    execution = bridge._resolve_dispatch_inference(
        conversation_id,
        initial["model"],
    )

    assert execution.plan.selected_from == "conversation"
    assert execution.plan.profile_id == conversation_profile["id"]
    assert execution.plan.provider_id == "anthropic"
    assert execution.plan.connection_id == anthropic["id"]
    assert execution.plan.model == "claude-sonnet-5-5"
    assert execution.credential == "ANTHROPIC-PRIVATE"

    # Conversation binding must not mutate the global desktop selection/profile.
    general = profiles.get_by_slug("general")
    assert general["configuration"]["primary"]["connection_id"] == (
        initial["aiConnectionId"]
    )


def test_dispatch_worker_receives_resolved_plan_not_ui_model(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    _vault(monkeypatch)
    bridge = JarvisBridge()
    initial = json.loads(bridge.bootstrap())
    cid = json.loads(bridge.createConversation())["id"]

    captured = {}

    class FakeThread:
        def __init__(self, *args, **kwargs):
            self.started = type("Signal", (), {"connect": lambda self, fn: None})()
            self.finished = type("Signal", (), {"connect": lambda self, fn: None})()

        def start(self):
            pass

    class FakeWorker:
        def __init__(self, conversation_id, prompt, model, credential, **kwargs):
            captured.update({
                "conversation_id": conversation_id,
                "prompt": prompt,
                "model": model,
                "credential": credential,
                **kwargs,
            })
            signal = type("Signal", (), {"connect": lambda self, fn: None})
            self.delta = signal()
            self.done = signal()
            self.knowledgeDone = signal()
            self.createProposed = signal()
            self.mutationProposed = signal()

        def moveToThread(self, thread):
            pass

        def deleteLater(self):
            pass

        def run(self):
            pass

    import jarvis.desktop.bridge as bridge_module
    monkeypatch.setattr(bridge_module, "ReplyWorker", FakeWorker)
    monkeypatch.setattr(bridge_module, "QThread", FakeThread)

    result = json.loads(bridge._dispatch(
        cid,
        "Oi",
        initial["model"],
        memory_scope=None,
        knowledge_dataset=None,
    ))

    assert result["ok"] is True
    assert captured["model"] == initial["model"]
    assert captured["provider_id"] == "openai"
    assert captured["connection_id"] == initial["aiConnectionId"]
    assert captured["inference_plan"].profile_slug == "general"
    assert captured["inference_plan"].selected_from == "global"
    assert captured["credential"] == "OPENAI-PRIVATE"

from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.desktop.bridge import JarvisBridge
from jarvis.inference.profiles import InferenceProfileStore
from jarvis.secrets.windows import WindowsCredentialStore


@pytest.fixture
def bridge_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MODEL", "gpt-6-luna")
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
    bridge = JarvisBridge()
    boot = json.loads(bridge.bootstrap())
    return tmp_path, bridge, boot, secrets


def _anthropic(path, secrets):
    store = ConnectionStore(path)
    manager = ConnectionManager(store, WindowsCredentialStore())
    connection = store.create(
        "anthropic",
        configuration={
            "label": "Claude principal",
            "observed_models": ["claude-sonnet-5-5"],
        },
    )
    secrets[connection["id"]] = "ANTHROPIC-PRIVATE"
    store.set_enabled(connection["id"], True)
    current = store.get(connection["id"])
    store.record_inspection(
        connection["id"],
        display_identity=current["display_identity"],
        external_account_ref=current["external_account_ref"],
        observed_permissions=current["observed_permissions"],
        availability="available",
        error_code=None,
    )
    return store.get(connection["id"])


def test_profile_surface_lists_general_without_exposing_secrets(bridge_env):
    _, bridge, boot, _ = bridge_env
    result = json.loads(bridge.listInferenceProfiles())

    assert result["ok"] is True
    assert len(result["items"]) == 1
    general = result["items"][0]
    assert general["slug"] == "general"
    assert general["name"] == "Geral"
    assert general["providerId"] == "openai"
    assert general["connectionId"] == boot["aiConnectionId"]
    assert general["model"] == "gpt-6-luna"
    serialized = json.dumps(result)
    assert "OPENAI-PRIVATE" not in serialized
    assert "credential" not in serialized.lower()


def test_create_profile_requires_usable_ai_connection_and_returns_public_data(
    bridge_env,
):
    path, bridge, _, secrets = bridge_env
    anthropic = _anthropic(path / "jarvis.sqlite3", secrets)

    result = json.loads(bridge.createInferenceProfile(
        "Coding profundo",
        "coding-deep",
        anthropic["id"],
        "claude-sonnet-5-5",
    ))

    assert result["ok"] is True
    profile = result["profile"]
    assert profile["slug"] == "coding-deep"
    assert profile["providerId"] == "anthropic"
    assert profile["connectionId"] == anthropic["id"]
    assert profile["model"] == "claude-sonnet-5-5"
    assert "ANTHROPIC-PRIVATE" not in json.dumps(result)


def test_conversation_binding_can_override_and_then_return_to_global(bridge_env):
    path, bridge, boot, secrets = bridge_env
    anthropic = _anthropic(path / "jarvis.sqlite3", secrets)
    created = json.loads(bridge.createInferenceProfile(
        "Coding profundo",
        "coding-deep",
        anthropic["id"],
        "claude-sonnet-5-5",
    ))["profile"]
    cid = json.loads(bridge.createConversation())["id"]

    inherited = json.loads(bridge.getConversationInference(cid))
    assert inherited["ok"] is True
    assert inherited["bindingProfileId"] is None
    assert inherited["resolved"]["selected_from"] == "global"
    assert inherited["resolved"]["provider_id"] == "openai"

    bound = json.loads(bridge.setConversationInferenceProfile(
        cid, created["id"],
    ))
    assert bound["ok"] is True
    assert bound["bindingProfileId"] == created["id"]
    assert bound["resolved"]["selected_from"] == "conversation"
    assert bound["resolved"]["provider_id"] == "anthropic"
    assert bound["resolved"]["model"] == "claude-sonnet-5-5"

    inherited_again = json.loads(
        bridge.setConversationInferenceProfile(cid, "")
    )
    assert inherited_again["ok"] is True
    assert inherited_again["bindingProfileId"] is None
    assert inherited_again["resolved"]["selected_from"] == "global"
    assert inherited_again["resolved"]["connection_id"] == boot["aiConnectionId"]


def test_conversation_profile_rejects_unknown_profile(bridge_env):
    _, bridge, _, _ = bridge_env
    cid = json.loads(bridge.createConversation())["id"]

    result = json.loads(bridge.setConversationInferenceProfile(
        cid, "00000000-0000-0000-0000-000000000001",
    ))

    assert result["ok"] is False
    assert result["error"] == "INFERENCE_PROFILE_NOT_AVAILABLE"


def test_unbind_is_idempotent_for_inherit_global(bridge_env):
    _, bridge, _, _ = bridge_env
    cid = json.loads(bridge.createConversation())["id"]

    first = json.loads(bridge.setConversationInferenceProfile(cid, ""))
    second = json.loads(bridge.setConversationInferenceProfile(cid, ""))

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["bindingProfileId"] is None
    assert second["resolved"]["selected_from"] == "global"


def test_store_unbind_removes_only_requested_scope(bridge_env):
    path, bridge, _, _ = bridge_env
    cid = json.loads(bridge.createConversation())["id"]
    profiles = InferenceProfileStore(path / "jarvis.sqlite3")
    general = profiles.get_by_slug("general")
    profiles.bind(
        general["id"], scope_type="conversation", scope_id=cid,
    )

    assert profiles.unbind(
        scope_type="conversation", scope_id=cid,
    ) is True
    assert profiles.get_binding(
        scope_type="conversation", scope_id=cid,
    ) is None
    assert profiles.get_binding(scope_type="global") is not None

def test_deleting_conversation_removes_its_inference_binding(bridge_env):
    path, bridge, _, _ = bridge_env
    cid = json.loads(bridge.createConversation())["id"]
    profiles = InferenceProfileStore(path / "jarvis.sqlite3")
    general = profiles.get_by_slug("general")
    profiles.bind(
        general["id"],
        scope_type="conversation",
        scope_id=cid,
    )

    deleted = json.loads(bridge.deleteConversation(cid))
    assert deleted["ok"] is True
    assert profiles.get_binding(
        scope_type="conversation",
        scope_id=cid,
    ) is None
    assert profiles.get_binding(scope_type="global") is not None


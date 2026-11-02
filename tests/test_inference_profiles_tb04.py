from __future__ import annotations

import json
import sqlite3

import pytest

from jarvis.connections.store import ConnectionStore
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.inference.profiles import InferenceProfileStore
from jarvis.secrets.windows import WindowsCredentialStore


def test_schema_v7_adds_profiles_and_bindings_without_losing_history(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    store = SQLiteConversationStore(path)
    cid = store.create_conversation("Antes do TB-04D")
    store.append_user_message(cid, "mensagem existente")

    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE inference_bindings")
        db.execute("DROP TABLE inference_profiles")
        db.execute("PRAGMA user_version = 6")
        db.commit()

    reopened = SQLiteConversationStore(path)
    assert reopened.list_messages(cid)[0]["content"] == "mensagem existente"

    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 7
        names = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'inference_%'"
            ).fetchall()
        }
    assert names == {"inference_profiles", "inference_bindings"}


def test_ensure_general_creates_one_global_profile_and_never_overwrites_it(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections = ConnectionStore(path)
    openai = connections.create("openai")
    anthropic = connections.create("anthropic")
    profiles = InferenceProfileStore(path)

    profile, binding, created = profiles.ensure_general(
        connection_id=openai["id"],
        model="gpt-6-luna",
    )
    assert created is True
    assert profile["slug"] == "general"
    assert profile["name"] == "Geral"
    assert profile["configuration"]["primary"] == {
        "connection_id": openai["id"],
        "model": "gpt-6-luna",
    }
    assert profile["configuration"]["requirements"] == {
        "streaming": True,
        "structured_output": True,
    }
    assert profile["configuration"]["constraints"] == {
        "locality": "cloud_allowed",
    }
    assert binding["scope_type"] == "global"
    assert binding["scope_id"] == "*"
    assert binding["profile_id"] == profile["id"]

    again, again_binding, created = profiles.ensure_general(
        connection_id=anthropic["id"],
        model="claude-sonnet-5-5",
    )
    assert created is False
    assert again["id"] == profile["id"]
    assert again["configuration"]["primary"] == {
        "connection_id": openai["id"],
        "model": "gpt-6-luna",
    }
    assert again_binding["id"] == binding["id"]


def test_global_binding_is_unique_and_rebinding_updates_same_identity(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections = ConnectionStore(path)
    one = connections.create("openai")
    two = connections.create("anthropic")
    profiles = InferenceProfileStore(path)
    general = profiles.create_profile(
        "general", "Geral", connection_id=one["id"], model="gpt-6-luna",
    )
    deep = profiles.create_profile(
        "coding-deep", "Coding profundo",
        connection_id=two["id"], model="claude-sonnet-5-5",
    )

    first = profiles.bind(general["id"], scope_type="global")
    second = profiles.bind(deep["id"], scope_type="global")

    assert second["id"] == first["id"]
    assert second["profile_id"] == deep["id"]

    with sqlite3.connect(path) as db:
        count = db.execute(
            "SELECT COUNT(*) FROM inference_bindings "
            "WHERE scope_type='global' AND scope_id='*'"
        ).fetchone()[0]
    assert count == 1


def test_profile_rejects_external_integration_connection(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    github = ConnectionStore(path).create("github")
    profiles = InferenceProfileStore(path)

    with pytest.raises(
        ValueError, match="inference_profile_requires_ai_connection"
    ):
        profiles.create_profile(
            "invalid", "Inválido",
            connection_id=github["id"],
            model="not-a-model",
        )


def test_profile_persistence_never_contains_provider_secret(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connection = ConnectionStore(path).create("openai")
    profiles = InferenceProfileStore(path)
    profile = profiles.create_profile(
        "general", "Geral",
        connection_id=connection["id"],
        model="gpt-6-luna",
    )

    serialized = json.dumps(profile)
    assert "api_key" not in serialized.lower()
    assert "secret" not in serialized.lower()
    assert b"PRIVATE-TOKEN" not in path.read_bytes()


def test_desktop_bootstrap_materializes_general_from_existing_selection(
    tmp_path, monkeypatch,
):
    pytest.importorskip("PySide6")
    from jarvis.desktop.bridge import JarvisBridge

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MODEL", "gpt-6-luna")
    monkeypatch.setattr(
        WindowsCredentialStore, "get_openai_key",
        lambda self: "PRIVATE-OPENAI",
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "get_memory_key",
        lambda self: None,
    )

    boot = json.loads(JarvisBridge().bootstrap())
    assert boot["aiProvider"] == "openai"
    assert boot["model"] == "gpt-6-luna"

    profiles = InferenceProfileStore(tmp_path / "jarvis.sqlite3")
    general = profiles.get_by_slug("general")
    binding = profiles.get_binding(scope_type="global")

    assert general is not None
    assert binding is not None
    assert binding["profile_id"] == general["id"]
    assert general["configuration"]["primary"] == {
        "connection_id": boot["aiConnectionId"],
        "model": "gpt-6-luna",
    }
    assert "PRIVATE-OPENAI" not in json.dumps(general)

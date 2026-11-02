from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from jarvis.connections.github import GitHubConnectionAdapter, GitHubConnectionError
from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.conversation.store import SQLiteConversationStore


class FakeVault:
    def __init__(self):
        self.secrets = {}
        self.deleted = []

    def get_connection_secret(self, connection_id):
        return self.secrets.get(connection_id)

    def set_connection_secret(self, connection_id, secret):
        self.secrets[connection_id] = secret

    def delete_connection_secret(self, connection_id):
        self.deleted.append(connection_id)
        self.secrets.pop(connection_id, None)


class FakeGitHub:
    def __init__(self, *, fail=None):
        self.fail = fail
        self.tokens = []

    def inspect(self, token):
        self.tokens.append(token)
        if self.fail:
            raise GitHubConnectionError(self.fail)
        return {
            "display_identity": "kallbuloso",
            "external_account_ref": "4968546",
            "observed_permissions": [],
            "availability": "available",
        }


def test_current_schema_keeps_connections_without_losing_existing_history(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    store = SQLiteConversationStore(path)
    cid = store.create_conversation("Antes do TB-04")
    store.append_user_message(cid, "mensagem existente")

    with sqlite3.connect(path) as raw:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 7
        assert raw.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='integration_connections'"
        ).fetchone()

    reopened = SQLiteConversationStore(path)
    assert reopened.list_messages(cid)[0]["content"] == "mensagem existente"


def test_connection_store_never_persists_secret(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    store = ConnectionStore(path)
    item = store.create("github", configuration={"label": "Principal"})
    serialized = json.dumps(item)
    assert item["provider_id"] == "github"
    assert item["enabled"] is False
    assert item["availability"] == "unknown"
    assert "token" not in serialized.lower()
    assert item["credential_ref"] == f"wincred:{item['id']}"

    raw = path.read_bytes()
    assert b"github" in raw
    assert b"PRIVATE-TOKEN" not in raw


def test_manager_github_lifecycle_is_identity_bound_and_disabled_by_default(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    github = FakeGitHub()
    manager._adapters["github"] = github

    item = manager.create_github("PRIVATE-TOKEN", label="Minha conta")
    assert item["configured"] is True
    assert item["display_identity"] == "kallbuloso"
    assert item["external_account_ref"] == "4968546"
    assert item["availability"] == "available"
    assert item["enabled"] is False
    assert github.tokens == ["PRIVATE-TOKEN"]
    assert "PRIVATE-TOKEN" not in json.dumps(item)

    enabled = manager.set_enabled(item["id"], True)
    assert enabled["enabled"] is True

    disabled = manager.set_enabled(item["id"], False)
    assert disabled["enabled"] is False

    assert manager.remove(item["id"]) is True
    assert vault.deleted == [item["id"]]
    assert store.get(item["id"]) is None


def test_invalid_github_credential_remains_configured_but_not_enableable(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    manager._adapters["github"] = FakeGitHub(fail="AUTHENTICATION_FAILED")

    item = manager.create_github("BAD-TOKEN")
    assert item["configured"] is True
    assert item["availability"] == "auth_required"
    assert item["last_error_code"] == "AUTHENTICATION_FAILED"
    assert item["external_account_ref"] is None

    with pytest.raises(ValueError, match="CONNECTION_NOT_VERIFIED"):
        manager.set_enabled(item["id"], True)


def test_two_connections_keep_secrets_and_identities_isolated(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)

    identities = iter([
        ("personal", "100"),
        ("work", "200"),
    ])

    class MultiGitHub:
        def inspect(self, token):
            login, account = next(identities)
            return {
                "display_identity": login,
                "external_account_ref": account,
                "observed_permissions": [],
                "availability": "available",
            }

    manager._adapters["github"] = MultiGitHub()
    one = manager.create_github("TOKEN-ONE")
    two = manager.create_github("TOKEN-TWO")

    assert one["id"] != two["id"]
    assert one["external_account_ref"] != two["external_account_ref"]
    assert vault.secrets[one["id"]] == "TOKEN-ONE"
    assert vault.secrets[two["id"]] == "TOKEN-TWO"


class FakeResponse:
    status = 200

    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self):
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(
            {"login": "kallbuloso", "id": 4968546},
            {"X-OAuth-Scopes": ""},
        )


def test_github_inspector_uses_bearer_without_returning_token():
    opener = FakeOpener()
    result = GitHubConnectionAdapter(opener=opener).inspect("PRIVATE")
    assert result == {
        "display_identity": "kallbuloso",
        "external_account_ref": "4968546",
        "observed_permissions": [],
        "availability": "available",
    }
    request, timeout = opener.requests[0]
    assert request.full_url == "https://api.github.com/user"
    assert request.get_header("Authorization") == "Bearer PRIVATE"
    assert timeout == 10.0
    assert "PRIVATE" not in json.dumps(result)


def test_desktop_integration_surface_never_rehydrates_stored_token():
    source = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "type=\"password\"" in source
    assert "githubToken.value = ''" in source
    assert "listIntegrationConnections" in source
    assert "connection.token" not in source

    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    assert "configureGitHubConnection" in bridge
    assert "IntegrationConnectionWorker" in bridge

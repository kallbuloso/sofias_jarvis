from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from jarvis.connections.ai_verification import (
    AIConnectionVerificationError,
    AnthropicConnectionVerifier,
)
from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore


class FakeHeaders(dict):
    pass


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return FakeResponse(self.response)


def test_anthropic_verifier_authenticates_with_models_endpoint():
    opener = FakeOpener(response={
        "data": [
            {"id": "claude-sonnet-5-5", "lifecycle": "active"},
            {"id": "claude-haiku-5-5", "lifecycle": "active"},
        ],
        "has_more": False,
    })
    result = AnthropicConnectionVerifier(opener=opener).inspect("PRIVATE")
    assert result == {
        "availability": "available",
        "available_models": [
            {"id": "claude-sonnet-5-5", "lifecycle": "active"},
            {"id": "claude-haiku-5-5", "lifecycle": "active"},
        ],
    }
    request, timeout = opener.requests[0]
    assert request.full_url == "https://api.anthropic.com/v1/models?limit=100"
    assert request.get_header("Authorization") == "Bearer PRIVATE"
    assert request.get_header("Anthropic-version") == "2026-10-21"
    assert timeout == 10.0
    assert "PRIVATE" not in json.dumps(result)


def test_anthropic_verifier_normalizes_revoked_key_to_authentication_failed():
    error = HTTPError(
        "https://api.anthropic.com/v1/models",
        401,
        "Unauthorized",
        FakeHeaders(),
        BytesIO(b"{}"),
    )
    with pytest.raises(
        AIConnectionVerificationError, match="AUTHENTICATION_FAILED"
    ):
        AnthropicConnectionVerifier(
            opener=FakeOpener(error=error)
        ).inspect("OLD-KEY")


class FakeVault:
    def __init__(self):
        self.secrets = {}

    def get_openai_key(self):
        return None

    def get_connection_secret(self, connection_id):
        return self.secrets.get(connection_id)

    def set_connection_secret(self, connection_id, secret):
        self.secrets[connection_id] = secret

    def delete_connection_secret(self, connection_id):
        self.secrets.pop(connection_id, None)


class ValidVerifier:
    def inspect(self, secret):
        assert secret == "ANTHROPIC-PRIVATE"
        return {
            "availability": "available",
            "available_models": [
                {"id": "claude-sonnet-5-5", "lifecycle": "active"}
            ],
        }


class RevokedVerifier:
    def inspect(self, secret):
        raise AIConnectionVerificationError("AUTHENTICATION_FAILED")


def test_manager_persists_successful_ai_verification(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    manager._ai_verifiers["anthropic"] = ValidVerifier()

    item = manager.create_ai("anthropic", "ANTHROPIC-PRIVATE")
    result = manager.verify_ai(item["id"])

    assert result["availability"] == "available"
    assert result["last_error_code"] is None
    assert result["available_models"][0]["id"] == "claude-sonnet-5-5"
    persisted = store.get(item["id"])
    assert persisted["availability"] == "available"
    assert persisted["last_verified_at"] is not None


def test_revoked_verified_ai_connection_is_fail_closed_even_if_enabled(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    manager._ai_verifiers["anthropic"] = RevokedVerifier()

    item = manager.create_ai("anthropic", "OLD-KEY")
    manager.set_enabled(item["id"], True)
    checked = manager.verify_ai(item["id"])

    assert checked["availability"] == "auth_required"
    assert checked["last_error_code"] == "AUTHENTICATION_FAILED"
    with pytest.raises(ValueError, match="AI_CONNECTION_NOT_AVAILABLE"):
        manager.resolve_ai_connection(
            provider_id="anthropic", connection_id=item["id"],
        )


def test_ai_provider_ui_exposes_verify_and_availability():
    from pathlib import Path
    source = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "@click=\"checkAIConnection(connection)\">Verificar</v-btn>" in source
    assert "disponibilidade: {{ connection.availability }}" in source
    assert "último erro: {{ connection.last_error_code }}" in source

def test_verified_models_are_persisted_and_unknown_model_is_rejected(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    manager._ai_verifiers["anthropic"] = ValidVerifier()

    item = manager.create_ai("anthropic", "ANTHROPIC-PRIVATE")
    manager.set_enabled(item["id"], True)
    checked = manager.verify_ai(item["id"])

    assert checked["configuration"]["observed_models"] == [
        "claude-sonnet-5-5"
    ]

    resolved, _ = manager.resolve_ai_connection(
        provider_id="anthropic",
        connection_id=item["id"],
        model_id="claude-sonnet-5-5",
    )
    assert resolved["id"] == item["id"]

    with pytest.raises(ValueError, match="AI_MODEL_NOT_AVAILABLE"):
        manager.resolve_ai_connection(
            provider_id="anthropic",
            connection_id=item["id"],
            model_id="claude-not-accessible",
        )


def test_unverified_status_check_provider_is_not_used_for_inference(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)

    item = manager.create_ai("anthropic", "ANTHROPIC-PRIVATE")
    manager.set_enabled(item["id"], True)

    with pytest.raises(ValueError, match="AI_CONNECTION_NOT_VERIFIED"):
        manager.resolve_ai_connection(
            provider_id="anthropic",
            connection_id=item["id"],
            model_id="claude-sonnet-5-5",
        )


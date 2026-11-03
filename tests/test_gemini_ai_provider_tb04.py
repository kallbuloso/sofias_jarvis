from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from jarvis.adapters.litellm_inference import LiteLLMInferenceAdapter
from jarvis.connections.ai_verification import (
    AIConnectionVerificationError,
    GeminiConnectionVerifier,
)
from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.inference.factory import build_inference_provider
from jarvis.inference.profiles import InferenceProfileStore
from jarvis.inference.resolver import (
    InferenceResolutionContext,
    InferenceResolver,
)


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


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.raw if size < 0 else self.raw[:size]


class FakeOpener:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return FakeResponse(self.payload)


def test_gemini_registry_is_litellm_metadata_not_native_adapter(tmp_path):
    manager = ConnectionManager(
        ConnectionStore(tmp_path / "jarvis.sqlite3"), FakeVault(),
    )
    descriptor = next(
        item for item in manager.providers() if item["provider_id"] == "gemini"
    )

    assert descriptor["display_name"] == "Google Gemini"
    assert descriptor["provider_type"] == "ai_inference"
    assert descriptor["transport"] == "litellm"
    assert descriptor["litellm_prefix"] == "gemini"
    assert descriptor["status_check_support"] is True
    assert "inference.text.streaming" in descriptor["capabilities"]
    assert "inference.structured_json" in descriptor["capabilities"]


def test_gemini_verifier_uses_google_api_key_header_and_normalizes_models():
    opener = FakeOpener({
        "models": [
            {
                "name": "models/gemini-3.8-flash",
                "supportedGenerationMethods": [
                    "generateContent", "countTokens",
                ],
            },
            {
                "name": "models/gemini-embedding-2",
                "supportedGenerationMethods": ["embedContent"],
            },
            {
                "name": "models/gemini-3.6-flash",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/not-gemini",
                "supportedGenerationMethods": ["generateContent"],
            },
        ]
    })
    verifier = GeminiConnectionVerifier(opener=opener)

    observed = verifier.inspect("GEMINI-PRIVATE")

    assert observed == {
        "availability": "available",
        "available_models": [
            {"id": "gemini-3.6-flash", "lifecycle": "available"},
            {"id": "gemini-3.8-flash", "lifecycle": "available"},
        ],
    }
    request, timeout = opener.requests[0]
    assert request.full_url == (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models?pageSize=1000"
    )
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers["x-goog-api-key"] == "GEMINI-PRIVATE"
    assert timeout == 10.0


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "AUTHENTICATION_FAILED"),
        (401, "AUTHENTICATION_FAILED"),
        (403, "EXTERNAL_PERMISSION_INSUFFICIENT"),
        (429, "RATE_LIMITED"),
        (503, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_gemini_verifier_normalizes_http_failures(status, code):
    error = HTTPError(
        "https://generativelanguage.googleapis.com/v1beta/models",
        status,
        "failure",
        {},
        io.BytesIO(b"{}"),
    )
    verifier = GeminiConnectionVerifier(opener=FakeOpener(error=error))

    with pytest.raises(AIConnectionVerificationError, match=code):
        verifier.inspect("PRIVATE")


def test_gemini_connection_secret_is_not_persisted_and_models_are_verified(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    store = ConnectionStore(path)
    vault = FakeVault()
    manager = ConnectionManager(store, vault)

    created = manager.create_ai(
        "gemini", "GEMINI-PRIVATE", label="Gemini principal",
    )
    assert created["provider_id"] == "gemini"
    assert created["enabled"] is False
    assert created["configured"] is True
    assert b"GEMINI-PRIVATE" not in path.read_bytes()

    class Verifier:
        def inspect(self, secret):
            assert secret == "GEMINI-PRIVATE"
            return {
                "availability": "available",
                "available_models": [
                    {"id": "gemini-3.8-flash", "lifecycle": "available"},
                ],
            }

    manager._ai_verifiers["gemini"] = Verifier()
    verified = manager.verify_ai(created["id"])
    assert verified["availability"] == "available"
    assert verified["configuration"]["observed_models"] == [
        "gemini-3.8-flash"
    ]

    manager.set_enabled(created["id"], True)
    resolved, secret = manager.resolve_ai_connection(
        provider_id="gemini",
        connection_id=created["id"],
        model_id="gemini-3.8-flash",
    )
    assert resolved["id"] == created["id"]
    assert secret == "GEMINI-PRIVATE"
    assert "GEMINI-PRIVATE" not in json.dumps(resolved)


def test_gemini_profile_resolves_without_provider_specific_runtime(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    store = ConnectionStore(path)
    vault = FakeVault()
    manager = ConnectionManager(store, vault)
    connection = manager.create_ai("gemini", "PRIVATE")
    store.update_configuration(
        connection["id"],
        {
            "observed_models": ["gemini-3.8-flash"],
        },
    )
    store.record_inspection(
        connection["id"],
        display_identity=None,
        external_account_ref=None,
        observed_permissions=[],
        availability="available",
        error_code=None,
    )
    manager.set_enabled(connection["id"], True)

    profiles = InferenceProfileStore(path)
    profile = profiles.create_profile(
        "gemini-general",
        "Gemini General",
        connection_id=connection["id"],
        model="gemini-3.8-flash",
        requirements={
            "streaming": True,
            "structured_output": True,
        },
    )
    profiles.bind(profile["id"], scope_type="global")

    plan = InferenceResolver(profiles, store).resolve(
        InferenceResolutionContext()
    )
    assert plan.provider_id == "gemini"
    assert plan.connection_id == connection["id"]
    assert plan.model == "gemini-3.8-flash"


def test_factory_builds_gemini_through_single_litellm_adapter():
    provider = build_inference_provider(
        "gemini", "PRIVATE", backend="litellm",
    )

    assert isinstance(provider, LiteLLMInferenceAdapter)
    assert provider.provider_id == "gemini"
    assert provider.litellm_prefix == "gemini"
    assert provider._model("gemini-3.8-flash") == (
        "gemini/gemini-3.8-flash"
    )


def test_no_gemini_specific_inference_adapter_exists():
    adapters = Path(__file__).resolve().parents[1] / "src" / "jarvis" / "adapters"
    forbidden = [
        path.name
        for path in adapters.glob("*gemini*")
        if path.is_file()
    ]
    assert forbidden == []

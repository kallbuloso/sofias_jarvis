"""Offline TB-02 connection tests; no requests to live production services."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError

import pytest

from jarvis.memory.connection import (
    MemoryConfigurationError, REQUIRED_CAPABILITIES,
    SofiasMemoryConnection, configured_memory_url, save_memory_url,
    validate_memory_url,
)

ORIGIN = "https://pefil-sofias-memory.q8cqqr.easypanel.host"


class FakeResponse:
    status = 200

    def __init__(self, value):
        self.content = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size):
        return self.content[:size]


class FakeOpener:
    def __init__(self, *, info=None, error=None):
        self.calls = []
        self.info = info
        self.error = error

    def open(self, request, timeout):
        self.calls.append((request.full_url, dict(request.header_items()), timeout))
        if self.error is not None:
            raise self.error
        if request.full_url.endswith("/api/v1/info"):
            return FakeResponse(self.info)
        return FakeResponse({"status": "ok"})


def valid_info(**overrides):
    data = {
        "name": "Sofias Memory", "version": "0.7.0", "api_contract_version": "1",
        "contracts": {"cognitive_memory": "1"},
        "capabilities": sorted(REQUIRED_CAPABILITIES),
    }
    data.update(overrides)
    return {"data": data, "meta": {"request_id": "opaque"}}


def test_validation_accepts_only_https_origin():
    assert validate_memory_url(ORIGIN + "/") == ORIGIN
    for bad in (
        "http://example.com", "https://example.com/docs", "https://example.com?a=b",
        "https://user:pass@example.com", "https://example.com/#fragment",
        "https://example.com:abc", "https://example.com\r\nX-API-Key: foo",
        " https://example.com", "", "file:///etc/passwd", "https://example.com:0",
    ):
        with pytest.raises(MemoryConfigurationError):
            validate_memory_url(bad)


def test_settings_store_only_origin_and_environment_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MEMORY_URL", raising=False)
    assert configured_memory_url() is None
    assert save_memory_url(ORIGIN + "/") == ORIGIN
    assert configured_memory_url() == ORIGIN
    contents = (tmp_path / "memory_connection.json").read_text()
    assert "key" not in contents
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://another.example")
    assert configured_memory_url() == "https://another.example"


def test_incompatible_saved_settings_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MEMORY_URL", raising=False)
    (tmp_path / "memory_connection.json").write_text("invalid json")
    with pytest.raises(MemoryConfigurationError):
        configured_memory_url()


def test_connection_success_and_key_only_on_protected_endpoint():
    fake = FakeOpener(info=valid_info())
    client = SofiasMemoryConnection(ORIGIN, "never-echo-this", opener=fake)
    result = client.diagnose()
    assert result["status"] == "COMPATIBLE"
    assert result["service_version"] == "0.7.0"
    assert not result["missing_capabilities"]
    assert len(fake.calls) == 3
    assert "x-api-key" not in {k.lower() for k in fake.calls[0][1]}
    assert "x-api-key" not in {k.lower() for k in fake.calls[1][1]}
    assert any(k.lower() == "x-api-key" for k in fake.calls[2][1])
    assert "never-echo-this" not in json.dumps(result)


def test_contract_incompatibility_is_not_success():
    fake = FakeOpener(info=valid_info(api_contract_version="2"))
    assert SofiasMemoryConnection(ORIGIN, "key", opener=fake).diagnose()["status"] == "CONTRACT_INCOMPATIBLE"


def test_missing_capability_is_not_silently_accepted():
    subset = sorted(REQUIRED_CAPABILITIES - {"cognitive_memory.forget"})
    fake = FakeOpener(info=valid_info(capabilities=subset))
    result = SofiasMemoryConnection(ORIGIN, "key", opener=fake).diagnose()
    assert result["status"] == "CAPABILITIES_MISSING"
    assert result["missing_capabilities"] == ["cognitive_memory.forget"]


def test_malformed_envelope_rejected():
    fake = FakeOpener(info={"no_data": True})
    assert SofiasMemoryConnection(ORIGIN, "key", opener=fake).diagnose()["status"] == "INCOMPATIBLE_RESPONSE"


@pytest.mark.parametrize("code,expected", [
    (401, "AUTH_REJECTED"), (403, "AUTH_REJECTED"),
    (302, "REDIRECT_BLOCKED"), (503, "SERVICE_UNAVAILABLE"),
    (404, "HTTP_FAILED"),
])
def test_http_errors_are_sanitized(code, expected):
    fake = FakeOpener(error=HTTPError(ORIGIN, code, "secret in body", None, None))
    result = SofiasMemoryConnection(ORIGIN, "key", opener=fake).diagnose()
    assert result["status"] == expected
    assert "secret" not in json.dumps(result)


def test_network_unavailable_is_not_empty_recall():
    fake = FakeOpener(error=URLError("private endpoint error"))
    assert SofiasMemoryConnection(ORIGIN, "key", opener=fake).diagnose()["status"] == "SERVICE_UNAVAILABLE"


def test_empty_key_rejected():
    with pytest.raises(MemoryConfigurationError):
        SofiasMemoryConnection(ORIGIN, "  ")

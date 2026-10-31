"""TB-02 connection negotiation, with no memory writes or hidden retries.

Only a configured HTTPS origin is accepted. All requests remain in Python;
redirects are blocked so X-API-Key is never forwarded to another origin.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from jarvis.config import data_directory

REQUIRED_CAPABILITIES = frozenset({
    "cognitive_memory.write",
    "cognitive_memory.get",
    "cognitive_memory.recall",
    "cognitive_memory.supersede",
    "cognitive_memory.forget",
})
_MAX_RESPONSE_BYTES = 65_536
_TIMEOUT_SECONDS = 8.0


class MemoryConfigurationError(ValueError):
    """URL or saved connection settings are invalid."""


class MemoryTransportError(RuntimeError):
    """Stable non-secret failure type suitable for UI/CLI display."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_memory_url(url: str) -> str:
    """Accept only an HTTPS origin, with no embedded credentials or path."""
    if not isinstance(url, str) or not url or url != url.strip():
        raise MemoryConfigurationError("invalid_memory_url")
    if any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise MemoryConfigurationError("invalid_memory_url")
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or not parsed.netloc or parsed.port == 0):
            raise MemoryConfigurationError("invalid_memory_url")
    except ValueError as exc:
        raise MemoryConfigurationError("invalid_memory_url") from exc
    return f"https://{parsed.netloc}"


def memory_settings_path() -> Path:
    return data_directory() / "memory_connection.json"


def save_memory_url(url: str) -> str:
    """Persist only the URL, atomically. Credentials never enter this file."""
    normalized = validate_memory_url(url)
    target = memory_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=".memory-", suffix=".tmp", delete=False,
        ) as f:
            temp_name = f.name
            json.dump({"url": normalized}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, target)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return normalized


def configured_memory_url() -> str | None:
    """An explicit JARVIS_MEMORY_URL overrides persisted non-secret settings."""
    env = os.environ.get("JARVIS_MEMORY_URL")
    if env is not None:
        return validate_memory_url(env)
    target = memory_settings_path()
    if not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("url"), str):
            raise MemoryConfigurationError("invalid_saved_memory_settings")
        return validate_memory_url(payload["url"])
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MemoryConfigurationError("invalid_saved_memory_settings") from exc


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SofiasMemoryConnection:
    """Read-only connectivity check; no cognitive API mutations."""

    def __init__(self, base_url: str, api_key: str, *, opener: Any = None):
        self.base_url = validate_memory_url(base_url)
        if not api_key or not api_key.strip():
            raise MemoryConfigurationError("memory_key_missing")
        self._api_key = api_key
        self._opener = opener if opener is not None else build_opener(_NoRedirect())

    def _get(self, path: str, *, authenticated: bool) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["X-API-Key"] = self._api_key
        request = Request(f"{self.base_url}{path}", headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
                if not 200 <= response.status < 300:
                    raise MemoryTransportError("HTTP_FAILED")
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                raise MemoryTransportError("REDIRECT_BLOCKED") from None
            if exc.code in (401, 403):
                raise MemoryTransportError("AUTH_REJECTED") from None
            if exc.code in (502, 503, 504):
                raise MemoryTransportError("SERVICE_UNAVAILABLE") from None
            raise MemoryTransportError("HTTP_FAILED") from None
        except (OSError, URLError, TimeoutError):
            raise MemoryTransportError("SERVICE_UNAVAILABLE") from None
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise MemoryTransportError("RESPONSE_TOO_LARGE")
        try:
            decoded = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MemoryTransportError("INVALID_RESPONSE") from None
        if not isinstance(decoded, dict):
            raise MemoryTransportError("INVALID_RESPONSE")
        return decoded

    def diagnose(self) -> dict[str, Any]:
        """Report only safe operational data, never the key or response body."""
        result: dict[str, Any] = {
            "status": "UNAVAILABLE",
            "url": self.base_url,
            "service_version": None,
            "api_contract_version": None,
            "cognitive_memory_contract": None,
            "capabilities": [],
            "missing_capabilities": sorted(REQUIRED_CAPABILITIES),
        }
        try:
            self._get("/health/live", authenticated=False)
            self._get("/health/ready", authenticated=False)
            info = self._get("/api/v1/info", authenticated=True)
        except MemoryTransportError as exc:
            result["status"] = exc.code
            return result
        data = info.get("data")
        if not isinstance(data, dict):
            result["status"] = "INCOMPATIBLE_RESPONSE"
            return result
        contracts = data.get("contracts")
        capabilities = data.get("capabilities")
        if (not isinstance(contracts, dict) or not isinstance(capabilities, list)
                or not all(isinstance(x, str) for x in capabilities)):
            result["status"] = "INCOMPATIBLE_RESPONSE"
            return result
        version = data.get("version")
        api_version = data.get("api_contract_version")
        cognitive_version = contracts.get("cognitive_memory")
        actual = set(capabilities)
        result.update({
            "service_version": version if isinstance(version, str) else None,
            "api_contract_version": api_version if isinstance(api_version, str) else None,
            "cognitive_memory_contract": cognitive_version if isinstance(cognitive_version, str) else None,
            "capabilities": sorted(actual & REQUIRED_CAPABILITIES),
            "missing_capabilities": sorted(REQUIRED_CAPABILITIES - actual),
        })
        if api_version != "1" or cognitive_version != "1":
            result["status"] = "CONTRACT_INCOMPATIBLE"
        elif REQUIRED_CAPABILITIES - actual:
            result["status"] = "CAPABILITIES_MISSING"
        else:
            result["status"] = "COMPATIBLE"
        return result

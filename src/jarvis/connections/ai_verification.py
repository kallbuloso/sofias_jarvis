"""Cheap, non-inference verification for AI provider credentials."""
from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


_MAX_RESPONSE_BYTES = 262_144
_TIMEOUT_SECONDS = 10.0
_ANTHROPIC_VERSION = "2026-10-21"


class AIConnectionVerificationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AnthropicConnectionVerifier:
    """Authenticate a key by listing accessible models without inference."""

    def __init__(self, *, opener: Any = None):
        self._opener = opener if opener is not None else build_opener(_NoRedirect())

    def inspect(self, api_key: str) -> dict:
        if not isinstance(api_key, str) or not api_key.strip():
            raise AIConnectionVerificationError("AUTHENTICATION_REQUIRED")

        request = Request(
            "https://api.anthropic.com/v1/models?limit=100",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key.strip()}",
                "anthropic-version": _ANTHROPIC_VERSION,
                "User-Agent": "sofias-jarvis",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code == 401:
                raise AIConnectionVerificationError("AUTHENTICATION_FAILED") from None
            if exc.code == 403:
                raise AIConnectionVerificationError(
                    "EXTERNAL_PERMISSION_INSUFFICIENT"
                ) from None
            if exc.code == 429:
                raise AIConnectionVerificationError("RATE_LIMITED") from None
            if exc.code in (500, 502, 503, 504):
                raise AIConnectionVerificationError("PROVIDER_UNAVAILABLE") from None
            raise AIConnectionVerificationError("CONNECTION_UNAVAILABLE") from None
        except (OSError, URLError, TimeoutError):
            raise AIConnectionVerificationError("PROVIDER_UNAVAILABLE") from None

        if len(raw) > _MAX_RESPONSE_BYTES:
            raise AIConnectionVerificationError("INVALID_RESPONSE")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise AIConnectionVerificationError("INVALID_RESPONSE") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise AIConnectionVerificationError("INVALID_RESPONSE")

        models = []
        for item in payload["data"]:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id")
            lifecycle = item.get("lifecycle")
            if isinstance(model_id, str) and model_id:
                models.append({
                    "id": model_id,
                    "lifecycle": lifecycle if isinstance(lifecycle, str) else None,
                })

        if not models:
            raise AIConnectionVerificationError("NO_MODELS_AVAILABLE")

        return {
            "availability": "available",
            "available_models": models,
        }

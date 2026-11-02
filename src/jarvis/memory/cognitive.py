"""Explicit cognitive operations for Sofias Memory API contract 1.

Ordinary chat never becomes durable memory by importing this client.
All mutations require a caller-owned idempotency key; uncertain outcomes
must be reconciled, not retried with a newly generated key.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request
from uuid import UUID

from jarvis.memory.connection import SofiasMemoryConnection

_MAX_COGNITIVE_RESPONSE = 1024 * 1024
_SCOPE = re.compile(r"(?:global|project:[a-z0-9._-]{1,128})\Z")
_TYPE = frozenset({"profile", "semantic"})
_ORIGINS = frozenset({"user_asserted", "tool_observed", "imported", "inferred", "assistant_generated"})
_PROVENANCE_FIELDS = frozenset({
    "origin_kind", "source_system", "conversation_uuid", "turn_uuid", "task_uuid",
    "confirmation_ref", "source_ref", "observed_at",
})
_HTTP_CODES = frozenset({
    "INVALID_REQUEST", "MEMORY_NOT_FOUND", "MEMORY_STATE_CONFLICT",
    "IDEMPOTENCY_CONFLICT", "RESERVED_IDEMPOTENCY_KEY_NAMESPACE",
    "DEPENDENCY_UNAVAILABLE", "MISSING_API_KEY", "INVALID_API_KEY",
})


class CognitiveMemoryError(RuntimeError):
    """A safe error code, with optional caller-owned operation reference."""

    def __init__(self, code: str, *, operation_key: str | None = None):
        self.code = code
        self.operation_key = operation_key
        super().__init__(code)


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("invalid_uuid") from exc


def _scope(scope: str) -> str:
    if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
        raise ValueError("invalid_scope")
    return scope


def _payload(content: str, provenance: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 16384:
        raise ValueError("invalid_content")
    if not isinstance(provenance, Mapping):
        raise ValueError("invalid_provenance")
    if set(provenance) - _PROVENANCE_FIELDS:
        raise ValueError("unexpected_provenance_fields")
    origin = provenance.get("origin_kind")
    system = provenance.get("source_system")
    if not isinstance(origin, str) or origin not in _ORIGINS or system != "jarvis":
        raise ValueError("invalid_provenance")
    if origin == "user_asserted" and not (provenance.get("turn_uuid") or provenance.get("source_ref")):
        raise ValueError("provenance_requires_turn_or_source")
    if origin == "tool_observed" and not (provenance.get("source_ref") and provenance.get("observed_at")):
        raise ValueError("provenance_requires_source_and_time")
    if origin == "imported" and not provenance.get("source_ref"):
        raise ValueError("provenance_requires_source")
    if origin in {"inferred", "assistant_generated"} and not any(
        provenance.get(field) for field in ("turn_uuid", "task_uuid", "source_ref")
    ):
        raise ValueError("provenance_requires_reference")
    confidence = extra.get("confidence")
    if confidence is not None and (
        isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1
    ):
        raise ValueError("invalid_confidence")
    if origin == "inferred" and confidence is None:
        raise ValueError("inference_requires_confidence")
    if set(extra) - {"confidence", "valid_from", "valid_until"}:
        raise ValueError("unexpected_payload_fields")
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    result = {"content": normalized, "provenance": dict(provenance)}
    result.update(extra)
    for ref in ("turn_uuid", "conversation_uuid", "task_uuid"):
        if result["provenance"].get(ref) is not None:
            result["provenance"][ref] = _uuid(result["provenance"][ref])
    return result


def _memory_item(data: Any, *, expected_id: str | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("invalid_memory_item")
    memory_id = _uuid(data.get("memory_id"))
    if expected_id is not None and memory_id != expected_id:
        raise ValueError("unexpected_memory_identity")
    if data.get("memory_type") not in _TYPE:
        raise ValueError("invalid_memory_type")
    lifecycle = data.get("lifecycle")
    if lifecycle not in {"active", "superseded", "forgotten"}:
        raise ValueError("invalid_lifecycle")
    if lifecycle == "forgotten":
        if data.get("content") is not None or data.get("scope") is not None:
            raise ValueError("forgotten_memory_exposed")
    else:
        if not isinstance(data.get("content"), str) or not data["content"]:
            raise ValueError("invalid_memory_content")
        _scope(data.get("scope"))
    if not isinstance(data.get("provenance"), dict) or not isinstance(data["provenance"].get("source_system"), str):
        raise ValueError("invalid_memory_provenance")
    return data


class CognitiveMemoryClient(SofiasMemoryConnection):
    """HTTP adapter only; JARVIS caller owns consent, scope and operation journal."""

    def _json_request(
        self, method: str, path: str, *, payload: dict[str, Any] | None = None,
        operation_key: str | None = None,
    ) -> Any:
        mutation = method == "POST" and path != "/api/v1/memories/recall"
        headers = {"Accept": "application/json", "X-API-Key": self._api_key}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if operation_key is not None:
            headers["Idempotency-Key"] = operation_key
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=15.0) as response:
                expected = 201 if path == "/api/v1/memories" else 200
                if response.status != expected:
                    raise CognitiveMemoryError("RESULT_UNKNOWN" if mutation else "INCOMPATIBLE_RESPONSE", operation_key=operation_key)
                raw = response.read(_MAX_COGNITIVE_RESPONSE + 1)
        except HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                raise CognitiveMemoryError("REDIRECT_BLOCKED", operation_key=operation_key) from None
            if exc.code in (401, 403):
                raise CognitiveMemoryError("AUTH_REJECTED", operation_key=operation_key) from None
            if exc.code in (400, 404, 409, 422):
                try:
                    err = json.loads(exc.read(8193))
                    code = err.get("error", {}).get("code")
                    if isinstance(code, str) and code in _HTTP_CODES:
                        raise CognitiveMemoryError(code, operation_key=operation_key)
                except (ValueError, AttributeError, TypeError, OSError):
                    pass
                raise CognitiveMemoryError("HTTP_REJECTED", operation_key=operation_key) from None
            raise CognitiveMemoryError("RESULT_UNKNOWN" if mutation else "SERVICE_UNAVAILABLE", operation_key=operation_key) from None
        except (OSError, URLError, TimeoutError):
            raise CognitiveMemoryError("RESULT_UNKNOWN" if mutation else "SERVICE_UNAVAILABLE", operation_key=operation_key) from None
        if len(raw) > _MAX_COGNITIVE_RESPONSE:
            raise CognitiveMemoryError("RESULT_UNKNOWN" if mutation else "RESPONSE_TOO_LARGE", operation_key=operation_key)
        try:
            envelope = json.loads(raw)
            if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
                raise ValueError("invalid_envelope")
            return envelope["data"]
        except (ValueError, UnicodeError):
            raise CognitiveMemoryError("RESULT_UNKNOWN" if mutation else "INCOMPATIBLE_RESPONSE", operation_key=operation_key) from None

    def create(
        self, *, memory_type: str, scope: str, content: str,
        provenance: Mapping[str, Any], idempotency_key: str,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        if memory_type not in _TYPE:
            raise ValueError("invalid_memory_type")
        payload = _payload(content, provenance, confidence=confidence)
        payload.update(memory_type=memory_type, scope=_scope(scope))
        key = _uuid(idempotency_key)
        data = self._json_request("POST", "/api/v1/memories", payload=payload, operation_key=key)
        try:
            item = _memory_item(data)
            if item["lifecycle"] != "active" or item["memory_type"] != memory_type or item["scope"] != scope:
                raise ValueError("unexpected_creation")
            return item
        except ValueError:
            raise CognitiveMemoryError("RESULT_UNKNOWN", operation_key=key) from None

    def get(self, memory_id: str) -> dict[str, Any]:
        memory_id = _uuid(memory_id)
        data = self._json_request("GET", f"/api/v1/memories/{memory_id}")
        try:
            return _memory_item(data, expected_id=memory_id)
        except ValueError:
            raise CognitiveMemoryError("INCOMPATIBLE_RESPONSE") from None

    def recall(
        self, *, query: str, scopes: list[str], top_k: int = 10,
        include_superseded: bool = False,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 8192:
            raise ValueError("invalid_query")
        if not isinstance(scopes, list) or not 1 <= len(scopes) <= 16:
            raise ValueError("invalid_scopes")
        scopes = list(dict.fromkeys(_scope(s) for s in scopes))
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 50:
            raise ValueError("invalid_top_k")
        if not isinstance(include_superseded, bool):
            raise ValueError("invalid_historical_flag")
        payload = {"query": query.strip(), "scopes": scopes, "top_k": top_k,
                   "include_superseded": include_superseded}
        data = self._json_request("POST", "/api/v1/memories/recall", payload=payload)
        try:
            items = data.get("items")
            if not isinstance(items, list) or len(items) > top_k:
                raise ValueError("invalid_items")
            for hit in items:
                if not isinstance(hit, dict) or not isinstance(hit.get("is_current_truth"), bool):
                    raise ValueError("invalid_hit")
                relevance = hit.get("relevance")
                if isinstance(relevance, bool) or not isinstance(relevance, (int, float)) or not -1 <= relevance <= 1:
                    raise ValueError("invalid_relevance")
                memory = _memory_item(hit.get("memory"))
                if memory["lifecycle"] == "forgotten" or memory["scope"] not in scopes:
                    raise ValueError("invalid_recall_scope_or_state")
                if not include_superseded and not hit["is_current_truth"]:
                    raise ValueError("inactive_recall")
            return items
        except ValueError:
            raise CognitiveMemoryError("INCOMPATIBLE_RESPONSE") from None

    def supersede(
        self, memory_id: str, *, content: str, provenance: Mapping[str, Any],
        idempotency_key: str, confidence: float | None = None,
    ) -> dict[str, Any]:
        memory_id = _uuid(memory_id)
        payload = _payload(content, provenance, confidence=confidence)
        key = _uuid(idempotency_key)
        data = self._json_request("POST", f"/api/v1/memories/{memory_id}/supersede", payload=payload, operation_key=key)
        try:
            old = _memory_item(data.get("old"), expected_id=memory_id)
            replacement = _memory_item(data.get("replacement"))
            if (old["lifecycle"] != "superseded" or replacement["lifecycle"] != "active"
                    or old["superseded_by"] != replacement["memory_id"]
                    or old["scope"] != replacement["scope"]
                    or old["memory_type"] != replacement["memory_type"]):
                raise ValueError("unexpected_supersede")
            return data
        except (ValueError, KeyError):
            raise CognitiveMemoryError("RESULT_UNKNOWN", operation_key=key) from None

    def forget(self, memory_id: str, *, idempotency_key: str) -> dict[str, Any]:
        memory_id = _uuid(memory_id)
        key = _uuid(idempotency_key)
        data = self._json_request("POST", f"/api/v1/memories/{memory_id}/forget", operation_key=key)
        try:
            item = _memory_item(data, expected_id=memory_id)
            if item["lifecycle"] != "forgotten":
                raise ValueError("not_forgotten")
            return item
        except ValueError:
            raise CognitiveMemoryError("RESULT_UNKNOWN", operation_key=key) from None

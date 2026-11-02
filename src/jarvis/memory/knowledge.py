"""Sofias Memory Knowledge Retrieval adapter (API contract 1).

Different from Cognitive Memory. Explicit dataset slugs; mode=chunks only;
the server persists a Query audit record, but performs no memory writes,
dataset changes, or LLM answer generation. Evidence is never invented.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request
from uuid import UUID

from jarvis.memory.connection import SofiasMemoryConnection

_MAX_RESPONSE = 2 * 1024 * 1024
_SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?\Z")


class KnowledgeError(RuntimeError):
    """Sanitized error status for UI and CLI; no raw headers or response body."""


def _dataset_slug(value: str) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value) or len(value) > 120:
        raise ValueError("invalid_dataset_slug")
    return value


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise KnowledgeError("INCOMPATIBLE_RESPONSE") from exc


def _score(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise KnowledgeError("INCOMPATIBLE_RESPONSE")
    return float(value)


class KnowledgeClient(SofiasMemoryConnection):
    """HTTP interface for explicit dataset listing and chunk-only retrieval."""

    def _request(self, method: str, path: str, *, body: dict | None = None,
                 accepted_status: tuple[int, ...] = (200,)) -> dict:
        headers = {"Accept": "application/json", "X-API-Key": self._api_key}
        encoded = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        request = Request(self.base_url + path, data=encoded, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=20.0) as response:
                if response.status not in accepted_status:
                    raise KnowledgeError("HTTP_FAILED")
                raw = response.read(_MAX_RESPONSE + 1)
        except HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                raise KnowledgeError("REDIRECT_BLOCKED") from None
            if exc.code in (401, 403):
                raise KnowledgeError("AUTH_REJECTED") from None
            if exc.code == 404:
                raise KnowledgeError("DATASET_NOT_FOUND") from None
            if exc.code in (400, 422):
                raise KnowledgeError("INVALID_REQUEST") from None
            if exc.code in (502, 503, 504):
                raise KnowledgeError("SERVICE_UNAVAILABLE") from None
            raise KnowledgeError("HTTP_FAILED") from None
        except (OSError, URLError, TimeoutError):
            raise KnowledgeError("SERVICE_UNAVAILABLE") from None
        if len(raw) > _MAX_RESPONSE:
            raise KnowledgeError("RESPONSE_TOO_LARGE")
        try:
            envelope = json.loads(raw)
        except (ValueError, UnicodeError):
            raise KnowledgeError("INCOMPATIBLE_RESPONSE") from None
        if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        return envelope["data"]

    def list_datasets(self, *, limit: int = 50, offset: int = 0) -> dict:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("invalid_dataset_limit")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("invalid_dataset_offset")
        data = self._request("GET", f"/api/v1/datasets?limit={limit}&offset={offset}")
        items = data.get("items")
        total = data.get("total")
        if (not isinstance(items, list) or len(items) > limit
                or isinstance(total, bool) or not isinstance(total, int) or total < 0):
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        public = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            slug = item.get("slug")
            try:
                slug = _dataset_slug(slug)
            except ValueError:
                raise KnowledgeError("INCOMPATIBLE_RESPONSE") from None
            public.append({
                "dataset_id": _uuid(item.get("dataset_id")),
                "slug": slug,
                "name": item["name"],
                "status": item.get("status"),
            })
        return {"items": public, "total": total, "limit": limit, "offset": offset}

    def query_chunks(self, *, query: str, datasets: list[str], top_k: int = 5) -> dict:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4000:
            raise ValueError("invalid_knowledge_query")
        if not isinstance(datasets, list) or not 1 <= len(datasets) <= 8:
            raise ValueError("explicit_datasets_required")
        unique = list(dict.fromkeys(_dataset_slug(v) for v in datasets))
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 10:
            raise ValueError("invalid_top_k")
        data = self._request("POST", "/api/v1/recall", body={
            "query": query.strip(),
            "datasets": unique,
            "mode": "chunks",
            "top_k": top_k,
            "only_context": True,
            "include_references": True,
            "include_session_context": False,
        })
        if data.get("mode") != "chunks" or data.get("answer") is not None:
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        contexts = data.get("context")
        refs = data.get("references")
        if (not isinstance(contexts, list) or len(contexts) > top_k
                or not isinstance(refs, list)):
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        query_id = _uuid(data.get("query_id"))
        context = []
        for item in contexts:
            if not isinstance(item, dict):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            ids = {name: _uuid(item.get(name)) for name in
                   ("chunk_id", "source_id", "document_id", "dataset_id")}
            if (not isinstance(item.get("text"), str)
                    or not isinstance(item.get("source_name"), str)):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            context.append({
                **ids, "text": item["text"], "source_name": item["source_name"],
                "score": _score(item.get("score")),
                "chunk_ordinal": item.get("chunk_ordinal"),
            })
        # A returned reference must refer to a retrieved chunk; a source URL
        # may be absent. Never fabricate a citation when references are empty.
        matches = {(x["source_id"], x["document_id"], x["chunk_id"]) for x in context}
        references = []
        for item in refs:
            if not isinstance(item, dict):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            ids = {name: _uuid(item.get(name)) for name in
                   ("source_id", "document_id", "chunk_id")}
            if tuple(ids.values()) not in matches:
                raise KnowledgeError("INCOMPATIBLE_REFERENCE")
            if not isinstance(item.get("quote"), str) or not isinstance(item.get("source_name"), str):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            url = item.get("url")
            if url is not None and not isinstance(url, str):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            references.append({
                **ids, "quote": item["quote"],
                "source_name": item["source_name"],
                "url": url, "score": _score(item.get("score")),
            })
        return {
            "status": "RESULTS_FOUND" if context else "NO_RESULTS",
            "query_id": query_id,
            "mode": "chunks",
            "datasets": unique,
            "context": context,
            "references": references,
        }

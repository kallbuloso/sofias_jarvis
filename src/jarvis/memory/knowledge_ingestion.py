"""Strict TB-02 document ingestion flow for one approved JARVIS ADR.

This is Knowledge, not Cognitive Memory. No generic ingestion surface is
exported by the CLI. Mutations require user confirmation before dispatch.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from jarvis.memory.knowledge import KnowledgeClient, KnowledgeError

DATASET_SLUG = "jarvis-knowledge"
DATASET_NAME = "JARVIS Knowledge"
DATASET_DESCRIPTION = "Documentos aprovados de arquitetura do JARVIS (TB-02)."
SOURCE_NAME = "JARVIS ADR-0001 — Modular Monolith"
SOURCE_REL_PATH = "docs/product-manager/07-JARVIS-ADRs.md"
SOURCE_URL = (
    "https://github.com/kallbuloso/sofias_jarvis/blob/"
    "76e06ab6edb78461c1a9ca5469acd0ab3c3dd26b/"
    "docs/product-manager/07-JARVIS-ADRs.md"
)
_START = "# ADR-0001 — Modular Monolith as the JARVIS Core Architecture"
_END = "# ADR-0002 — Operational Persistence & Recovery"
_RUN_STATES = frozenset({
    "queued", "running", "succeeded", "failed", "cancelling", "cancelled",
})


def _uuid(value) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise KnowledgeError("INCOMPATIBLE_RESPONSE") from None


def approved_adr(root: Path | None = None) -> dict:
    """Extract exact accepted ADR-0001 text from the checked-out source file."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    path = (project_root / SOURCE_REL_PATH).resolve()
    if not path.is_file():
        raise KnowledgeError("ADR_SOURCE_NOT_FOUND")
    if path.stat().st_size > 50_000:
        raise KnowledgeError("ADR_SOURCE_TOO_LARGE")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise KnowledgeError("ADR_SOURCE_UNREADABLE") from None
    lines = text.splitlines(keepends=True)
    start = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == _START]
    end = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == _END]
    if len(start) != 1 or len(end) != 1 or end[0] <= start[0]:
        raise KnowledgeError("ADR_SOURCE_INCOMPATIBLE")
    content = "".join(lines[start[0]:end[0]]).rstrip()
    if content.endswith("---"):
        content = content[:-3].rstrip()
    if (not content.startswith(_START)
            or "**Status:** ACCEPTED" not in content
            or len(content.encode("utf-8")) > 15_000
            or "# ADR-0002" in content):
        raise KnowledgeError("ADR_SOURCE_INCOMPATIBLE")
    return {
        "content": content,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "name": SOURCE_NAME,
        "source_path": SOURCE_REL_PATH,
        "source_url": SOURCE_URL,
    }


class ADRKnowledgeClient(KnowledgeClient):
    """Never silently re-create, overwrite, retry or force-ingest an ADR."""

    def _dataset(self, *, required: bool) -> dict | None:
        offset = 0
        found = []
        while True:
            page = self.list_datasets(limit=100, offset=offset)
            found += [item for item in page["items"] if item["slug"] == DATASET_SLUG]
            offset += len(page["items"])
            if offset >= page["total"]:
                break
            if not page["items"]:
                raise KnowledgeError("INVALID_DATASET_PAGINATION")
        if len(found) > 1:
            raise KnowledgeError("DUPLICATE_DATASET_SLUG")
        if found:
            if found[0]["status"] != "active":
                raise KnowledgeError("DATASET_NOT_ACTIVE")
            if found[0]["name"] != DATASET_NAME:
                raise KnowledgeError("DATASET_IDENTITY_MISMATCH")
            return found[0]
        if required:
            raise KnowledgeError("DATASET_NOT_FOUND")
        return None

    def create_adr_dataset(self) -> dict:
        existing = self._dataset(required=False)
        if existing:
            return {"status": "ALREADY_EXISTS", **existing}
        data = self._request(
            "POST", "/api/v1/datasets",
            body={"name": DATASET_NAME, "description": DATASET_DESCRIPTION,
                  "slug": DATASET_SLUG},
            accepted_status=(201,),
        )
        if (data.get("slug") != DATASET_SLUG
                or data.get("name") != DATASET_NAME
                or data.get("status") != "active"):
            raise KnowledgeError("RESULT_UNKNOWN")
        return {"status": "CREATED", "dataset_id": _uuid(data.get("dataset_id")),
                "slug": DATASET_SLUG, "name": DATASET_NAME}

    def _sources(self, dataset_id: str) -> list[dict]:
        items = []
        offset = 0
        while True:
            data = self._request(
                "GET", f"/api/v1/datasets/{_uuid(dataset_id)}/sources"
                       f"?limit=100&offset={offset}",
            )
            rows = data.get("items")
            total = data.get("total")
            if (not isinstance(rows, list) or isinstance(total, bool)
                    or not isinstance(total, int) or total < 0
                    or len(rows) > 100):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            items.extend(rows)
            offset += len(rows)
            if offset >= total:
                break
            if not rows:
                raise KnowledgeError("INVALID_SOURCE_PAGINATION")
        return items

    def ingest_adr(self, adr: dict) -> dict:
        dataset = self._dataset(required=True)
        expected_hash = adr["sha256"]
        if (not isinstance(expected_hash, str) or len(expected_hash) != 64
                or hashlib.sha256(adr["content"].encode("utf-8")).hexdigest()
                != expected_hash):
            raise KnowledgeError("ADR_CONTENT_MISMATCH")
        for item in self._sources(dataset["dataset_id"]):
            if not isinstance(item, dict):
                raise KnowledgeError("INCOMPATIBLE_RESPONSE")
            metadata = item.get("metadata")
            if item.get("name") == SOURCE_NAME or (
                isinstance(metadata, dict)
                and metadata.get("adr_id") == "ADR-0001"
            ):
                if (not isinstance(metadata, dict)
                        or metadata.get("source_sha256") != expected_hash):
                    raise KnowledgeError("ADR_SOURCE_CONFLICT")
                return {
                    "status": "SOURCE_ALREADY_EXISTS_REVIEW_RUN",
                    "source_id": _uuid(item.get("source_id")),
                    "dataset_id": dataset["dataset_id"],
                    "source_status": item.get("status"),
                }
        payload = {
            "dataset": DATASET_SLUG,
            "name": SOURCE_NAME,
            "content": adr["content"],
            "metadata": {
                "owner": "jarvis",
                "adr_id": "ADR-0001",
                "source_path": SOURCE_REL_PATH,
                "source_url": SOURCE_URL,
                "source_sha256": expected_hash,
            },
            "mode": "full",
            "wait": False,
            "force": False,
        }
        data = self._request(
            "POST", "/api/v1/remember", body=payload,
            accepted_status=(200, 202),
        )
        state = data.get("status")
        if state not in _RUN_STATES:
            raise KnowledgeError("RESULT_UNKNOWN")
        return {
            "status": "ACCEPTED" if state in {"queued", "running", "cancelling"}
                      else state.upper(),
            "run_id": _uuid(data.get("run_id")),
            "pipeline_status": state,
            "dataset_id": _uuid(data["dataset_id"]) if data.get("dataset_id") else None,
            "source_id": _uuid(data["source_id"]) if data.get("source_id") else None,
        }

    def inspect_run(self, run_id: str) -> dict:
        run_id = _uuid(run_id)
        data = self._request("GET", f"/api/v1/runs/{run_id}")
        if data.get("run_id") != run_id or data.get("status") not in _RUN_STATES:
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        return {
            "status": data["status"],
            "run_id": run_id,
            "dataset_id": _uuid(data["dataset_id"]) if data.get("dataset_id") else None,
            "source_id": _uuid(data["source_id"]) if data.get("source_id") else None,
            "progress": data.get("progress"),
            "current_step": data.get("current_step"),
            "error_code": data.get("error_code"),
            "metrics": data.get("metrics") if isinstance(data.get("metrics"), dict) else {},
        }

    def dataset_stats(self) -> dict:
        dataset = self._dataset(required=True)
        stats = self._request(
            "GET", f"/api/v1/datasets/{dataset['dataset_id']}/stats",
        )
        if stats.get("dataset_id") != dataset["dataset_id"]:
            raise KnowledgeError("INCOMPATIBLE_RESPONSE")
        return {
            "dataset_id": dataset["dataset_id"],
            "slug": DATASET_SLUG,
            "sources": stats.get("sources"),
            "documents": stats.get("documents"),
            "chunks": stats.get("chunks"),
        }

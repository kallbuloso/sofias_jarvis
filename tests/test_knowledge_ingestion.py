"""Offline test of the real ADR slice and bounded Knowledge ingest contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from jarvis.memory.knowledge import KnowledgeError
from jarvis.memory.knowledge_ingestion import (
    ADRKnowledgeClient, DATASET_NAME, DATASET_SLUG, SOURCE_NAME,
    approved_adr,
)

BASE = "https://memory.example"
DATASET_ID = str(uuid4())
SOURCE_ID = str(uuid4())
RUN_ID = str(uuid4())


class FakeReply:
    def __init__(self, status, data):
        self.status = status
        self.raw = json.dumps({"data": data, "meta": {}}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.raw[:size]


class Transport:
    def __init__(self, *, existing=False, source=None, fail_on=None):
        self.existing = existing
        self.source = source
        self.fail_on = fail_on
        self.calls = []

    def open(self, request, timeout):
        self.calls.append(request)
        url, method = request.full_url, request.method
        if self.fail_on and self.fail_on in url:
            raise URLError("secret from private network")
        if "/api/v1/datasets?" in url and method == "GET":
            items = [{
                "dataset_id": DATASET_ID, "name": DATASET_NAME,
                "slug": DATASET_SLUG, "status": "active",
            }] if self.existing else []
            return FakeReply(200, {"items": items, "limit": 100, "offset": 0,
                                   "total": len(items)})
        if url.endswith("/api/v1/datasets") and method == "POST":
            assert json.loads(request.data) == {
                "name": DATASET_NAME,
                "slug": DATASET_SLUG,
                "description": "Documentos aprovados de arquitetura do JARVIS (TB-02).",
            }
            self.existing = True
            return FakeReply(201, {
                "dataset_id": DATASET_ID, "name": DATASET_NAME,
                "slug": DATASET_SLUG, "status": "active",
            })
        if "/sources?" in url and method == "GET":
            return FakeReply(200, {"items": [self.source] if self.source else [],
                                   "total": 1 if self.source else 0,
                                   "limit": 100, "offset": 0})
        if url.endswith("/api/v1/remember") and method == "POST":
            body = json.loads(request.data)
            assert body["dataset"] == DATASET_SLUG
            assert body["mode"] == "full"
            assert body["wait"] is False
            assert body["force"] is False
            assert body["metadata"]["adr_id"] == "ADR-0001"
            assert body["metadata"]["source_sha256"] == hashlib.sha256(
                body["content"].encode("utf-8")
            ).hexdigest()
            return FakeReply(202, {
                "run_id": RUN_ID, "status": "queued",
                "dataset_id": None, "source_id": None,
            })
        if "/api/v1/runs/" in url and method == "GET":
            return FakeReply(200, {
                "run_id": RUN_ID, "status": "succeeded",
                "dataset_id": DATASET_ID, "source_id": SOURCE_ID,
                "progress": 1.0, "current_step": None,
                "error_code": None, "metrics": {"chunks": 3},
            })
        if url.endswith("/stats") and method == "GET":
            return FakeReply(200, {
                "dataset_id": DATASET_ID,
                "sources": {"active": 1, "total": 1},
                "documents": {"active": 1, "total": 1},
                "chunks": {"active": 3, "total": 3},
            })
        raise AssertionError(f"Unexpected request {method} {url}")


def client(transport):
    return ADRKnowledgeClient(BASE, "PRIVATE-KEY", opener=transport)


def test_real_checked_out_adr_is_one_approved_document():
    record = approved_adr()
    assert record["content"].startswith("# ADR-0001")
    assert "**Status:** ACCEPTED" in record["content"]
    assert "Adotar Modular Monolith" in record["content"]
    assert "# ADR-0002" not in record["content"]
    assert record["sha256"] == hashlib.sha256(
        record["content"].encode("utf-8")
    ).hexdigest()


def test_source_extraction_rejects_unapproved_changed_document(tmp_path):
    path = tmp_path / "docs/product-manager/07-JARVIS-ADRs.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# ADR-0001 — Modular Monolith as the JARVIS Core Architecture\n"
        "**Status:** DRAFT\n"
        "# ADR-0002 — Operational Persistence & Recovery\n",
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeError, match="ADR_SOURCE_INCOMPATIBLE"):
        approved_adr(tmp_path)


def test_dataset_create_exact_slug_http_201_and_second_call_is_noop():
    transport = Transport()
    service = client(transport)
    assert service.create_adr_dataset()["status"] == "CREATED"
    assert transport.calls[-1].method == "POST"
    before = len([r for r in transport.calls if r.method == "POST"])
    second = service.create_adr_dataset()
    assert second["status"] == "ALREADY_EXISTS"
    assert second["dataset_id"] == DATASET_ID
    assert second["slug"] == DATASET_SLUG
    assert len([r for r in transport.calls if r.method == "POST"]) == before


def test_full_adr_ingest_returns_run_without_pretending_processing_finished():
    transport = Transport(existing=True)
    service = client(transport)
    record = approved_adr()
    result = service.ingest_adr(record)
    assert result["status"] == "ACCEPTED"
    assert result["pipeline_status"] == "queued"
    assert result["run_id"] == RUN_ID
    assert result["source_id"] is None
    writes = [r for r in transport.calls if r.method == "POST"]
    assert len(writes) == 1
    assert "PRIVATE-KEY" not in json.dumps(result)


def test_no_document_ingest_when_dataset_is_missing():
    transport = Transport(existing=False)
    with pytest.raises(KnowledgeError, match="DATASET_NOT_FOUND"):
        client(transport).ingest_adr(approved_adr())
    assert not any(r.method == "POST" for r in transport.calls)


def test_duplicate_document_is_detected_before_any_new_write():
    record = approved_adr()
    transport = Transport(existing=True, source={
        "source_id": SOURCE_ID, "name": SOURCE_NAME, "status": "active",
        "metadata": {"adr_id": "ADR-0001", "source_sha256": record["sha256"]},
    })
    result = client(transport).ingest_adr(record)
    assert result["status"] == "SOURCE_ALREADY_EXISTS_REVIEW_RUN"
    assert not any(r.method == "POST" for r in transport.calls)


def test_source_name_hash_collision_fails_closed():
    record = approved_adr()
    transport = Transport(existing=True, source={
        "source_id": SOURCE_ID, "name": SOURCE_NAME, "status": "active",
        "metadata": {"adr_id": "ADR-0001", "source_sha256": "bad"},
    })
    with pytest.raises(KnowledgeError, match="ADR_SOURCE_CONFLICT"):
        client(transport).ingest_adr(record)
    assert not any(r.method == "POST" for r in transport.calls)


def test_does_not_overwrite_unrelated_dataset():
    transport = Transport(existing=True)
    original = transport.open

    def wrong_name(request, timeout):
        result = original(request, timeout)
        if "/api/v1/datasets?" in request.full_url:
            return FakeReply(200, {"items": [{
                "dataset_id": DATASET_ID, "name": "Unrelated owner",
                "slug": DATASET_SLUG, "status": "active",
            }], "limit": 100, "offset": 0, "total": 1})
        return result

    transport.open = wrong_name
    with pytest.raises(KnowledgeError, match="DATASET_IDENTITY_MISMATCH"):
        client(transport).create_adr_dataset()
    assert not any(r.method == "POST" for r in transport.calls)


def test_failed_network_submission_never_retries():
    transport = Transport(existing=True, fail_on="/api/v1/remember")
    with pytest.raises(KnowledgeError, match="SERVICE_UNAVAILABLE"):
        client(transport).ingest_adr(approved_adr())
    assert len([r for r in transport.calls if r.method == "POST"]) == 1


def test_readonly_run_and_stats():
    service = client(Transport(existing=True))
    result = service.inspect_run(RUN_ID)
    assert result["status"] == "succeeded"
    assert result["source_id"] == SOURCE_ID
    assert service.dataset_stats()["chunks"]["active"] == 3


def test_run_id_mismatch_rejected():
    transport = Transport(existing=True)
    service = client(transport)
    with pytest.raises(KnowledgeError, match="INCOMPATIBLE_RESPONSE"):
        service.inspect_run(str(uuid4()))

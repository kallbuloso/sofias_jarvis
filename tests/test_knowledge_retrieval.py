"""Sofias Memory Knowledge (chunks) contract tests: offline only."""
from __future__ import annotations

from io import BytesIO
import json
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from jarvis.memory.knowledge import KnowledgeClient, KnowledgeError

QUERY_ID = str(uuid4())
DATASET_ID = str(uuid4())
SOURCE_ID = str(uuid4())
DOCUMENT_ID = str(uuid4())
CHUNK_ID = str(uuid4())
URL = "https://memory.example"


class Reply:
    status = 200

    def __init__(self, data, status=200):
        self.data = json.dumps({"data": data, "meta": {}}).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.data[:limit]


class Transport:
    def __init__(self, data, error=None):
        self.data, self.error, self.calls = data, error, []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return Reply(self.data)


def client(data, error=None):
    transport = Transport(data, error)
    return KnowledgeClient(URL, "PRIVATE-MEMORY-KEY", opener=transport), transport


def dataset_list():
    return {"items": [{
        "dataset_id": DATASET_ID, "name": "JARVIS documents",
        "slug": "jarvis-docs", "status": "active",
    }], "total": 1, "limit": 50, "offset": 0}


def chunk_result(*, context=None, references=None, mode="chunks", answer=None):
    context = [{
        "chunk_id": CHUNK_ID, "source_id": SOURCE_ID,
        "document_id": DOCUMENT_ID, "dataset_id": DATASET_ID,
        "text": "O Core não executa memória.", "source_name": "ADR-0004",
        "score": 0.87, "chunk_ordinal": 1,
    }] if context is None else context
    references = [{
        "chunk_id": CHUNK_ID, "source_id": SOURCE_ID,
        "document_id": DOCUMENT_ID, "quote": "O Core não executa memória.",
        "source_name": "ADR-0004", "score": 0.87, "url": None,
    }] if references is None else references
    return {"query_id": QUERY_ID, "mode": mode, "answer": answer,
            "context": context, "references": references,
            "timings_ms": {"retrieval": 12}}


def test_list_datasets_retrieves_only_safe_metadata():
    adapter, transport = client(dataset_list())
    result = adapter.list_datasets()
    assert result["items"][0] == {
        "dataset_id": DATASET_ID, "name": "JARVIS documents",
        "slug": "jarvis-docs", "status": "active",
    }
    request, _ = transport.calls[0]
    assert request.method == "GET"
    assert request.full_url.endswith("/api/v1/datasets?limit=50&offset=0")
    assert request.get_header("X-api-key") == "PRIVATE-MEMORY-KEY"


def test_query_sends_explicit_dataset_chunks_only_context_and_refs():
    adapter, transport = client(chunk_result())
    result = adapter.query_chunks(query=" O que decidiu o Core? ", datasets=["jarvis-docs"])
    assert result["status"] == "RESULTS_FOUND"
    assert result["query_id"] == QUERY_ID
    assert result["references"][0]["chunk_id"] == CHUNK_ID
    assert result["references"][0]["source_name"] == "ADR-0004"
    request, _ = transport.calls[0]
    body = json.loads(request.data)
    assert request.method == "POST"  # read-only to knowledge; server keeps Query audit
    assert body == {
        "query": "O que decidiu o Core?",
        "datasets": ["jarvis-docs"], "mode": "chunks", "top_k": 5,
        "only_context": True, "include_references": True,
        "include_session_context": False,
    }
    assert len(transport.calls) == 1
    assert "PRIVATE-MEMORY-KEY" not in json.dumps(result)


def test_no_results_not_confused_with_outage():
    adapter, _ = client(chunk_result(context=[], references=[]))
    result = adapter.query_chunks(query="O que não está documentado?", datasets=["main"])
    assert result["status"] == "NO_RESULTS"
    assert result["references"] == []


@pytest.mark.parametrize("datasets", [
    [], ["NOT-VALID"], ["a/b"], ["http://other"], ["bad slug"],
])
def test_invalid_dataset_never_contacts_remote_service(datasets):
    adapter, transport = client(chunk_result())
    with pytest.raises(ValueError):
        adapter.query_chunks(query="Teste", datasets=datasets)
    assert transport.calls == []


@pytest.mark.parametrize("query", ["", "  ", "Q" * 4001])
def test_invalid_query_prevents_remote_request(query):
    adapter, transport = client(chunk_result())
    with pytest.raises(ValueError):
        adapter.query_chunks(query=query, datasets=["main"])
    assert transport.calls == []


def test_missing_references_never_fabricated():
    adapter, _ = client(chunk_result(references=[]))
    result = adapter.query_chunks(query="Busca", datasets=["main"])
    assert len(result["context"]) == 1
    assert result["references"] == []


def test_citation_for_unrelated_chunk_is_rejected():
    result = chunk_result()
    result["references"][0]["chunk_id"] = str(uuid4())
    adapter, _ = client(result)
    with pytest.raises(KnowledgeError, match="INCOMPATIBLE_REFERENCE"):
        adapter.query_chunks(query="Busca", datasets=["main"])


@pytest.mark.parametrize("change", [
    {"mode": "rag"},
    {"answer": "Um resumo gerado pela API"},
    {"query_id": "not-uuid"},
])
def test_incompatible_result_cannot_be_claimed_as_knowledge(change):
    result = chunk_result()
    result.update(change)
    adapter, _ = client(result)
    with pytest.raises(KnowledgeError, match="INCOMPATIBLE_RESPONSE"):
        adapter.query_chunks(query="Busca", datasets=["main"])


def test_transport_failure_and_auth_error_sanitized():
    adapter, _ = client(chunk_result(), URLError("private network details"))
    with pytest.raises(KnowledgeError, match="SERVICE_UNAVAILABLE"):
        adapter.query_chunks(query="Busca", datasets=["main"])
    err = HTTPError(URL, 403, "private body", None, BytesIO(b'{"private":"data"}'))
    adapter, _ = client(chunk_result(), err)
    with pytest.raises(KnowledgeError, match="AUTH_REJECTED"):
        adapter.query_chunks(query="Busca", datasets=["main"])


def test_list_rejects_invalid_pagination_without_network():
    adapter, transport = client(dataset_list())
    for limit, offset in ((0, 0), (101, 0), (10, -1), (True, 0)):
        with pytest.raises(ValueError):
            adapter.list_datasets(limit=limit, offset=offset)
    assert transport.calls == []

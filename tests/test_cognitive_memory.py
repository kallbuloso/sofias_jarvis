"""Cognitive Memory v1 tests: simulated transport, never contact the VPS."""
import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError

MEM = "4ccf64a8-5b4e-4c1d-82e1-bc95a394087f"
NEXT = "138c6786-f1b9-4fb4-a1d9-cc13017d8ae3"
TURN = "dd0c6034-7c69-4641-8c54-f2c4a159bd59"
KEY = "dcaddbaf-d393-426a-bab2-d9ba9702c874"
PROVENANCE = {"origin_kind": "user_asserted", "source_system": "jarvis", "turn_uuid": TURN}


def item(id=MEM, lifecycle="active", scope="project:jarvis"):
    return {
        "memory_id": id, "memory_type": "semantic",
        "scope": None if lifecycle == "forgotten" else scope,
        "content": None if lifecycle == "forgotten" else "Escolha aprovada",
        "lifecycle": lifecycle, "created_at": "2026-10-31T17:00:00Z",
        "confidence": None, "superseded_by": None, "superseded_at": None,
        "forgotten_at": None, "valid_from": None, "valid_until": None,
        "provenance": PROVENANCE,
    }


class Reply:
    def __init__(self, data, status=200):
        self.raw = json.dumps({"data": data, "meta": {}}).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size):
        return self.raw[:size]


class Transport:
    def __init__(self, data=None, status=200, error=None):
        self.calls, self.data, self.status, self.error = [], data, status, error

    def open(self, request, timeout):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return Reply(self.data, self.status)


def client(transport):
    return CognitiveMemoryClient("https://memory.example", "PRIVATE-KEY", opener=transport)


def test_get_uses_authenticated_read_and_checks_identity():
    transport = Transport(item())
    assert client(transport).get(MEM)["memory_id"] == MEM
    request = transport.calls[0]
    assert request.method == "GET"
    assert request.get_header("X-api-key") == "PRIVATE-KEY"
    assert request.full_url.endswith("/memories/" + MEM)


def test_create_requires_explicit_idempotency_and_user_provenance():
    transport = Transport(item(), status=201)
    assert client(transport).create(
        memory_type="semantic", scope="project:jarvis", content="Escolha aprovada",
        provenance=PROVENANCE, idempotency_key=KEY,
    )["lifecycle"] == "active"
    request = transport.calls[0]
    assert request.get_header("Idempotency-key") == KEY
    assert json.loads(request.data)["provenance"]["source_system"] == "jarvis"
    assert len(transport.calls) == 1


@pytest.mark.parametrize("invalid", [
    {"memory_type": "episodic", "scope": "global", "content": "ok", "provenance": PROVENANCE, "idempotency_key": KEY},
    {"memory_type": "semantic", "scope": "project:Other", "content": "ok", "provenance": PROVENANCE, "idempotency_key": KEY},
    {"memory_type": "semantic", "scope": "global", "content": "", "provenance": PROVENANCE, "idempotency_key": KEY},
    {"memory_type": "semantic", "scope": "global", "content": "ok", "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis"}, "idempotency_key": KEY},
    {"memory_type": "semantic", "scope": "global", "content": "ok", "provenance": PROVENANCE, "idempotency_key": "new-key"},
])
def test_invalid_creates_never_leave_process(invalid):
    transport = Transport(item(), status=201)
    with pytest.raises(ValueError):
        client(transport).create(**invalid)
    assert not transport.calls


def test_inferred_requires_confidence():
    transport = Transport(item(), status=201)
    with pytest.raises(ValueError, match="inference_requires_confidence"):
        client(transport).create(
            memory_type="semantic", scope="global", content="ok",
            provenance={"origin_kind": "inferred", "source_system": "jarvis", "turn_uuid": TURN},
            idempotency_key=KEY,
        )
    assert not transport.calls


def test_current_recall_scopes_and_historical_flag():
    transport = Transport({"items": [{"memory": item(), "relevance": 0.9, "is_current_truth": True}]})
    hits = client(transport).recall(query="Decisão?", scopes=["project:jarvis"])
    assert len(hits) == 1
    request = transport.calls[0]
    assert request.method == "POST"
    assert request.get_header("Idempotency-key") is None
    assert json.loads(request.data)["include_superseded"] is False


@pytest.mark.parametrize("hit", [
    {"memory": item(lifecycle="forgotten"), "relevance": 0.9, "is_current_truth": True},
    {"memory": item(scope="project:other"), "relevance": 0.9, "is_current_truth": True},
    {"memory": item(), "relevance": 0.9, "is_current_truth": False},
])
def test_recall_rejects_forgotten_other_scope_and_not_current(hit):
    transport = Transport({"items": [hit]})
    with pytest.raises(CognitiveMemoryError, match="INCOMPATIBLE_RESPONSE"):
        client(transport).recall(query="Busca", scopes=["project:jarvis"])


def test_empty_recall_is_not_network_outage():
    assert client(Transport({"items": []})).recall(query="Busca", scopes=["global"]) == []
    transport = Transport(error=URLError("sensitive transport details"))
    with pytest.raises(CognitiveMemoryError) as e:
        client(transport).recall(query="Busca", scopes=["global"])
    assert e.value.code == "SERVICE_UNAVAILABLE"
    assert len(transport.calls) == 1
    assert "sensitive" not in str(e.value)


def test_supersede_preserves_lineage_and_inherits_scope():
    old = item(lifecycle="superseded")
    old["superseded_by"] = NEXT
    transport = Transport({"old": old, "replacement": item(id=NEXT)})
    data = client(transport).supersede(
        MEM, content="Nova decisão", provenance=PROVENANCE, idempotency_key=KEY,
    )
    assert data["replacement"]["memory_id"] == NEXT
    body = json.loads(transport.calls[0].data)
    assert "scope" not in body and "memory_type" not in body
    assert transport.calls[0].get_header("Idempotency-key") == KEY


def test_forget_checks_tombstone_without_content():
    transport = Transport(item(lifecycle="forgotten"))
    assert client(transport).forget(MEM, idempotency_key=KEY)["lifecycle"] == "forgotten"
    assert transport.calls[0].data is None
    with pytest.raises(CognitiveMemoryError) as e:
        client(Transport(item())).forget(MEM, idempotency_key=KEY)
    assert e.value.code == "RESULT_UNKNOWN"
    assert e.value.operation_key == KEY


def test_mutation_transport_failure_is_unknown_and_never_retried():
    transport = Transport(error=URLError("PRIVATE INFORMATION"))
    with pytest.raises(CognitiveMemoryError) as e:
        client(transport).create(
            memory_type="semantic", scope="project:jarvis", content="Decisão",
            provenance=PROVENANCE, idempotency_key=KEY,
        )
    assert e.value.code == "RESULT_UNKNOWN"
    assert e.value.operation_key == KEY
    assert len(transport.calls) == 1
    assert "PRIVATE" not in str(e.value)


@pytest.mark.parametrize("status,code", [
    (404, "MEMORY_NOT_FOUND"), (409, "MEMORY_STATE_CONFLICT"),
    (409, "IDEMPOTENCY_CONFLICT"), (422, "INVALID_REQUEST"),
])
def test_http_rejection_preserves_safe_error_code(status, code):
    payload = json.dumps({"error": {"code": code}}).encode()
    transport = Transport(error=HTTPError("https://memory.example", status, "private", None, BytesIO(payload)))
    with pytest.raises(CognitiveMemoryError) as e:
        client(transport).get(MEM)
    assert e.value.code == code


def test_mutation_http_503_must_not_invent_success():
    transport = Transport(error=HTTPError("https://memory.example", 503, "private", None, None))
    with pytest.raises(CognitiveMemoryError) as e:
        client(transport).forget(MEM, idempotency_key=KEY)
    assert e.value.code == "RESULT_UNKNOWN"

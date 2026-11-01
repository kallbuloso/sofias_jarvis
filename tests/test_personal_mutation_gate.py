from uuid import uuid4
import pytest
from jarvis.memory.personal_confirmation import PersonalMutationGate

def test_one_use_token():
    memory_id = str(uuid4())
    conversation_id = str(uuid4())
    gate = PersonalMutationGate(now=lambda: 100.0)
    token, phrase = gate.offer("forget", {"memory_id": memory_id, "source_ref": "origin"}, "", conversation_id)
    assert phrase == "ESQUECER " + memory_id
    assert gate.consume(token, phrase, conversation_id).action == "forget"
    with pytest.raises(ValueError):
        gate.consume(token, phrase, conversation_id)

def test_wrong_confirmation_consumes_token():
    memory_id = str(uuid4())
    conversation_id = str(uuid4())
    gate = PersonalMutationGate()
    token, phrase = gate.offer("supersede", {"memory_id": memory_id, "source_ref": "origin"}, "nova", conversation_id)
    with pytest.raises(ValueError):
        gate.consume(token, "SIM", conversation_id)
    with pytest.raises(ValueError):
        gate.consume(token, phrase, conversation_id)

def test_expiry_and_cancel():
    clock = [100.0]
    memory_id, conversation_id = str(uuid4()), str(uuid4())
    gate = PersonalMutationGate(ttl_seconds=10, now=lambda: clock[0])
    token, phrase = gate.offer("forget", {"memory_id": memory_id, "source_ref": "origin"}, "", conversation_id)
    clock[0] = 120.0
    with pytest.raises(ValueError):
        gate.consume(token, phrase, conversation_id)
    token, phrase = gate.offer("forget", {"memory_id": memory_id, "source_ref": "origin"}, "", conversation_id)
    gate.clear()
    with pytest.raises(ValueError):
        gate.consume(token, phrase, conversation_id)

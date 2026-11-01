from uuid import uuid4
import pytest
from jarvis.memory.personal_confirmation import PersonalMutationGate, PersonalCreateGate

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


def test_conversational_create_consumes_click_once_without_uuid_or_phrase():
    conversation_id = str(uuid4())
    gate = PersonalCreateGate(now=lambda: 100.0)
    token = gate.offer(content="No JARVIS prefiro Vuetify 3",
                       scope="project:jarvis", conversation_id=conversation_id)
    pending = gate.consume(token, conversation_id, "project:jarvis")
    assert pending.content == "No JARVIS prefiro Vuetify 3"
    assert pending.authorization.method == "desktop_approved"
    assert pending.authorization.target_memory_id is None
    assert pending.authorization.conversation_id == conversation_id
    with pytest.raises(ValueError, match="missing"):
        gate.consume(token, conversation_id, "project:jarvis")


def test_conversational_create_requires_scope_and_sanitized_content():
    conversation_id = str(uuid4())
    gate = PersonalCreateGate()
    with pytest.raises(ValueError, match="sensitive"):
        gate.offer(content="Minha senha: 123456789", scope="global",
                   conversation_id=conversation_id)
    with pytest.raises(ValueError, match="scope"):
        gate.offer(content="Uma escolha", scope="project:other",
                   conversation_id=conversation_id)
    token = gate.offer(content="Para este projeto prefiro teal",
                       scope=None, conversation_id=conversation_id)
    pending = gate.consume(token, conversation_id, "project:jarvis")
    assert pending.scope == "project:jarvis"


def test_conversational_create_wrong_scope_conversation_and_expiry_fail_closed():
    original = str(uuid4())
    other = str(uuid4())
    time = [10.0]
    gate = PersonalCreateGate(ttl_seconds=2, now=lambda: time[0])
    token = gate.offer(content="Teste", scope="global", conversation_id=original)
    with pytest.raises(ValueError, match="wrong_conversation"):
        gate.consume(token, other, "global")
    with pytest.raises(ValueError, match="missing"):
        gate.consume(token, original, "global")
    token = gate.offer(content="Teste", scope="global", conversation_id=original)
    with pytest.raises(ValueError, match="wrong_scope"):
        gate.consume(token, original, "project:jarvis")
    token = gate.offer(content="Teste", scope=None, conversation_id=original)
    time[0] = 13.0
    with pytest.raises(ValueError, match="expired"):
        gate.consume(token, original, "global")
    token = gate.offer(content="Teste", scope=None, conversation_id=original)
    gate.clear()
    with pytest.raises(ValueError, match="missing"):
        gate.consume(token, original, "global")

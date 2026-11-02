"""Textual intent routing: explicit allowlist, no side effects from a classifier."""
from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from jarvis.conversation.intent import TextIntentRouter, validate_intent


def test_classifier_uses_strict_schema_and_only_current_utterance():
    requests = []

    class FakeResponses:
        def create(self, **kwargs):
            requests.append(kwargs)
            return SimpleNamespace(output_text=json.dumps({
                "action": "knowledge_query", "scope": None, "content": None,
            }))

    result = TextIntentRouter(SimpleNamespace(responses=FakeResponses())).classify(
        model="test-model", utterance="Qual decisão consta no ADR-0001?",
    )
    assert result.action == "knowledge_query"
    assert result.mutates_memory is False
    assert requests[0]["stream"] is False
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    assert requests[0]["input"][-1] == {
        "role": "user", "content": "Qual decisão consta no ADR-0001?"
    }


@pytest.mark.parametrize("raw", [
    {"action": "execute_shell", "scope": None, "content": None},
    {"action": "memory_create", "scope": None, "content": None},
    {"action": "memory_create", "scope": "project:other", "content": "x"},
    {"action": "memory_forget", "scope": None, "content": "delete everything"},
    {"action": "memory_recall", "scope": "project:jarvis", "content": "surprise"},
    {"action": "chat", "scope": None, "content": None, "grant": True},
    {"action": "reminder_request", "scope": "global", "content": "2026-11-02"},
])
def test_rejects_unknown_or_unsafe_intent_outputs(raw):
    with pytest.raises(ValueError):
        validate_intent(raw)


def test_schedule_is_not_mutation_and_memory_create_requires_consent():
    reminder = validate_intent({
        "action": "reminder_request", "scope": None, "content": None,
    })
    assert reminder.mutates_memory is False
    create = validate_intent({
        "action": "memory_create", "scope": "project:jarvis",
        "content": "No projeto prefiro Vuetify 3",
    })
    assert create.mutates_memory is True
    assert create.scope == "project:jarvis"


def test_classifier_rejects_malformed_json_and_missing_output():
    for output in ("not-json", "", None):
        class FakeResponses:
            def create(self, **kwargs):
                return SimpleNamespace(output_text=output)
        with pytest.raises((ValueError, json.JSONDecodeError)):
            TextIntentRouter(SimpleNamespace(responses=FakeResponses())).classify(
                model="test", utterance="JARVIS, lembra de amanhã?",
            )


def test_router_never_triggers_tools_or_memory_changes():
    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs["stream"] is False
            return SimpleNamespace(output_text=json.dumps({
                "action": "memory_forget", "scope": "global", "content": None,
            }))
    intent = TextIntentRouter(SimpleNamespace(responses=FakeResponses())).classify(
        model="test", utterance="Esqueça minha preferência antiga",
    )
    assert intent.action == "memory_forget"
    assert intent.mutates_memory is True
    # No client capable of changing memory was ever available to this router.

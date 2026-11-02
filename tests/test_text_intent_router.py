"""Textual intent routing: explicit allowlist, provider-neutral structured output."""
from __future__ import annotations

import pytest

from jarvis.conversation.intent import TextIntentRouter, validate_intent


class FakeStructuredProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def test_classifier_uses_strict_schema_and_only_current_utterance():
    provider = FakeStructuredProvider({
        "action": "knowledge_query", "scope": None, "content": None,
    })
    result = TextIntentRouter(provider).classify(
        model="test-model", utterance="Qual decisão consta no ADR-0001?",
    )
    assert result.action == "knowledge_query"
    assert result.mutates_memory is False
    request = provider.calls[0]
    assert request["schema_name"] == "jarvis_text_intent"
    assert request["schema"]["additionalProperties"] is False
    assert request["messages"][-1] == {
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


@pytest.mark.parametrize("output", [None, "not-a-dict", [], {}])
def test_classifier_rejects_malformed_provider_output(output):
    provider = FakeStructuredProvider(output)
    with pytest.raises((ValueError, TypeError)):
        TextIntentRouter(provider).classify(
            model="test", utterance="JARVIS, lembra de amanhã?",
        )


def test_router_never_triggers_tools_or_memory_changes():
    provider = FakeStructuredProvider({
        "action": "memory_forget", "scope": "global", "content": None,
    })
    intent = TextIntentRouter(provider).classify(
        model="test", utterance="Esqueça minha preferência antiga",
    )
    assert intent.action == "memory_forget"
    assert intent.mutates_memory is True
    assert len(provider.calls) == 1

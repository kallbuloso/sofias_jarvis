"""Ephemeral, one-use authorization gate for user-confirmed memory mutation.

An LLM, source document, command preview or UI button cannot perform a
mutation until a second, exact typed authorization is validated.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from secrets import token_urlsafe
from time import monotonic
from typing import Callable
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PersonalMutationAuthorization:
    """Local evidence of verified typed consent; never contains the phrase/token."""
    authorization_id: str
    action: str
    target_memory_id: str | None
    method: str
    conversation_id: str | None

    @classmethod
    def from_typed_confirmation(cls, *, action: str, target_memory_id: str | None,
                                phrase: str, method: str,
                                conversation_id: str | None = None):
        if method not in {"cli_typed", "desktop_typed"}:
            raise ValueError("invalid_confirmation_method")
        if action not in {"create", "supersede", "forget"}:
            raise ValueError("invalid_confirmation_action")
        if method == "desktop_typed":
            if action == "create" or conversation_id is None:
                raise ValueError("invalid_desktop_confirmation_context")
            conversation_id = str(UUID(conversation_id))
        elif conversation_id is not None:
            raise ValueError("unexpected_cli_confirmation_context")
        if action == "create":
            if target_memory_id is not None or phrase != "GRAVAR":
                raise ValueError("invalid_create_confirmation")
            target = None
        else:
            target = str(UUID(target_memory_id))
            expected = ("SUBSTITUIR " if action == "supersede" else "ESQUECER ") + target
            if phrase != expected:
                raise ValueError("confirmation_phrase_mismatch")
        return cls(str(uuid4()), action, target, method, conversation_id)


@dataclass(frozen=True)
class PendingPersonalMutation:
    action: str
    preview: dict
    replacement: str
    conversation_id: str
    expires_at: float
    authorization: PersonalMutationAuthorization | None = None


class PersonalMutationGate:
    def __init__(self, *, ttl_seconds: int = 180,
                 now: Callable[[], float] = monotonic):
        if ttl_seconds < 1 or ttl_seconds > 900:
            raise ValueError("invalid_authorization_ttl")
        self._ttl = ttl_seconds
        self._now = now
        self._token: str | None = None
        self._pending: PendingPersonalMutation | None = None

    def clear(self) -> None:
        self._token = None
        self._pending = None

    def offer(self, action: str, preview: dict, replacement: str,
              conversation_id: str) -> tuple[str, str]:
        self.clear()
        if action not in {"supersede", "forget"}:
            raise ValueError("invalid_personal_action")
        if not isinstance(preview, dict):
            raise ValueError("invalid_memory_preview")
        target = str(UUID(preview["memory_id"]))
        conversation_id = str(UUID(conversation_id))
        if preview.get("memory_id") != target or not preview.get("source_ref"):
            raise ValueError("invalid_memory_preview")
        if (action == "supersede"
                and (not isinstance(replacement, str)
                     or not replacement.strip()
                     or len(replacement) > 16384)):
            raise ValueError("invalid_replacement")
        if action == "forget" and replacement:
            raise ValueError("invalid_forget_replacement")
        phrase = ("SUBSTITUIR " if action == "supersede" else "ESQUECER ") + target
        self._token = token_urlsafe(32)
        self._pending = PendingPersonalMutation(
            action=action, preview=dict(preview), replacement=replacement,
            conversation_id=conversation_id, expires_at=self._now() + self._ttl,
        )
        return self._token, phrase

    def consume(self, token: str, phrase: str,
                conversation_id: str) -> PendingPersonalMutation:
        pending, expected = self._pending, self._token
        # Fail closed: any attempt consumes the authorization, successful or not.
        self.clear()
        if (pending is None or not isinstance(token, str)
                or token != expected
                or not isinstance(phrase, str)):
            raise ValueError("authorization_missing_or_invalid")
        if self._now() > pending.expires_at:
            raise ValueError("authorization_expired")
        if str(UUID(conversation_id)) != pending.conversation_id:
            raise ValueError("authorization_wrong_conversation")
        target = pending.preview["memory_id"]
        required = ("SUBSTITUIR " if pending.action == "supersede"
                    else "ESQUECER ") + target
        if phrase != required:
            raise ValueError("authorization_phrase_mismatch")
        consent = PersonalMutationAuthorization.from_typed_confirmation(
            action=pending.action, target_memory_id=target,
            phrase=phrase, method="desktop_typed",
            conversation_id=pending.conversation_id,
        )
        return replace(pending, authorization=consent)

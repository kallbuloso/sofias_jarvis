"""Scoped receipts for explicit direct Create and separately confirmed mutations.

An LLM, source document, or tool result never grants authority. Direct
low-risk Create needs the original user's persisted explicit request;
Supersede/Forget retain their separate, one-use typed authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from secrets import token_urlsafe
from time import monotonic
from typing import Callable
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PersonalMutationAuthorization:
    """Local evidence of an explicit owner request or separate approval."""
    authorization_id: str
    action: str
    target_memory_id: str | None
    method: str
    conversation_id: str | None
    source_message_id: str | None = None

    @classmethod
    def from_explicit_user_message(
        cls, *, action: str, conversation_id: str, message_id: str,
    ):
        """Direct authorization requires proof of a persisted user's request.

        The Core separately validates the exact original content and policy.
        """
        if action != "create":
            raise ValueError("user_direct_intent_create_only")
        return cls(
            str(uuid4()), "create", None, "user_direct_intent",
            str(UUID(conversation_id)), str(UUID(message_id)),
        )

    @classmethod
    def from_desktop_approval(
        cls, *, action: str, conversation_id: str,
        target_memory_id: str | None = None,
    ):
        """Recorded single-click approval for one bounded desktop operation."""
        conversation_id = str(UUID(conversation_id))
        if action == "create":
            if target_memory_id is not None:
                raise ValueError("unexpected_create_target")
            target = None
        elif action in {"supersede", "forget"}:
            if target_memory_id is None:
                raise ValueError("desktop_approval_target_required")
            target = str(UUID(target_memory_id))
        else:
            raise ValueError("invalid_desktop_approval_action")
        return cls(str(uuid4()), action, target, "desktop_approved",
                   conversation_id)

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

    def approve(self, token: str, conversation_id: str) -> PendingPersonalMutation:
        """Single-click desktop approval for an already previewed mutation."""
        pending, expected = self._pending, self._token
        self.clear()
        if pending is None or not isinstance(token, str) or token != expected:
            raise ValueError("authorization_missing_or_invalid")
        if self._now() > pending.expires_at:
            raise ValueError("authorization_expired")
        if str(UUID(conversation_id)) != pending.conversation_id:
            raise ValueError("authorization_wrong_conversation")
        target = str(UUID(pending.preview["memory_id"]))
        consent = PersonalMutationAuthorization.from_desktop_approval(
            action=pending.action,
            conversation_id=pending.conversation_id,
            target_memory_id=target,
        )
        return replace(pending, authorization=consent)


@dataclass(frozen=True)
class PendingPersonalCreate:
    content: str
    scope: str
    conversation_id: str
    expires_at: float
    authorization: PersonalMutationAuthorization


class PersonalCreateGate:
    """Single use, conversation-scoped, time-limited approval for a previewed Create."""

    def __init__(self, *, ttl_seconds: int = 180,
                 now: Callable[[], float] = monotonic):
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("invalid_create_ttl")
        self._ttl = ttl_seconds
        self._now = now
        self._token: str | None = None
        self._pending: tuple[str, str | None, str, float] | None = None

    def clear(self) -> None:
        self._token = None
        self._pending = None

    def offer(self, *, content: str, scope: str | None,
              conversation_id: str) -> str:
        self.clear()
        from jarvis.memory.sensitive import looks_like_credential
        if (not isinstance(content, str) or not 1 <= len(content.strip()) <= 16384
                or looks_like_credential(content)):
            raise ValueError("invalid_or_sensitive_create_content")
        if scope is not None and scope not in {"global", "project:jarvis"}:
            raise ValueError("invalid_create_scope")
        conversation_id = str(UUID(conversation_id))
        self._token = token_urlsafe(32)
        self._pending = (content.strip(), scope, conversation_id,
                         self._now() + self._ttl)
        return self._token

    def consume(self, token: str, conversation_id: str,
                scope: str) -> PendingPersonalCreate:
        pending, expected = self._pending, self._token
        # Every attempt consumes the offer; never permit replay.
        self.clear()
        if (pending is None or not isinstance(token, str)
                or token != expected):
            raise ValueError("create_approval_missing")
        content, proposed_scope, owner_conversation, expiry = pending
        if self._now() > expiry:
            raise ValueError("create_approval_expired")
        if str(UUID(conversation_id)) != owner_conversation:
            raise ValueError("create_approval_wrong_conversation")
        if (scope not in {"global", "project:jarvis"}
                or (proposed_scope is not None and proposed_scope != scope)):
            raise ValueError("create_approval_wrong_scope")
        receipt = PersonalMutationAuthorization.from_desktop_approval(
            action="create", conversation_id=owner_conversation,
        )
        return PendingPersonalCreate(
            content, scope, owner_conversation, expiry, receipt,
        )

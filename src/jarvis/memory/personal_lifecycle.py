"""B-01: supervised, explicit user-owned cognitive memory mutations.

Never used by ordinary text generation or documentary retrieval. The caller
must show an exact target preview and obtain separate human confirmation.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError, _payload
from jarvis.memory.connection import validate_memory_url
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
from jarvis.memory.sensitive import looks_like_credential
from jarvis.conversation.create_decision import evaluate_direct_create


class PersonalMemoryLifecycle:
    def __init__(self, client: CognitiveMemoryClient,
                 journal: MemoryOperationJournal, service_url: str):
        self.client = client
        self.journal = journal
        self.service_url = validate_memory_url(service_url)
        if client.base_url != self.service_url:
            raise ValueError("memory_service_mismatch")

    def create(self, *, content: str, scope: str, conversation_id: str,
               confirmation: PersonalMutationAuthorization) -> dict:
        """User-approved personal Create: journal-first, no retry after ambiguity."""
        if (not isinstance(confirmation, PersonalMutationAuthorization)
                or confirmation.action != "create"
                or confirmation.target_memory_id is not None
                or confirmation.method not in {"desktop_approved", "user_direct_intent"}
                or confirmation.conversation_id != str(UUID(conversation_id))):
            raise ValueError("missing_or_mismatched_create_approval")
        if confirmation.method == "user_direct_intent":
            message_id = confirmation.source_message_id
            original = (
                self.journal._store.verified_user_utterance(message_id, conversation_id)
                if message_id is not None else None
            )
            decision = evaluate_direct_create(
                original, classified_action="memory_create",
            )
            if (decision.result != "PERMITTED" or decision.content != content
                    or decision.scope != scope):
                raise ValueError("direct_create_not_authorized_by_user_message")
            confirmation_ref = "user-message:" + message_id
        else:
            if confirmation.source_message_id is not None:
                raise ValueError("invalid_desktop_approval_source")
            confirmation_ref = (
                f"user-confirmation:{confirmation.authorization_id}"
            )
        if scope not in {"global", "project:jarvis"}:
            raise ValueError("invalid_create_scope")
        if looks_like_credential(content):
            raise ValueError("sensitive_content_rejected")
        memory_type = "profile" if scope == "global" else "semantic"
        operation_id = str(uuid4())
        provenance = {
            "origin_kind": "user_asserted",
            "source_system": "jarvis",
            "source_ref": f"memory-operation:{operation_id}",
            "conversation_uuid": confirmation.conversation_id,
            "confirmation_ref": confirmation_ref,
        }
        _payload(content, provenance)  # Check before any journal/network operation.
        payload = {
            "idempotency_key": operation_id,
            "memory_type": memory_type,
            "scope": scope,
            "content": content.strip(),
            "provenance": provenance,
        }
        self.journal.prepare(
            operation_id, self.service_url, payload, confirmation=confirmation,
        )

        def confirmed(reply: dict) -> dict:
            memory_id = str(UUID(reply["memory_id"]))
            if (reply.get("lifecycle") != "active"
                    or reply.get("content") != content.strip()
                    or reply.get("scope") != scope
                    or reply.get("memory_type") != memory_type
                    or reply.get("provenance", {}).get("origin_kind") != "user_asserted"
                    or reply.get("provenance", {}).get("source_system") != "jarvis"
                    or reply.get("provenance", {}).get("source_ref") !=
                    provenance["source_ref"]):
                raise ValueError("invalid_personal_create_ack")
            self.journal.resolve(operation_id, status="confirmed", memory_id=memory_id)
            return {"status": "CONFIRMED", "operation_id": operation_id,
                    "memory_id": memory_id, "scope": scope,
                    "memory_type": memory_type}

        return self._execute(
            operation_id, lambda: self.client.create(
                memory_type=memory_type, scope=scope, content=content.strip(),
                provenance=provenance, idempotency_key=operation_id,
            ), confirmed,
        )

    def preview(self, memory_id: str, *, action: str) -> dict:
        if action not in {"supersede", "forget"}:
            raise ValueError("invalid_personal_action")
        memory_id = str(UUID(memory_id))
        owner = self.journal.owned_user_memory(memory_id, self.service_url)
        if owner is None:
            raise ValueError("memory_not_owned_by_this_installation")
        if self.journal.has_unresolved_mutation(memory_id):
            raise ValueError("memory_mutation_unresolved")
        remote = self.client.get(memory_id)
        provenance = remote.get("provenance", {})
        if (remote.get("memory_id") != memory_id
                or remote.get("lifecycle") not in (
                    ("active",) if action == "supersede" else ("active", "superseded"))
                or remote.get("memory_type") not in {"profile", "semantic"}
                or not isinstance(provenance, dict)
                or provenance.get("source_system") != "jarvis"
                or provenance.get("origin_kind") != "user_asserted"
                or provenance.get("source_ref") != f"memory-operation:{owner['id']}"
                or not isinstance(remote.get("content"), str)
                or not isinstance(remote.get("scope"), str)):
            raise ValueError("personal_memory_identity_or_state_mismatch")
        return {
            "memory_id": memory_id,
            "scope": remote["scope"],
            "memory_type": remote["memory_type"],
            "lifecycle": remote["lifecycle"],
            "content": remote["content"],
            "source_ref": provenance["source_ref"],
        }

    def _execute(self, operation_id: str, command, acknowledged) -> dict:
        # The journal must be committed before the external effect.
        self.journal.claim(operation_id)
        try:
            result = acknowledged(command())
            return result
        except CognitiveMemoryError as exc:
            unknown = exc.code == "RESULT_UNKNOWN"
            self.journal.resolve(
                operation_id, status="unknown" if unknown else "rejected",
                error_code=exc.code,
            )
            return {"status": "RESULT_UNKNOWN" if unknown else exc.code,
                    "operation_id": operation_id, "retry_automatically": False}
        except Exception:
            try:
                self.journal.resolve(operation_id, status="unknown",
                                     error_code="LOCAL_ERROR")
            except Exception:
                pass
            return {"status": "RESULT_UNKNOWN", "operation_id": operation_id,
                    "retry_automatically": False}

    def _recheck(self, preview: dict, action: str) -> None:
        current = self.preview(preview["memory_id"], action=action)
        if current != preview:
            raise ValueError("memory_changed_since_confirmation")

    @staticmethod
    def _require_typed_consent(
        preview: dict, action: str, confirmation: PersonalMutationAuthorization,
    ) -> None:
        if (not isinstance(confirmation, PersonalMutationAuthorization)
                or confirmation.action != action
                or confirmation.target_memory_id != preview.get("memory_id")):
            raise ValueError("missing_or_mismatched_human_confirmation")

    def supersede(self, confirmed_preview: dict, *, new_content: str,
                  confirmation: PersonalMutationAuthorization) -> dict:
        self._require_typed_consent(confirmed_preview, "supersede", confirmation)
        self._recheck(confirmed_preview, "supersede")
        if looks_like_credential(new_content):
            raise ValueError("sensitive_content_rejected")
        operation_id = str(uuid4())
        provenance = {
            "origin_kind": "user_asserted", "source_system": "jarvis",
            "source_ref": f"memory-operation:{operation_id}",
        }
        _payload(new_content, provenance)  # Validate BEFORE journal/network.
        target = confirmed_preview["memory_id"]
        payload = {
            "idempotency_key": operation_id, "memory_id": target,
            "content": new_content, "provenance": provenance,
        }
        self.journal.prepare(operation_id, self.service_url, payload,
                             kind="user_supersede", target_memory_id=target,
                             confirmation=confirmation)

        def confirmed(reply: dict) -> dict:
            old, new = reply["old"], reply["replacement"]
            new_id = str(UUID(new["memory_id"]))
            if (old.get("memory_id") != target
                    or old.get("lifecycle") != "superseded"
                    or old.get("superseded_by") != new_id
                    or new_id == target
                    or new.get("lifecycle") != "active"
                    or new.get("scope") != confirmed_preview["scope"]
                    or new.get("memory_type") != confirmed_preview["memory_type"]
                    or new.get("content") != new_content.strip()
                    or new.get("provenance", {}).get("source_ref") !=
                    provenance["source_ref"]):
                raise ValueError("invalid_personal_supersede_ack")
            self.journal.resolve(operation_id, status="confirmed",
                                 memory_id=new_id)
            return {"status": "CONFIRMED", "operation_id": operation_id,
                    "old_memory_id": target, "replacement_memory_id": new_id}

        return self._execute(operation_id, lambda: self.client.supersede(
            target, content=new_content, provenance=provenance,
            idempotency_key=operation_id), confirmed)

    def forget(self, confirmed_preview: dict, *,
               confirmation: PersonalMutationAuthorization) -> dict:
        self._require_typed_consent(confirmed_preview, "forget", confirmation)
        self._recheck(confirmed_preview, "forget")
        operation_id = str(uuid4())
        target = confirmed_preview["memory_id"]
        self.journal.prepare(
            operation_id, self.service_url,
            {"idempotency_key": operation_id, "memory_id": target},
            kind="user_forget", target_memory_id=target,
            confirmation=confirmation,
        )

        def confirmed(reply: dict) -> dict:
            if (reply.get("memory_id") != target
                    or reply.get("lifecycle") != "forgotten"
                    or reply.get("scope") is not None
                    or reply.get("content") is not None):
                raise ValueError("invalid_personal_forget_ack")
            self.journal.resolve(operation_id, status="confirmed", memory_id=target)
            return {"status": "CONFIRMED", "operation_id": operation_id,
                    "memory_id": target, "lifecycle": "forgotten"}

        return self._execute(
            operation_id, lambda: self.client.forget(
                target, idempotency_key=operation_id), confirmed)

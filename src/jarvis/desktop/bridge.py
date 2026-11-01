"""Restricted Qt WebChannel bridge for conversations and text replies.

The web UI receives only JSON data and approved methods. Credentials and
database connections remain in Python. The actual provider runs in a QThread.
"""

from __future__ import annotations

from contextlib import closing
from uuid import UUID
from jarvis.memory.personal_confirmation import PersonalMutationGate
from jarvis.memory.sensitive import looks_like_credential
import json
import os
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
from jarvis.config import database_path
from jarvis.desktop.diagnostics import trace
from jarvis.desktop.model_preferences import bootstrap_model, save_preferred_model
from jarvis.conversation.runtime import ConversationRuntime
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.secrets.windows import WindowsCredentialStore


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


class ReplyWorker(QObject):
    delta = Signal(str, str)
    done = Signal(str, str, str, str)
    knowledgeDone = Signal(str, str)
    createProposed = Signal(str, str)
    mutationProposed = Signal(str, str)

    def __init__(self, conversation_id: str, prompt: str, model: str, api_key: str, *,
                 memory_scope: str | None = None,
                 knowledge_dataset: str | None = None,
                 conversational: bool = False):
        super().__init__()
        self.conversation_id = conversation_id
        self.prompt = prompt
        self.model = model
        self.api_key = api_key
        self.memory_scope = memory_scope
        self.knowledge_dataset = knowledge_dataset
        self.conversational = conversational
        self.routing_status = "NOT_REQUESTED"
        self.create_proposal: dict | None = None
        self.mutation_proposal: dict | None = None
        self.direct_create = None
        self.cancelled = threading.Event()

    @Slot()
    def run(self) -> None:
        trace("reply_worker_begin", memory=self.memory_scope is not None,
              knowledge=self.knowledge_dataset is not None)
        result = "completed"
        error_code = ""
        memory_provider = None
        knowledge_provider = None
        runtime = None
        memory_status = "NOT_REQUESTED"
        memory_key = None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, timeout=30.0)
            from jarvis.conversation.grounding import GroundedTextProvider
            from jarvis.conversation.intent import TextIntentRouter
            from jarvis.conversation.create_decision import evaluate_direct_create
            prepared_answer = None
            if self.conversational:
                try:
                    intent = TextIntentRouter(client).classify(
                        model=self.model, utterance=self.prompt,
                    )
                    self.routing_status = "CLASSIFIED"
                    if intent.action == "memory_recall":
                        self.memory_scope = intent.scope or "global"
                    elif intent.action == "knowledge_query":
                        self.knowledge_dataset = "jarvis-knowledge"
                    elif intent.action == "memory_create":
                        decision = evaluate_direct_create(
                            self.prompt, classified_action=intent.action,
                        )
                        if decision.result == "PERMITTED":
                            if intent.scope is not None and intent.scope != decision.scope:
                                prepared_answer = (
                                    "Não consegui determinar um escopo consistente "
                                    "para guardar essa informação. Não gravei nada."
                                )
                            else:
                                # The actual user message will be durably recorded
                                # before evaluating its authority again in Core.
                                self.direct_create = decision
                        elif decision.result == "CLARIFY":
                            prepared_answer = (
                                "Essa informação vale como preferência geral ou "
                                "somente para o projeto JARVIS? Especifique o "
                                "contexto ao repetir o pedido; ainda não gravei nada."
                            )
                        else:
                            prepared_answer = (
                                "Não consegui validar esse pedido de memória "
                                "como uma instrução direta e segura. "
                                "Nenhuma informação foi gravada."
                            )
                    elif intent.action == "reminder_request":
                        prepared_answer = (
                            "Entendi que você quer um lembrete agendado. "
                            "O scheduler e as notificações ainda não estão disponíveis "
                            "nesta versão. Não agendei nenhum lembrete."
                        )
                    elif intent.action in {"memory_update", "memory_forget"}:
                        try:
                            from jarvis.memory.cognitive import CognitiveMemoryClient
                            from jarvis.memory.connection import configured_memory_url
                            from jarvis.memory.journal import MemoryOperationJournal
                            from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

                            memory_url = configured_memory_url()
                            memory_key = (
                                WindowsCredentialStore().get_memory_key()
                                if memory_url else None
                            )
                            if not memory_url or not memory_key:
                                raise ValueError("memory_not_configured")
                            reader = CognitiveMemoryClient(memory_url, memory_key)
                            lifecycle = PersonalMemoryLifecycle(
                                reader, MemoryOperationJournal(database_path()), memory_url,
                            )
                            action = (
                                "supersede" if intent.action == "memory_update"
                                else "forget"
                            )
                            scopes = (
                                [intent.scope] if intent.scope
                                else ["global", "project:jarvis"]
                            )
                            preview = lifecycle.resolve_preview(
                                self.prompt, action=action, scopes=scopes,
                            )
                            replacement = intent.content if action == "supersede" else ""
                            if (action == "supersede"
                                    and (not isinstance(replacement, str)
                                         or not replacement.strip()
                                         or looks_like_credential(replacement))):
                                raise ValueError("invalid_or_sensitive_replacement")
                            self.mutation_proposal = {
                                "action": action,
                                "memory_id": preview["memory_id"],
                                "replacement": replacement or "",
                            }
                            prepared_answer = (
                                "Encontrei uma memória correspondente. "
                                "Revise a prévia antes de confirmar a alteração."
                            )
                        except ValueError as exc:
                            reason = str(exc)
                            if reason == "memory_target_ambiguous":
                                prepared_answer = (
                                    "Encontrei mais de uma memória possível. "
                                    "Especifique melhor qual informação você quer "
                                    "alterar ou esquecer. Nenhuma memória foi modificada."
                                )
                            elif reason == "memory_target_not_found":
                                prepared_answer = (
                                    "Não encontrei uma memória ativa e pertencente "
                                    "a esta instalação que corresponda ao pedido. "
                                    "Nenhuma memória foi modificada."
                                )
                            else:
                                prepared_answer = (
                                    "Não consegui preparar essa alteração com segurança. "
                                    "Nenhuma memória foi modificada."
                                )
                        except Exception as exc:
                            trace("natural_memory_target_resolution_failed",
                                  error_class=type(exc).__name__)
                            prepared_answer = (
                                "O Sofias Memory não está disponível para resolver "
                                "essa alteração agora. Nenhuma memória foi modificada."
                            )
                except Exception as exc:
                    self.routing_status = "UNAVAILABLE"
                    trace("conversational_router_unavailable",
                          error_class=type(exc).__name__)
                    # Fail closed for ambiguous intent: do not pass a possible
                    # write request to a generic reply that might claim success.
                    prepared_answer = (
                        "Não consegui interpretar este pedido com segurança agora. "
                        "Nenhuma memória, tarefa ou agendamento foi modificado. "
                        "Tente novamente quando o roteamento estiver disponível."
                    )

            if self.direct_create is not None:
                decision = self.direct_create

                class DirectCreateProvider:
                    """Execute exactly the owner's current stored utterance."""

                    def stream_text(inner_self, *, model, messages):
                        from jarvis.memory.cognitive import CognitiveMemoryClient
                        from jarvis.memory.connection import configured_memory_url
                        from jarvis.memory.personal_confirmation import PersonalMutationAuthorization
                        from jarvis.memory.journal import MemoryOperationJournal
                        from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

                        try:
                            if self.cancelled.is_set() or runtime is None:
                                yield "Pedido interrompido antes da gravação."
                                return
                            message_id = runtime.last_user_message_id
                            if message_id is None:
                                raise ValueError("missing_verified_user_message")
                            url = configured_memory_url()
                            if not url:
                                yield ("O Sofias Memory não está configurado. "
                                       "Nenhuma gravação foi executada.")
                                return
                            key = WindowsCredentialStore().get_memory_key()
                            if not key:
                                yield ("Não foi possível acessar a credencial "
                                       "de memória. Nenhuma gravação foi executada.")
                                return
                            reader = CognitiveMemoryClient(url, key)
                            if reader.diagnose().get("status") != "COMPATIBLE":
                                yield ("O Sofias Memory está incompatível. "
                                       "Nenhuma gravação foi iniciada.")
                                return
                            consent = PersonalMutationAuthorization.from_explicit_user_message(
                                action="create", conversation_id=self.conversation_id,
                                message_id=message_id,
                            )
                            service = PersonalMemoryLifecycle(
                                reader, MemoryOperationJournal(database_path()), url,
                            )
                            if self.cancelled.is_set():
                                yield "Pedido interrompido antes da gravação."
                                return
                            reply = service.create(
                                content=decision.content, scope=decision.scope,
                                conversation_id=self.conversation_id,
                                confirmation=consent,
                            )
                            if reply.get("status") == "CONFIRMED":
                                yield (
                                    "Guardei essa informação no Sofias Memory "
                                    + ("para o projeto JARVIS." if decision.scope == "project:jarvis"
                                       else "como preferência geral.")
                                )
                            elif reply.get("status") == "RESULT_UNKNOWN":
                                yield (
                                    "O Sofias Memory não confirmou o resultado. "
                                    "Não vou repetir automaticamente a gravação; "
                                    "é necessário verificar o journal."
                                )
                            else:
                                yield (
                                    "O Sofias Memory não confirmou a gravação "
                                    f"({reply.get('status', 'FAILED')}). "
                                    "Não registrei essa informação como concluída."
                                )
                        except Exception as exc:
                            trace("direct_memory_create_failed",
                                  error_class=type(exc).__name__)
                            yield (
                                "Não consegui confirmar o registro da memória. "
                                "Não repita automaticamente; verifique o journal "
                                "antes de uma nova tentativa."
                            )

                provider = DirectCreateProvider()
            elif prepared_answer is not None:
                class StaticAnswer:
                    def stream_text(self, *, model, messages):
                        yield prepared_answer
                provider = StaticAnswer()
            else:
                provider = GroundedTextProvider(OpenAIResponsesAdapter(client))

            if self.memory_scope is not None:
                from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError
                from jarvis.memory.connection import configured_memory_url
                from jarvis.memory.context import MemoryAwareTextProvider

                try:
                    memory_url = configured_memory_url()
                    memory_key = WindowsCredentialStore().get_memory_key() if memory_url else None
                except Exception:
                    memory_url = None
                    memory_key = None

                if memory_url and memory_key:
                    reader = CognitiveMemoryClient(memory_url, memory_key)
                else:
                    class UnavailableReader:
                        def recall(self, **kwargs):
                            raise CognitiveMemoryError("SERVICE_UNAVAILABLE")
                    reader = UnavailableReader()

                memory_provider = MemoryAwareTextProvider(
                    provider, reader, scopes=[self.memory_scope],
                )
                provider = memory_provider
                memory_status = "NOT_ATTEMPTED"

            if self.knowledge_dataset is not None:
                from jarvis.memory.connection import configured_memory_url
                from jarvis.memory.knowledge import KnowledgeClient, KnowledgeError
                from jarvis.memory.knowledge_context import KnowledgeAwareTextProvider

                try:
                    knowledge_url = configured_memory_url()
                    knowledge_key = (WindowsCredentialStore().get_memory_key()
                                     if knowledge_url else None)
                except Exception:
                    knowledge_url = None
                    knowledge_key = None

                if knowledge_url and knowledge_key:
                    knowledge_reader = KnowledgeClient(knowledge_url, knowledge_key)
                else:
                    class UnavailableKnowledgeReader:
                        def list_datasets(self, **kwargs):
                            raise KnowledgeError("SERVICE_UNAVAILABLE")

                        def query_chunks(self, **kwargs):
                            raise KnowledgeError("SERVICE_UNAVAILABLE")
                    knowledge_reader = UnavailableKnowledgeReader()
                knowledge_provider = KnowledgeAwareTextProvider(
                    provider, knowledge_reader, datasets=[self.knowledge_dataset],
                )
                provider = knowledge_provider

            store = SQLiteConversationStore(database_path())
            runtime = ConversationRuntime(store, provider)
            with closing(runtime.reply(
                conversation_id=self.conversation_id,
                text=self.prompt,
                model=self.model,
            )) as stream:
                for part in stream:
                    if self.cancelled.is_set():
                        result = "interrupted"
                        break
                    self.delta.emit(self.conversation_id, part)
        except Exception as exc:
            result = "failed"
            error_code = type(exc).__name__
        finally:
            if memory_provider is not None:
                memory_status = memory_provider.last_retrieval_status or "NOT_ATTEMPTED"
            if self.knowledge_dataset is not None:
                evidence = {
                    "knowledgeStatus": (knowledge_provider.last_retrieval_status
                                        if knowledge_provider is not None else None)
                                       or "NOT_ATTEMPTED",
                    "queryId": (knowledge_provider.last_query_id
                                if knowledge_provider is not None else None),
                    "references": (knowledge_provider.last_references
                                   if knowledge_provider is not None else []),
                    "dataset": self.knowledge_dataset,
                    "assistantMessageId": (
                        runtime.last_assistant_message_id if runtime is not None else None
                    ),
                    "evidencePersistence": "NOT_SAVED",
                }
                if evidence["assistantMessageId"] is not None:
                    try:
                        # Localized per-message metadata only, no chunk content.
                        SQLiteConversationStore(database_path()).save_knowledge_evidence(
                            evidence["assistantMessageId"],
                            dataset=self.knowledge_dataset,
                            knowledge_status=evidence["knowledgeStatus"],
                            query_id=evidence["queryId"],
                            references=evidence["references"],
                        )
                        evidence["evidencePersistence"] = "SAVED"
                    except Exception as exc:
                        trace("knowledge_evidence_persistence_failed",
                              error_class=type(exc).__name__)
                        # No unsaved references can be presented as durable.
                        evidence["references"] = []
                        evidence["evidencePersistence"] = "FAILED"
                self.knowledgeDone.emit(self.conversation_id, _json(evidence))
            self.api_key = ""
            memory_key = None
            knowledge_key = None
            trace("reply_worker_end", result=result, error_class=error_code,
                  memory_status=memory_status,
                  knowledge=self.knowledge_dataset is not None)
            if result == "completed" and self.create_proposal is not None:
                self.createProposed.emit(
                    self.conversation_id, _json(self.create_proposal),
                )
            if result == "completed" and self.mutation_proposal is not None:
                self.mutationProposed.emit(
                    self.conversation_id, _json(self.mutation_proposal),
                )
            self.done.emit(self.conversation_id, result, error_code, memory_status)

class MemoryPreviewWorker(QObject):
    """Read-only remote preview; no mutation methods or execution token."""
    finishedPreview = Signal(str)

    def __init__(self, action: str, memory_id: str, *,
                 replacement: str = "", conversation_id: str | None = None,
                 approval_mode: str = "typed"):
        super().__init__()
        if approval_mode not in {"typed", "click"}:
            raise ValueError("invalid_approval_mode")
        self.action = action
        self.memory_id = memory_id
        self.replacement = replacement
        self.conversation_id = conversation_id
        self.approval_mode = approval_mode
        self.full_preview: dict | None = None

    @Slot()
    def run(self) -> None:
        trace("memory_preview_begin")
        try:
            from jarvis.memory.cognitive import CognitiveMemoryClient
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.journal import MemoryOperationJournal
            from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

            url = configured_memory_url()
            if not url:
                raise ValueError("memory_not_configured")
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                raise ValueError("memory_key_missing")
            client = CognitiveMemoryClient(url, key)
            if client.diagnose().get("status") != "COMPATIBLE":
                raise ValueError("memory_contract_incompatible")
            lifecycle = PersonalMemoryLifecycle(
                client, MemoryOperationJournal(database_path()), url,
            )
            preview = lifecycle.preview(self.memory_id, action=self.action)
            self.full_preview = preview
            result = {"ok": True, "action": self.action, "preview": {
                "memory_id": preview["memory_id"],
                "memory_type": preview["memory_type"],
                "scope": preview["scope"],
                "lifecycle": preview["lifecycle"],
                "content": preview["content"],
            }}
        except Exception as exc:
            # Never send SDK exceptions, provider errors or credentials to UI.
            result = {"ok": False, "error": type(exc).__name__}
        trace("memory_preview_end", ok=bool(result["ok"]))
        self.finishedPreview.emit(_json(result))


class MemoryMutationWorker(QObject):
    """Executes precisely one consumed owner-confirmed operation on its own thread."""
    finishedMutation = Signal(str)

    def __init__(self, pending):
        super().__init__()
        self.pending = pending

    @Slot()
    def run(self) -> None:
        trace("personal_mutation_begin", action=self.pending.action)
        try:
            from jarvis.memory.cognitive import CognitiveMemoryClient
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.journal import MemoryOperationJournal
            from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

            url = configured_memory_url()
            if not url:
                raise ValueError("memory_not_configured")
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                raise ValueError("memory_key_missing")
            client = CognitiveMemoryClient(url, key)
            if client.diagnose().get("status") != "COMPATIBLE":
                raise ValueError("memory_contract_incompatible")
            lifecycle = PersonalMemoryLifecycle(
                client, MemoryOperationJournal(database_path()), url,
            )
            if self.pending.authorization is None:
                raise ValueError("missing_human_confirmation")
            result = (lifecycle.supersede(
                          self.pending.preview,
                          new_content=self.pending.replacement,
                          confirmation=self.pending.authorization,
                      ) if self.pending.action == "supersede"
                      else lifecycle.forget(
                          self.pending.preview,
                          confirmation=self.pending.authorization,
                      ))
            safe = {
                "ok": result.get("status") == "CONFIRMED",
                "status": result.get("status", "RESULT_UNKNOWN"),
                "operationId": result.get("operation_id"),
                "memoryId": result.get("memory_id"),
                "replacementMemoryId": result.get("replacement_memory_id"),
                "retryAutomatically": False,
            }
        except Exception as exc:
            # Never propagate raw exceptions, SDK errors, prompts or credentials.
            safe = {"ok": False, "status": "NOT_CONFIRMED",
                    "error": type(exc).__name__, "retryAutomatically": False}
        trace("personal_mutation_end", ok=bool(safe["ok"]), action=self.pending.action)
        self.finishedMutation.emit(_json(safe))


class ConversationalCreateWorker(QObject):
    """One approved Cognitive Create; no LLM or Qt WebView controls the write."""
    finishedMutation = Signal(str)

    def __init__(self, pending):
        super().__init__()
        self.pending = pending

    @Slot()
    def run(self) -> None:
        trace("conversational_create_begin")
        try:
            from jarvis.memory.cognitive import CognitiveMemoryClient
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.journal import MemoryOperationJournal
            from jarvis.memory.personal_lifecycle import PersonalMemoryLifecycle

            url = configured_memory_url()
            if not url:
                raise ValueError("memory_not_configured")
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                raise ValueError("memory_key_missing")
            client = CognitiveMemoryClient(url, key)
            if client.diagnose().get("status") != "COMPATIBLE":
                raise ValueError("memory_contract_incompatible")
            lifecycle = PersonalMemoryLifecycle(
                client, MemoryOperationJournal(database_path()), url,
            )
            result = lifecycle.create(
                content=self.pending.content, scope=self.pending.scope,
                conversation_id=self.pending.conversation_id,
                confirmation=self.pending.authorization,
            )
            payload = {
                "action": "create",
                "ok": result.get("status") == "CONFIRMED",
                "status": result.get("status", "RESULT_UNKNOWN"),
                "operationId": result.get("operation_id"),
                "memoryId": result.get("memory_id"),
                "scope": result.get("scope"),
                "retryAutomatically": False,
            }
            if payload["ok"]:
                # Only a confirmed remote write may be described as saved.
                # Store an operational acknowledgement, not the sensitive
                # memory content, and never mask success if SQLite fails here.
                try:
                    store = SQLiteConversationStore(database_path())
                    text = ("Informação guardada no Sofias Memory "
                            + ("como preferência geral." if self.pending.scope == "global"
                               else "para o projeto JARVIS."))
                    message_id = store.begin_assistant_message(
                        self.pending.conversation_id,
                    )
                    store.append_assistant_delta(message_id, text)
                    store.end_assistant_message(message_id, successful=True)
                    payload["transcriptPersisted"] = True
                except Exception as exc:
                    trace("create_transcript_ack_failed",
                          error_class=type(exc).__name__)
                    payload["transcriptPersisted"] = False
        except Exception as exc:
            payload = {
                "action": "create", "ok": False, "status": "NOT_CONFIRMED",
                "error": type(exc).__name__, "retryAutomatically": False,
            }
        trace("conversational_create_end", ok=bool(payload["ok"]))
        self.finishedMutation.emit(_json(payload))


class JarvisBridge(QObject):
    streamEvent = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._store = SQLiteConversationStore(database_path())
        self._worker: ReplyWorker | None = None
        self._thread: QThread | None = None
        self._closing = False
        self._window = None
        self._preview_worker: MemoryPreviewWorker | None = None
        self._preview_thread: QThread | None = None
        self._mutation_gate = PersonalMutationGate()
        from jarvis.memory.personal_confirmation import PersonalCreateGate
        self._create_gate = PersonalCreateGate()
        self._deferred_create_proposal: dict | None = None
        self._deferred_mutation_proposal: dict | None = None
        self._mutation_thread: QThread | None = None
        self._mutation_worker: MemoryMutationWorker | None = None

    def attach_window(self, window) -> None:
        self._window = window

    @property
    def active(self) -> bool:
        return (self._thread is not None or self._preview_thread is not None
                or self._mutation_thread is not None)

    @Slot(result=str)
    def bootstrap(self) -> str:
        try:
            has_key = bool(WindowsCredentialStore().get_openai_key())
        except Exception:
            has_key = False
        from jarvis.memory.connection import configured_memory_url

        try:
            memory_configured = bool(
                configured_memory_url() and WindowsCredentialStore().get_memory_key()
            )
        except Exception:
            memory_configured = False
        return _json({
            "ok": True,
            "memoryConfigured": memory_configured,
            "conversations": self._store.list_conversations(),
            "model": bootstrap_model(),
            "credentialConfigured": has_key,
        })

    @Slot(result=str)
    def createConversation(self) -> str:
        return _json({"ok": True, "id": self._store.create_conversation()})

    @Slot(result=str)
    def listConversations(self) -> str:
        return _json({"ok": True, "items": self._store.list_conversations()})

    @Slot(str, result=str)
    def deleteConversation(self, conversation_id: str) -> str:
        """Owner-requested local transcript deletion; never deletes Memory."""
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        from uuid import UUID
        try:
            if str(UUID(conversation_id)) != conversation_id:
                return _json({"ok": False, "error": "invalid_conversation"})
        except (TypeError, ValueError, AttributeError):
            return _json({"ok": False, "error": "invalid_conversation"})
        self._mutation_gate.clear()
        self._create_gate.clear()
        deleted = self._store.delete_conversation(conversation_id)
        return _json({"ok": deleted, "error": None if deleted else "unknown_conversation"})

    @Slot(str, result=str)
    def listMessages(self, conversation_id: str) -> str:
        try:
            return _json({"ok": True, "items": self._store.list_messages(conversation_id)})
        except KeyError:
            return _json({"ok": False, "error": "unknown_conversation"})

    @Slot(str, str, str, result=str)
    def sendConversationalMessage(
        self, conversation_id: str, prompt: str, model: str,
    ) -> str:
        """Single natural-language entry. The classifier never authorizes writes."""
        return self._dispatch(
            conversation_id, prompt, model, memory_scope=None,
            knowledge_dataset=None, conversational=True,
        )

    @Slot(str, str, str, result=str)
    def sendMessage(self, conversation_id: str, prompt: str, model: str) -> str:
        """Original TB-01 text-only path. No memory access."""
        return self._dispatch(conversation_id, prompt, model, memory_scope=None,
                              knowledge_dataset=None)

    @Slot(str, str, str, str, result=str)
    def sendMessageWithMemory(
        self, conversation_id: str, prompt: str, model: str, memory_scope: str,
    ) -> str:
        """Read-only contextual retrieval with the user's explicit scope."""
        from jarvis.memory.cognitive import _scope

        try:
            validated_scope = _scope(memory_scope)
        except ValueError:
            return _json({"ok": False, "error": "invalid_memory_scope"})
        return self._dispatch(conversation_id, prompt, model, memory_scope=validated_scope,
                              knowledge_dataset=None)

    @Slot(str, str, str, str, str, result=str)
    def sendMessageWithContext(
        self, conversation_id: str, prompt: str, model: str,
        memory_scope: str, knowledge_dataset: str,
    ) -> str:
        """Explicit per-turn opt-in for Cognitive Memory and/or Knowledge."""
        from jarvis.memory.cognitive import _scope

        if not memory_scope and not knowledge_dataset:
            return _json({"ok": False, "error": "context_not_selected"})
        try:
            validated_scope = _scope(memory_scope) if memory_scope else None
        except ValueError:
            return _json({"ok": False, "error": "invalid_memory_scope"})
        if knowledge_dataset and knowledge_dataset != "jarvis-knowledge":
            return _json({"ok": False, "error": "invalid_knowledge_dataset"})
        return self._dispatch(conversation_id, prompt, model,
                              memory_scope=validated_scope,
                              knowledge_dataset=knowledge_dataset or None)

    @Slot(str, str, result=str)
    def previewPersonalMemory(self, action: str, memory_id: str) -> str:
        """Read-only. The UI cannot authorize mutating effects through this slot."""
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        if action not in {"supersede", "forget"}:
            return _json({"ok": False, "error": "invalid_action"})
        try:
            target_id = str(UUID(memory_id))
        except (TypeError, ValueError, AttributeError):
            return _json({"ok": False, "error": "invalid_memory_id"})
        self._mutation_gate.clear()
        worker = MemoryPreviewWorker(action, target_id)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._preview_worker = worker
        self._preview_thread = thread
        thread.started.connect(worker.run)
        worker.finishedPreview.connect(self._on_memory_preview)
        worker.finishedPreview.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_preview_thread_finished)
        trace("memory_preview_thread_starting")
        thread.start()
        return _json({"ok": True, "status": "PREVIEW_REQUESTED"})

    @Slot(str, str, str, str, result=str)
    def previewPersonalMutation(self, action: str, memory_id: str,
                                replacement: str, conversation_id: str) -> str:
        """Start a confirmed-owner preview; no mutation until typed consent."""
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        self._mutation_gate.clear()
        if action not in {"supersede", "forget"}:
            return _json({"ok": False, "error": "invalid_action"})
        try:
            target_id = str(UUID(memory_id))
            conv_id = str(UUID(conversation_id))
        except (TypeError, ValueError, AttributeError):
            return _json({"ok": False, "error": "invalid_identifier"})
        if self._store.get_conversation(conv_id) is None:
            return _json({"ok": False, "error": "unknown_conversation"})
        if (not isinstance(replacement, str)
                or (action == "forget" and replacement)
                or (action == "supersede" and (
                    not replacement.strip() or len(replacement) > 16384
                    or looks_like_credential(replacement)))):
            return _json({"ok": False, "error": "invalid_or_sensitive_replacement"})
        worker = MemoryPreviewWorker(action, target_id,
                                     replacement=replacement,
                                     conversation_id=conv_id)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._preview_worker = worker
        self._preview_thread = thread
        thread.started.connect(worker.run)
        worker.finishedPreview.connect(self._on_memory_preview)
        worker.finishedPreview.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_preview_thread_finished)
        trace("personal_preview_thread_starting", action=action)
        thread.start()
        return _json({"ok": True, "status": "PREVIEW_REQUESTED"})

    @Slot(str, str, str, result=str)
    def confirmPersonalMutation(self, token: str, phrase: str,
                                conversation_id: str) -> str:
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        try:
            pending = self._mutation_gate.consume(token, phrase, conversation_id)
        except (ValueError, KeyError, TypeError):
            return _json({"ok": False, "error": "authorization_invalid_or_expired"})
        worker = MemoryMutationWorker(pending)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._mutation_worker = worker
        self._mutation_thread = thread
        thread.started.connect(worker.run)
        worker.finishedMutation.connect(self._on_memory_mutation)
        worker.finishedMutation.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_mutation_thread_finished)
        trace("personal_mutation_thread_starting", action=pending.action)
        thread.start()
        return _json({"ok": True, "status": "MUTATION_REQUESTED"})

    @Slot(str, str, result=str)
    def approvePersonalMutation(self, token: str, conversation_id: str) -> str:
        """Approve one natural-language mutation after its exact target preview."""
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        try:
            pending = self._mutation_gate.approve(token, conversation_id)
        except (ValueError, KeyError, TypeError):
            return _json({"ok": False, "error": "authorization_invalid_or_expired"})
        worker = MemoryMutationWorker(pending)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._mutation_worker = worker
        self._mutation_thread = thread
        thread.started.connect(worker.run)
        worker.finishedMutation.connect(self._on_memory_mutation)
        worker.finishedMutation.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_mutation_thread_finished)
        trace("personal_mutation_thread_starting", action=pending.action)
        thread.start()
        return _json({"ok": True, "status": "MUTATION_REQUESTED"})

    @Slot(str, str, str, result=str)
    def confirmConversationalCreate(self, token: str, conversation_id: str,
                                    scope: str) -> str:
        """A UI approval authorizes one exact, previously previewed Create."""
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        try:
            if self._store.get_conversation(conversation_id) is None:
                return _json({"ok": False, "error": "unknown_conversation"})
            pending = self._create_gate.consume(token, conversation_id, scope)
        except (ValueError, KeyError, TypeError):
            return _json({"ok": False, "error": "approval_invalid_or_expired"})
        worker = ConversationalCreateWorker(pending)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._mutation_worker = worker
        self._mutation_thread = thread
        thread.started.connect(worker.run)
        worker.finishedMutation.connect(self._on_memory_mutation)
        worker.finishedMutation.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_mutation_thread_finished)
        trace("conversational_create_thread_starting")
        thread.start()
        return _json({"ok": True, "status": "CREATE_REQUESTED"})

    @Slot(result=str)
    def cancelConversationalCreate(self) -> str:
        if self._mutation_thread is not None:
            return _json({"ok": False, "error": "mutation_in_progress"})
        self._create_gate.clear()
        return _json({"ok": True, "status": "CANCELLED"})

    @Slot(result=str)
    def cancelPendingPersonalMutation(self) -> str:
        if self._mutation_thread is not None:
            return _json({"ok": False, "error": "mutation_in_progress"})
        self._mutation_gate.clear()
        return _json({"ok": True, "status": "CANCELLED"})

    @Slot(str)
    def _on_memory_mutation(self, raw_result: str) -> None:
        try:
            payload = json.loads(raw_result)
        except (ValueError, TypeError):
            payload = {"ok": False, "status": "RESULT_UNKNOWN",
                       "retryAutomatically": False}
        self.streamEvent.emit(_json({"type": "memory_mutation", **payload}))

    @Slot()
    def _on_mutation_thread_finished(self) -> None:
        trace("personal_mutation_thread_finished",
              in_gui_thread=QThread.currentThread() == self.thread())
        thread = self._mutation_thread
        if thread is None:
            return
        self._mutation_thread = None
        self._mutation_worker = None
        thread.deleteLater()
        if self._closing and self._window is not None and not self.active:
            QTimer.singleShot(0, self._window.close)

    @Slot(str)
    def _on_memory_preview(self, raw_result: str) -> None:
        try:
            data = json.loads(raw_result)
        except (ValueError, TypeError):
            data = {"ok": False, "error": "invalid_preview_result"}
        worker = self._preview_worker
        if (data.get("ok") and worker is not None
                and worker.conversation_id is not None
                and worker.full_preview is not None):
            try:
                token, phrase = self._mutation_gate.offer(
                    worker.action, worker.full_preview, worker.replacement,
                    worker.conversation_id,
                )
                data.update({
                    "authorizationToken": token,
                    "requiredPhrase": (
                        phrase if worker.approval_mode == "typed" else None
                    ),
                    "approvalMode": worker.approval_mode,
                    "conversationId": worker.conversation_id,
                })
            except (ValueError, KeyError, TypeError):
                self._mutation_gate.clear()
                data = {"ok": False, "error": "preview_authorization_invalid"}
        self.streamEvent.emit(_json({"type": "memory_preview", **data}))

    @Slot()
    def _on_preview_thread_finished(self) -> None:
        trace("memory_preview_thread_finished",
              in_gui_thread=QThread.currentThread() == self.thread())
        thread = self._preview_thread
        if thread is None:
            return
        self._preview_thread = None
        self._preview_worker = None
        thread.deleteLater()
        if self._closing and self._window is not None and not self.active:
            QTimer.singleShot(0, self._window.close)

    def _dispatch(
        self, conversation_id: str, prompt: str, model: str, *,
        memory_scope: str | None,
        knowledge_dataset: str | None,
        conversational: bool = False,
    ) -> str:
        trace("bridge_dispatch_requested", worker_active=self.active,
              memory=memory_scope is not None, knowledge=knowledge_dataset is not None)
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
        self._create_gate.clear()
        self._deferred_create_proposal = None
        self._deferred_mutation_proposal = None
        if not model.strip() or not prompt.strip():
            return _json({"ok": False, "error": "missing_text_or_model"})
        if self._store.get_conversation(conversation_id) is None:
            return _json({"ok": False, "error": "unknown_conversation"})
        try:
            key = WindowsCredentialStore().get_openai_key()
        except Exception:
            return _json({"ok": False, "error": "secure_vault_unavailable"})
        if not key:
            return _json({"ok": False, "error": "credential_not_configured"})

        worker = ReplyWorker(
            conversation_id, prompt.strip(), model.strip(), key,
            memory_scope=memory_scope,
            knowledge_dataset=knowledge_dataset,
            conversational=conversational,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        self._worker = worker
        self._thread = thread
        thread.started.connect(worker.run)
        thread.started.connect(self._on_thread_started)
        worker.delta.connect(self._on_delta)
        worker.done.connect(self._on_done)
        worker.knowledgeDone.connect(self._on_knowledge_done)
        worker.createProposed.connect(self._on_conversational_create_proposed)
        worker.mutationProposed.connect(self._on_conversational_mutation_proposed)
        worker.done.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        trace("bridge_thread_starting")
        thread.start()
        # This is a desktop preference, not the cognitive memory store.
        # Do not abort an accepted reply if the local preference write fails.
        try:
            save_preferred_model(model.strip())
        except (OSError, ValueError) as exc:
            trace("desktop_model_preference_write_failed",
                  error_class=type(exc).__name__)
        trace("bridge_thread_started_request")
        return _json({"ok": True, "conversationId": conversation_id})

    @Slot()
    def _on_thread_started(self) -> None:
        trace("bridge_thread_started")

    @Slot(str, str)
    def _on_delta(self, conversation_id: str, delta: str) -> None:
        self.streamEvent.emit(_json({
            "type": "delta", "conversationId": conversation_id, "text": delta,
        }))

    @Slot(str, str)
    def _on_knowledge_done(self, conversation_id: str, raw_evidence: str) -> None:
        try:
            data = json.loads(raw_evidence)
        except ValueError:
            return
        if not isinstance(data, dict):
            return
        self.streamEvent.emit(_json({
            "type": "knowledge",
            "conversationId": conversation_id,
            "knowledgeStatus": data.get("knowledgeStatus", "NOT_ATTEMPTED"),
            "queryId": data.get("queryId"),
            "references": data.get("references", []),
            "dataset": data.get("dataset"),
            "assistantMessageId": data.get("assistantMessageId"),
            "evidencePersistence": data.get("evidencePersistence", "NOT_SAVED"),
        }))

    @Slot(str, str)
    def _on_conversational_create_proposed(
        self, conversation_id: str, raw_proposal: str,
    ) -> None:
        if self._closing or self._store.get_conversation(conversation_id) is None:
            self._create_gate.clear()
            return
        try:
            proposal = json.loads(raw_proposal)
            if not isinstance(proposal, dict) or set(proposal) != {"content", "scope"}:
                raise ValueError("invalid_create_proposal")
            token = self._create_gate.offer(
                content=proposal["content"],
                scope=proposal["scope"],
                conversation_id=conversation_id,
            )
            payload = {
                "type": "create_proposal", "ok": True,
                "conversationId": conversation_id,
                "content": proposal["content"], "scope": proposal["scope"],
                "authorizationToken": token,
            }
        except (ValueError, KeyError, TypeError):
            self._create_gate.clear()
            payload = {
                "type": "create_proposal", "ok": False,
                "conversationId": conversation_id,
                "error": "invalid_or_sensitive_create_proposal",
            }
        if self._thread is None:
            self.streamEvent.emit(_json(payload))
        else:
            # Do not offer a clickable write button until the reply thread
            # is fully quiescent. Otherwise confirm may race the busy gate.
            self._deferred_create_proposal = payload

    @Slot(str, str, str, str)
    def _on_done(self, conversation_id: str, result: str, error_code: str,
                 memory_status: str) -> None:
        trace("bridge_worker_done_received", result=result, error_class=error_code)
        self.streamEvent.emit(_json({
            "type": "done", "conversationId": conversation_id,
            "status": result, "error": error_code,
            "memoryStatus": memory_status,
            "routingStatus": (
                self._worker.routing_status if self._worker is not None else "NOT_REQUESTED"
            ),
        }))


    @Slot()
    def _on_thread_finished(self) -> None:
        """QThread.finished is delivered to this bridge on its GUI thread."""
        trace("bridge_thread_finished", in_gui_thread=QThread.currentThread() == self.thread())
        thread = self._thread
        if thread is None:
            return
        self._thread = None
        self._worker = None
        thread.deleteLater()
        pending = self._deferred_create_proposal
        self._deferred_create_proposal = None
        if pending is not None:
            if (not self._closing and self._store.get_conversation(
                    pending["conversationId"]) is not None):
                self.streamEvent.emit(_json(pending))
            else:
                self._create_gate.clear()
        if self._closing and self._window is not None and not self.active:
            QTimer.singleShot(0, self._window.close)

    def request_shutdown(self) -> None:
        self._create_gate.clear()
        self._deferred_create_proposal = None
        trace("bridge_shutdown_requested", worker_active=self.active)
        self._mutation_gate.clear()
        self._closing = True
        if self._worker is not None:
            self._worker.cancelled.set()

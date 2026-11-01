"""Restricted Qt WebChannel bridge for conversations and text replies.

The web UI receives only JSON data and approved methods. Credentials and
database connections remain in Python. The actual provider runs in a QThread.
"""

from __future__ import annotations

from contextlib import closing
from uuid import UUID
import json
import os
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
from jarvis.config import database_path
from jarvis.desktop.diagnostics import trace
from jarvis.conversation.runtime import ConversationRuntime
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.secrets.windows import WindowsCredentialStore


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


class ReplyWorker(QObject):
    delta = Signal(str, str)
    done = Signal(str, str, str, str)
    knowledgeDone = Signal(str, str)

    def __init__(self, conversation_id: str, prompt: str, model: str, api_key: str, *,
                 memory_scope: str | None = None,
                 knowledge_dataset: str | None = None):
        super().__init__()
        self.conversation_id = conversation_id
        self.prompt = prompt
        self.model = model
        self.api_key = api_key
        self.memory_scope = memory_scope
        self.knowledge_dataset = knowledge_dataset
        self.cancelled = threading.Event()

    @Slot()
    def run(self) -> None:
        trace("reply_worker_begin", memory=self.memory_scope is not None,
              knowledge=self.knowledge_dataset is not None)
        result = "completed"
        error_code = ""
        memory_provider = None
        knowledge_provider = None
        memory_status = "NOT_REQUESTED"
        memory_key = None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, timeout=30.0)
            from jarvis.conversation.grounding import GroundedTextProvider

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
                }
                self.knowledgeDone.emit(self.conversation_id, _json(evidence))
            self.api_key = ""
            memory_key = None
            knowledge_key = None
            trace("reply_worker_end", result=result, error_class=error_code,
                  memory_status=memory_status,
                  knowledge=self.knowledge_dataset is not None)
            self.done.emit(self.conversation_id, result, error_code, memory_status)

class MemoryPreviewWorker(QObject):
    """Read-only remote preview; no mutation methods or execution token."""
    finishedPreview = Signal(str)

    def __init__(self, action: str, memory_id: str):
        super().__init__()
        self.action = action
        self.memory_id = memory_id

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

    def attach_window(self, window) -> None:
        self._window = window

    @property
    def active(self) -> bool:
        return self._thread is not None or self._preview_thread is not None

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
            "model": os.getenv("JARVIS_MODEL", ""),
            "credentialConfigured": has_key,
        })

    @Slot(result=str)
    def createConversation(self) -> str:
        return _json({"ok": True, "id": self._store.create_conversation()})

    @Slot(result=str)
    def listConversations(self) -> str:
        return _json({"ok": True, "items": self._store.list_conversations()})

    @Slot(str, result=str)
    def listMessages(self, conversation_id: str) -> str:
        try:
            return _json({"ok": True, "items": self._store.list_messages(conversation_id)})
        except KeyError:
            return _json({"ok": False, "error": "unknown_conversation"})

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

    @Slot(str)
    def _on_memory_preview(self, raw_result: str) -> None:
        try:
            data = json.loads(raw_result)
        except (ValueError, TypeError):
            data = {"ok": False, "error": "invalid_preview_result"}
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
    ) -> str:
        trace("bridge_dispatch_requested", worker_active=self.active,
              memory=memory_scope is not None, knowledge=knowledge_dataset is not None)
        if self.active or self._closing:
            return _json({"ok": False, "error": "busy"})
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
        worker.done.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        trace("bridge_thread_starting")
        thread.start()
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
        }))

    @Slot(str, str, str, str)
    def _on_done(self, conversation_id: str, result: str, error_code: str,
                 memory_status: str) -> None:
        trace("bridge_worker_done_received", result=result, error_class=error_code)
        self.streamEvent.emit(_json({
            "type": "done", "conversationId": conversation_id,
            "status": result, "error": error_code,
            "memoryStatus": memory_status,
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
        if self._closing and self._window is not None and not self.active:
            QTimer.singleShot(0, self._window.close)

    def request_shutdown(self) -> None:
        trace("bridge_shutdown_requested", worker_active=self.active)
        self._closing = True
        if self._worker is not None:
            self._worker.cancelled.set()

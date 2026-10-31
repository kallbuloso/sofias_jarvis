"""Restricted Qt WebChannel bridge for conversations and text replies.

The web UI receives only JSON data and approved methods. Credentials and
database connections remain in Python. The actual provider runs in a QThread.
"""

from __future__ import annotations

from contextlib import closing
import json
import os
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
from jarvis.config import database_path
from jarvis.conversation.runtime import ConversationRuntime
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.secrets.windows import WindowsCredentialStore


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


class ReplyWorker(QObject):
    delta = Signal(str, str)
    done = Signal(str, str, str, str)

    def __init__(self, conversation_id: str, prompt: str, model: str, api_key: str, *,
                 memory_scope: str | None = None):
        super().__init__()
        self.conversation_id = conversation_id
        self.prompt = prompt
        self.model = model
        self.api_key = api_key
        self.memory_scope = memory_scope
        self.cancelled = threading.Event()

    @Slot()
    def run(self) -> None:
        result = "completed"
        error_code = ""
        memory_provider = None
        memory_status = "NOT_REQUESTED"
        memory_key = None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, timeout=30.0)
            provider = OpenAIResponsesAdapter(client)

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
            self.api_key = ""
            memory_key = None
            self.done.emit(self.conversation_id, result, error_code, memory_status)

class JarvisBridge(QObject):
    streamEvent = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._store = SQLiteConversationStore(database_path())
        self._worker: ReplyWorker | None = None
        self._thread: QThread | None = None
        self._closing = False
        self._window = None

    def attach_window(self, window) -> None:
        self._window = window

    @property
    def active(self) -> bool:
        return self._thread is not None

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
        return self._dispatch(conversation_id, prompt, model, memory_scope=None)

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
        return self._dispatch(conversation_id, prompt, model, memory_scope=validated_scope)

    def _dispatch(
        self, conversation_id: str, prompt: str, model: str, *,
        memory_scope: str | None,
    ) -> str:
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
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        self._worker = worker
        self._thread = thread
        thread.started.connect(worker.run)
        worker.delta.connect(self._on_delta)
        worker.done.connect(self._on_done)
        worker.done.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._on_thread_finished(thread))
        thread.start()
        return _json({"ok": True, "conversationId": conversation_id})

    @Slot(str, str)
    def _on_delta(self, conversation_id: str, delta: str) -> None:
        self.streamEvent.emit(_json({
            "type": "delta", "conversationId": conversation_id, "text": delta,
        }))

    @Slot(str, str, str, str)
    def _on_done(self, conversation_id: str, result: str, error_code: str,
                 memory_status: str) -> None:
        self.streamEvent.emit(_json({
            "type": "done", "conversationId": conversation_id,
            "status": result, "error": error_code,
            "memoryStatus": memory_status,
        }))

    def _on_thread_finished(self, thread: QThread) -> None:
        if self._thread is not thread:
            return
        self._thread = None
        self._worker = None
        thread.deleteLater()
        if self._closing and self._window is not None:
            QTimer.singleShot(0, self._window.close)

    def request_shutdown(self) -> None:
        self._closing = True
        if self._worker is not None:
            self._worker.cancelled.set()

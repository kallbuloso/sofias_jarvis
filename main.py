"""JARVIS development entrypoint."""

from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jarvis.config import database_path  # noqa: E402
from jarvis.conversation.store import SQLiteConversationStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS development bootstrap")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--diagnose", action="store_true", help="Inspect operational store")
    actions.add_argument("--create-conversation", metavar="TITLE", help="Create local conversation")
    actions.add_argument("--list-conversations", action="store_true", help="List local conversations")
    actions.add_argument("--configure-openai-key", action="store_true", help="Prompt for key without echo")
    actions.add_argument("--configure-memory-url", metavar="HTTPS_URL", help="Persist Sofias Memory HTTPS origin (not a secret)")
    actions.add_argument("--configure-memory-key", action="store_true", help="Prompt for Sofias Memory key without echo")
    actions.add_argument("--memory-check", action="store_true", help="Verify Sofias Memory connectivity and capabilities")
    actions.add_argument("--memory-get", metavar="UUID", help="Read an existing Cognitive Memory by ID")
    actions.add_argument("--memory-recall", action="store_true", help="Prompt for read-only cognitive recall query")
    parser.add_argument("--memory-scope", action="append", default=None, help="Explicit Cognitive Memory scope for --memory-recall; repeatable")
    actions.add_argument("--chat", action="store_true", help="One conversational turn in console")
    actions.add_argument("--desktop", action="store_true", help="Launch local desktop UI")
    parser.add_argument("--conversation-id", help="Existing conversation ID for --chat")
    parser.add_argument("--model", help="OpenAI model; or configure JARVIS_MODEL")
    args = parser.parse_args()

    try:
        if args.configure_openai_key:
            from jarvis.secrets.windows import WindowsCredentialStore

            secret = getpass("OpenAI API key (not echoed): ")
            WindowsCredentialStore().set_openai_key(secret)
            print("Key securely stored in Windows Credential Manager")
            return 0

        if args.configure_memory_url is not None:
            from jarvis.memory.connection import save_memory_url

            url = save_memory_url(args.configure_memory_url)
            print(json.dumps({"status": "CONFIGURED", "url": url}))
            return 0

        if args.configure_memory_key:
            from jarvis.secrets.windows import WindowsCredentialStore

            secret = getpass("Sofias Memory API key (not echoed): ")
            WindowsCredentialStore().set_memory_key(secret)
            print("Sofias Memory key securely stored in Windows Credential Manager")
            return 0

        if args.memory_check:
            from jarvis.memory.connection import SofiasMemoryConnection, configured_memory_url
            from jarvis.secrets.windows import WindowsCredentialStore

            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING", "url": url}))
                return 2
            result = SofiasMemoryConnection(url, key).diagnose()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "COMPATIBLE" else 2

        if args.memory_get or args.memory_recall:
            from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError
            from jarvis.memory.connection import configured_memory_url
            from jarvis.secrets.windows import WindowsCredentialStore

            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING"}))
                return 2
            if args.memory_recall and not args.memory_scope:
                print(json.dumps({"status": "SCOPE_REQUIRED"}))
                return 2
            client = CognitiveMemoryClient(url, key)
            compatibility = client.diagnose()
            if compatibility["status"] != "COMPATIBLE":
                print(json.dumps({"status": compatibility["status"]}))
                return 2
            try:
                if args.memory_get:
                    result = {"status": "FOUND", "memory": client.get(args.memory_get)}
                else:
                    query = input("Consulta: ").strip()
                    hits = client.recall(query=query, scopes=args.memory_scope)
                    result = {"status": "RESULTS_FOUND" if hits else "NO_RESULTS", "items": hits}
            except CognitiveMemoryError as exc:
                print(json.dumps({"status": exc.code}))
                return 2
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.desktop:
            from jarvis.desktop.app import launch_desktop

            return launch_desktop()

        store = SQLiteConversationStore(database_path())
        recovered = store.interrupt_inflight_messages()
        if args.create_conversation is not None:
            print(json.dumps({"conversation_id": store.create_conversation(args.create_conversation)}))
        elif args.list_conversations:
            print(json.dumps(store.list_conversations(), ensure_ascii=False, indent=2))
        elif args.chat:
            from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
            from jarvis.conversation.runtime import ConversationRuntime
            from jarvis.secrets.windows import WindowsCredentialStore

            model = args.model or os.getenv("JARVIS_MODEL", "")
            if not model.strip():
                raise ValueError("Choose --model or configure JARVIS_MODEL")
            key = WindowsCredentialStore().get_openai_key()
            if not key:
                raise ValueError("No API key configured; use --configure-openai-key")
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Install the project runtime dependencies") from exc
            conversation_id = args.conversation_id or store.create_conversation()
            if store.get_conversation(conversation_id) is None:
                raise ValueError("Unknown conversation ID")
            prompt = input("Você: ").strip()
            if not prompt:
                raise ValueError("Message cannot be empty")
            runtime = ConversationRuntime(store, OpenAIResponsesAdapter(OpenAI(api_key=key)))
            print(f"Conversation: {conversation_id}")
            print("JARVIS: ", end="", flush=True)
            for delta in runtime.reply(conversation_id=conversation_id, text=prompt, model=model):
                print(delta, end="", flush=True)
            print()
        else:
            print(json.dumps({"phase": "TB-01 bootstrap", "store": str(store.path),
                              "conversations": len(store.list_conversations()),
                              "interrupted_recovered": recovered,
                              "desktop_ready": False}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # Do not print exception from external provider SDK here: it may include
        # request headers or private details. Known local errors are non-secret.
        print(f"JARVIS: operação não concluída ({type(exc).__name__}).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

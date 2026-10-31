"""JARVIS TB-01 development entrypoint (desktop UI still pending)."""

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
    parser = argparse.ArgumentParser(description="JARVIS TB-01 development bootstrap")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--diagnose", action="store_true", help="Inspect operational store")
    actions.add_argument("--create-conversation", metavar="TITLE", help="Create local conversation")
    actions.add_argument("--list-conversations", action="store_true", help="List local conversations")
    actions.add_argument("--configure-openai-key", action="store_true", help="Prompt for key without echo")
    actions.add_argument("--chat", action="store_true", help="One conversational turn in console")
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

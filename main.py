"""JARVIS TB-01 bootstrap: operational storage diagnostics (desktop pending)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from jarvis.config import database_path  # noqa: E402
from jarvis.conversation.store import SQLiteConversationStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS TB-01 development bootstrap")
    parser.add_argument("--diagnose", action="store_true", help="Inspect operational store")
    parser.add_argument("--create-conversation", metavar="TITLE", help="Create a local conversation")
    parser.add_argument("--list-conversations", action="store_true", help="List local conversations")
    args = parser.parse_args()

    store = SQLiteConversationStore(database_path())
    recovered = store.interrupt_inflight_messages()
    if args.create_conversation is not None:
        print(json.dumps({"conversation_id": store.create_conversation(args.create_conversation)}))
    elif args.list_conversations:
        print(json.dumps(store.list_conversations(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"phase": "TB-01 bootstrap", "store": str(store.path),
                          "conversations": len(store.list_conversations()),
                          "interrupted_recovered": recovered,
                          "desktop_ready": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

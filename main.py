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
    actions.add_argument("--knowledge-datasets", action="store_true", help="List Sofias Memory datasets (read only)")
    actions.add_argument("--knowledge-query", action="store_true", help="Prompt for a Knowledge query in chunks mode")
    actions.add_argument("--knowledge-create-dataset", action="store_true",
                         help="Confirm creation of the dedicated jarvis-knowledge dataset")
    actions.add_argument("--knowledge-ingest-adr", action="store_true",
                         help="Confirm ingestion of only approved ADR-0001 into jarvis-knowledge")
    actions.add_argument("--knowledge-run", metavar="UUID",
                         help="Inspect a knowledge ingestion PipelineRun (no retry)")
    actions.add_argument("--knowledge-stats", action="store_true",
                         help="Inspect jarvis-knowledge dataset counters")
    actions.add_argument("--memory-create", action="store_true", help="Create an explicitly confirmed cognitive memory")
    actions.add_argument("--memory-test-create", action="store_true", help="Create a fixed, isolated disposable TB-02 test memory")
    actions.add_argument("--memory-test-supersede", metavar="UUID", help="Supersede ONLY a locally registered TB-02 test memory")
    actions.add_argument("--memory-test-forget", metavar="UUID", help="Forget ONLY a locally registered TB-02 test memory")
    actions.add_argument("--memory-test-list", action="store_true", help="List only local TB-02 disposable memory IDs")
    actions.add_argument("--memory-operation", metavar="UUID", help="Inspect a local cognitive write intent")
    parser.add_argument("--memory-type", choices=["profile", "semantic"], default="profile", help="Explicit cognitive type for --memory-create")
    actions.add_argument("--memory-recall", action="store_true", help="Prompt for read-only cognitive recall query")
    parser.add_argument("--memory-scope", action="append", default=None, help="Explicit Cognitive Memory scope for --memory-recall; repeatable")
    parser.add_argument("--knowledge-dataset", action="append", default=None,
                        help="Explicit dataset slug for --knowledge-query; repeatable")
    actions.add_argument("--chat", action="store_true", help="One conversational turn in console")
    actions.add_argument("--desktop", action="store_true", help="Launch local desktop UI")
    parser.add_argument("--conversation-id", help="Existing conversation ID for --chat")
    parser.add_argument("--model", help="OpenAI model; or configure JARVIS_MODEL")
    parser.add_argument("--use-memory", action="store_true", help="Explicitly opt into read-only cognitive recall for --chat")
    parser.add_argument("--use-knowledge", action="store_true", help="Opt into documentary Knowledge Retrieval for --chat")
    args = parser.parse_args()

    try:
        if args.use_memory and not args.chat:
            raise ValueError("--use-memory requires --chat")
        if args.use_knowledge and not args.chat:
            raise ValueError("--use-knowledge requires --chat")
        if args.use_knowledge and args.knowledge_dataset != ["jarvis-knowledge"]:
            raise ValueError("--use-knowledge requires exactly --knowledge-dataset jarvis-knowledge")
        if args.chat and args.knowledge_dataset and not args.use_knowledge:
            raise ValueError("--knowledge-dataset for chat requires --use-knowledge")
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

        if args.knowledge_datasets or args.knowledge_query:
            from jarvis.memory.knowledge import KnowledgeClient, KnowledgeError
            from jarvis.memory.connection import configured_memory_url
            from jarvis.secrets.windows import WindowsCredentialStore

            if args.knowledge_query and not args.knowledge_dataset:
                print(json.dumps({"status": "DATASET_REQUIRED"}))
                return 2
            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING"}))
                return 2
            client = KnowledgeClient(url, key)
            compatibility = client.diagnose()
            if compatibility["status"] != "COMPATIBLE":
                print(json.dumps({"status": compatibility["status"]}))
                return 2
            try:
                if args.knowledge_datasets:
                    data = {"status": "OK", **client.list_datasets()}
                else:
                    query = input("Consulta documental: ").strip()
                    data = client.query_chunks(
                        query=query, datasets=args.knowledge_dataset,
                    )
            except KnowledgeError as exc:
                print(json.dumps({"status": str(exc)}))
                return 2
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0

        if (args.knowledge_create_dataset or args.knowledge_ingest_adr
                or args.knowledge_run or args.knowledge_stats):
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.knowledge import KnowledgeError
            from jarvis.memory.knowledge_ingestion import (
                ADRKnowledgeClient, DATASET_SLUG, DATASET_NAME,
                SOURCE_NAME, approved_adr,
            )
            from jarvis.secrets.windows import WindowsCredentialStore

            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING"}))
                return 2
            client = ADRKnowledgeClient(url, key)
            check = client.diagnose()
            if check["status"] != "COMPATIBLE":
                print(json.dumps({"status": check["status"]}))
                return 2
            try:
                if args.knowledge_create_dataset:
                    print(f"Dataset: {DATASET_SLUG} | Nome: {DATASET_NAME}")
                    print("Esta operação poderá criar um namespace persistente no Sofias Memory.")
                    if input(f"Digite CRIAR DATASET {DATASET_SLUG} para autorizar: ").strip() != f"CRIAR DATASET {DATASET_SLUG}":
                        print(json.dumps({"status": "CANCELLED"}))
                        return 0
                    result = client.create_adr_dataset()
                elif args.knowledge_ingest_adr:
                    adr = approved_adr()
                    print(f"Documento autorizado: {SOURCE_NAME}")
                    print(f"Origem: {adr['source_path']}")
                    print(f"SHA256: {adr['sha256']}")
                    print(f"Bytes: {len(adr['content'].encode('utf-8'))}")
                    print("Ingestão FULL pode consumir embeddings/LLM; não haverá retry automático.")
                    if input("Digite INGESTIR ADR-0001 para autorizar: ").strip() != "INGESTIR ADR-0001":
                        print(json.dumps({"status": "CANCELLED"}))
                        return 0
                    result = client.ingest_adr(adr)
                elif args.knowledge_run:
                    result = client.inspect_run(args.knowledge_run)
                else:
                    result = client.dataset_stats()
            except KnowledgeError as exc:
                print(json.dumps({"status": str(exc)}))
                return 2
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("status") in ("failed", "cancelled", "FAILED", "CANCELLED"):
                return 2
            return 0

        if args.memory_test_list:
            from jarvis.memory.journal import MemoryOperationJournal

            journal = MemoryOperationJournal(database_path())
            print(json.dumps({"status": "OK", "items": journal.list_test_items()},
                             ensure_ascii=False, indent=2))
            return 0

        if args.memory_test_create or args.memory_test_supersede or args.memory_test_forget:
            from jarvis.memory.cognitive import CognitiveMemoryClient
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.journal import MemoryOperationJournal
            from jarvis.memory.test_lifecycle import (
                TEST_A, TEST_B, TEST_SCOPE, TestMemoryLab,
            )
            from jarvis.secrets.windows import WindowsCredentialStore

            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING"}))
                return 2
            client = CognitiveMemoryClient(url, key)
            check = client.diagnose()
            if check["status"] != "COMPATIBLE":
                print(json.dumps({"status": check["status"]}))
                return 2
            lab = TestMemoryLab(client, MemoryOperationJournal(database_path()), url)

            if args.memory_test_create:
                print(f"Teste descartável | Sofias Memory | Escopo: {TEST_SCOPE}")
                print("Conteúdo:", TEST_A)
                print("Não é uma memória pessoal. Uma gravação será persistida no Sofias Memory.")
                if input("Digite CRIAR TESTE para autorizar: ").strip() != "CRIAR TESTE":
                    print(json.dumps({"status": "CANCELLED"}))
                    return 0
                result = lab.create()
            else:
                target_id = args.memory_test_supersede or args.memory_test_forget
                action = "supersede" if args.memory_test_supersede else "forget"
                preview = lab.preview(target_id, action=action)
                print(json.dumps({"target": preview["memory_id"],
                                  "scope": preview["scope"],
                                  "lifecycle": preview["lifecycle"],
                                  "content": preview["content"]},
                                 ensure_ascii=False, indent=2))
                if action == "supersede":
                    print("Substituição persistente:", TEST_B)
                    required = f"SUBSTITUIR {preview['memory_id']}"
                    label = "Para autorizar, digite exatamente SUBSTITUIR seguido do UUID: "
                else:
                    print("Esquecimento destrutivo e permanente, sem afetar outros IDs.")
                    required = f"ESQUECER {preview['memory_id']}"
                    label = "Para autorizar, digite exatamente ESQUECER seguido do UUID: "
                if input(label).strip() != required:
                    print(json.dumps({"status": "CANCELLED"}))
                    return 0
                # Verify the current remote item again after confirmation.
                result = (lab.supersede(preview["memory_id"]) if action == "supersede"
                          else lab.forget(preview["memory_id"]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "CONFIRMED" else 2

        if args.memory_operation:
            from jarvis.memory.journal import MemoryOperationJournal

            operation = MemoryOperationJournal(database_path()).get(args.memory_operation)
            print(json.dumps(operation or {"status": "NOT_FOUND"}, ensure_ascii=False, indent=2))
            return 0 if operation else 2

        if args.memory_create:
            from uuid import uuid4

            from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError
            from jarvis.memory.connection import configured_memory_url
            from jarvis.memory.journal import MemoryOperationJournal
            from jarvis.secrets.windows import WindowsCredentialStore

            if args.memory_scope is None or len(args.memory_scope) != 1:
                print(json.dumps({"status": "EXACTLY_ONE_SCOPE_REQUIRED"}))
                return 2
            scope = args.memory_scope[0]
            if scope != "global" and not (
                scope.startswith("project:")
                and 1 <= len(scope[8:]) <= 128
                and all(c in "abcdefghijklmnopqrstuvwxyz0123456789._-" for c in scope[8:])
            ):
                print(json.dumps({"status": "INVALID_SCOPE"}))
                return 2
            url = configured_memory_url()
            if not url:
                print(json.dumps({"status": "URL_MISSING"}))
                return 2
            key = WindowsCredentialStore().get_memory_key()
            if not key:
                print(json.dumps({"status": "CREDENTIAL_MISSING"}))
                return 2
            client = CognitiveMemoryClient(url, key)
            check = client.diagnose()
            if check["status"] != "COMPATIBLE":
                print(json.dumps({"status": check["status"]}))
                return 2
            content = input("Informação para lembrar: ").strip()
            if not 1 <= len(content) <= 16384:
                print(json.dumps({"status": "INVALID_CONTENT"}))
                return 2
            from jarvis.memory.sensitive import looks_like_credential

            if looks_like_credential(content):
                print(json.dumps({"status": "SENSITIVE_CONTENT_REJECTED"}))
                return 2
            print(f"Destino: Sofias Memory | Escopo: {scope} | Tipo: {args.memory_type}")
            print("Esta confirmação gravará uma memória cognitiva persistente.")
            if input("Digite GRAVAR para autorizar: ").strip() != "GRAVAR":
                print(json.dumps({"status": "CANCELLED"}))
                return 0

            operation_id = str(uuid4())
            provenance = {
                "origin_kind": "user_asserted",
                "source_system": "jarvis",
                "source_ref": f"memory-operation:{operation_id}",
            }
            payload = {
                "memory_type": args.memory_type,
                "scope": scope,
                "content": content,
                "provenance": provenance,
                "idempotency_key": operation_id,
            }
            journal = MemoryOperationJournal(database_path())
            journal.prepare(operation_id, url, payload)
            journal.claim(operation_id)
            try:
                saved = client.create(
                    memory_type=args.memory_type, scope=scope, content=content,
                    provenance=provenance, idempotency_key=operation_id,
                )
            except CognitiveMemoryError as exc:
                outcome = "unknown" if exc.code == "RESULT_UNKNOWN" else "rejected"
                journal.resolve(operation_id, status=outcome, error_code=exc.code)
                print(json.dumps({
                    "status": "RESULT_UNKNOWN" if outcome == "unknown" else exc.code,
                    "operation_id": operation_id,
                    "retry_automatically": False,
                }))
                return 2
            except Exception:
                journal.resolve(operation_id, status="unknown", error_code="LOCAL_ERROR")
                print(json.dumps({"status": "RESULT_UNKNOWN", "operation_id": operation_id,
                                  "retry_automatically": False}))
                return 2
            journal.resolve(operation_id, status="confirmed", memory_id=saved["memory_id"])
            print(json.dumps({"status": "CONFIRMED", "operation_id": operation_id,
                              "memory_id": saved["memory_id"], "scope": saved["scope"]},
                             ensure_ascii=False, indent=2))
            return 0

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
            provider = OpenAIResponsesAdapter(OpenAI(api_key=key))
            memory_provider = None
            knowledge_provider = None
            if args.use_memory:
                if not args.memory_scope:
                    raise ValueError("--use-memory requires --memory-scope")
                from jarvis.memory.cognitive import CognitiveMemoryClient, CognitiveMemoryError, _scope
                from jarvis.memory.connection import configured_memory_url
                from jarvis.memory.context import MemoryAwareTextProvider

                # Fail closed on malformed scope before the external request.
                scopes = list(dict.fromkeys(_scope(scope) for scope in args.memory_scope))
                memory_key = None
                try:
                    memory_url = configured_memory_url()
                    if memory_url:
                        memory_key = WindowsCredentialStore().get_memory_key()
                except Exception:
                    memory_url = None

                if memory_url and memory_key:
                    reader = CognitiveMemoryClient(memory_url, memory_key)
                else:
                    class UnavailableMemoryReader:
                        def recall(self, **kwargs):
                            raise CognitiveMemoryError("SERVICE_UNAVAILABLE")
                    reader = UnavailableMemoryReader()
                memory_provider = MemoryAwareTextProvider(provider, reader, scopes=scopes)
                provider = memory_provider
            if args.use_knowledge:
                from jarvis.memory.connection import configured_memory_url
                from jarvis.memory.knowledge import KnowledgeClient, KnowledgeError
                from jarvis.memory.knowledge_context import KnowledgeAwareTextProvider

                knowledge_key = None
                try:
                    knowledge_url = configured_memory_url()
                    if knowledge_url:
                        knowledge_key = WindowsCredentialStore().get_memory_key()
                except Exception:
                    knowledge_url = None

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
                    provider, knowledge_reader, datasets=args.knowledge_dataset,
                )
                provider = knowledge_provider
            runtime = ConversationRuntime(store, provider)
            print(f"Conversation: {conversation_id}")
            print("JARVIS: ", end="", flush=True)
            for delta in runtime.reply(conversation_id=conversation_id, text=prompt, model=model):
                print(delta, end="", flush=True)
            print()
            if memory_provider is not None:
                print(json.dumps({
                    "memory_retrieval": memory_provider.last_retrieval_status,
                    "memory_ids": memory_provider.last_memory_ids,
                    "scopes": memory_provider.scopes,
                }, ensure_ascii=False))
            if knowledge_provider is not None:
                print(json.dumps({
                    "knowledge_retrieval": knowledge_provider.last_retrieval_status,
                    "query_id": knowledge_provider.last_query_id,
                    "datasets": knowledge_provider.datasets,
                    "references": knowledge_provider.last_references,
                }, ensure_ascii=False))
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

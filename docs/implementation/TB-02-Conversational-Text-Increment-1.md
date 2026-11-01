# TB-02 — Text-First Conversational Entry / Increment 1

**Branch:** `feat/tb-02-memory-knowledge`
**Status:** IMPLEMENTED, **NOT TESTED on owner Windows**; no Product Done.
**Constraint:** Voice/microphone capture, TTS, scheduler/reminders and TB-03 are NOT part of this increment.

## Why the earlier desktop was wrong

The desktop inherited technical flags for `Consultar Sofias Memory`,
`Consultar Knowledge`, scoped dataset selection and slash commands that are
appropriate for the CLI but not for a natural-language personal assistant.
The owner explicitly rejected exposing UUID syntax to end users and approved
a text-first conversational interface, with voice deferred until text works.
The screenshot also showed many old, unlabelled `Nova conversa` records
without a deletion action.

## Implemented: deliberate first vertical checkpoint

1. `TextIntentRouter` makes a bounded OpenAI Responses **structured output**
   classification from **only the current user's text**. Closed actions:
   `chat`, `memory_recall`, `knowledge_query`, `memory_create`,
   `memory_update`, `memory_forget`, `reminder_request`. Closed scopes:
   `global`, `project:jarvis` or missing. It has no Memory API client or
   permission to execute an operation; unsupported/invalid results fail closed.
2. The desktop uses one Qt bridge entry `sendConversationalMessage`.
   Read-only Memory Recall and Knowledge are selected by the router and
   re-use the **existing** bounded retrieval/context providers. The
   `jarvis-knowledge` allowlist remains unchanged. The source metadata
   continues to persist with the exact assistant message under SQLite v5.
3. The **two manual switches, dataset/scope selectors and technical slash
   instruction banner were removed** from desktop. The original explicit
   CLI/bridge methods remain available as non-default engineering paths,
   to avoid prematurely deleting valuable tested implementations.
4. For `memory_create`, `memory_update` or `memory_forget`, this
   first increment intentionally shows a truthful **NOT EXECUTED** response.
   No LLM output alone can write to Cognitive Memory. For
   `reminder_request`, it explicitly states that no task was scheduled.
   If intent routing fails, no write/read is attempted and an explicit
   controlled failure is reported; there is no fake success.
5. Each conversation in the sidebar has an **Excluir** action with
   an explicit confirmation dialog. The Core removes only that local
   conversation's transcript and per-message Knowledge metadata via FK
   cascade. It does **not** delete cognitive memories, preserved operational
   journals or any other conversation. Deleting the final conversation
   keeps the list empty; a new one is created only when explicitly requested.
   Deletion is rejected while the application has active reply/preview/
   mutation workers.

## Explicitly NOT implemented yet

This is **not** completion of conversational memory actions.

- Natural-language `memory_create` should produce a contextual preview and
  simple conversational confirmation, then call a journalled/authorized
  create service with exact scope, idempotency and real service ACK.
- Natural `memory_update` / `memory_forget` must resolve targets only
  from owner-eligible records, disambiguate when needed, preview impact,
  and collect a fresh **one-use** confirmation bound to conversation,
  specific operation and target. Existing UUID-typed CLI gate remains
  an engineering fallback; it is **not** the desired desktop UX.
- A request such as "amanhã me lembre de ligar" is a **task/scheduler
  intention**, not a persistent preference. It must not be silently
  stored as cognitive memory or presented as scheduled. Scheduler remains
  a later authorized Slice.
- This first classifier adds one OpenAI request per conversational text
  turn; latency, model support for structured outputs and classification
  accuracy need a real smoke before extension.
- Degraded Memory/Knowledge, scope ambiguity, provider failures and source
  attribution still require human checks. Proactive behavior and voice are
  not authorized by this checkpoint.

## Local Windows tests (no Cognitive Memory mutations)

With the JARVIS desktop closed:

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

Previous validated baseline: **214 passed**. New test cases:
1 store deletion, 1 Qt bridge deletion, 11 classifier cases, 8 Qt routing
cases = **235 expected**, pending actual collection/execution.

Human smoke (after automated tests):
1. Text "Qual arquitetura foi definida no ADR-0001?" should automatically
   retrieve Knowledge and attach verifiable sources inside its message.
2. "Qual é minha preferência de cor?" should route to Cognitive Recall.
3. "JARVIS, amanhã às nove me lembre de ligar para o fornecedor"
   must **not** claim a scheduled reminder.
4. "JARVIS, lembre que neste projeto prefiro Vuetify 3" must be
   recognized but **not yet saved**; no confirmation UI exists yet.
5. Create a few empty local conversations, delete one (confirm),
   verify another remains, restart; delete the last one if desired,
   verify none is silently re-created. Ensure shutdown normal.

No migration beyond previously accepted SQLite v5 and no automatic
external mutating call. **Not Product Done**. Never merge to main
without a separate owner decision.

## Windows regression run — dataset fixture alignment (2026-11-01)

Owner ran the full offline test suite on Windows. Observed:
**234 passed, 1 failed in 9.78 s**. Only
`test_natural_text_knowledge_query_retrieves_sources_without_switch`
failed: assistant message status `failed` instead of `completed`.

Audit of test and production Knowledge provider found a precise
test-double mismatch: `KnowledgeAwareTextProvider._dataset_id()`
correctly enforces fixed approved dataset
`slug=jarvis-knowledge`, `name=JARVIS Knowledge`, `status=active`;
the newly authored conversational mock returned
`name=JARVIS`. That correctly triggered
`knowledge_dataset_not_active` and prevented retrieval.
**Production dataset guard remains unchanged.**

Repair updated only `tests/test_text_conversational_desktop.py`:
the fixture now returns `JARVIS Knowledge` and the test additionally
asserts worker `done` status and `evidencePersistence=SAVED` when
the mocked retrieval succeeds. Await fresh Windows pytest and
frontend build; **do not claim 235 passed or desktop smoke completed**.

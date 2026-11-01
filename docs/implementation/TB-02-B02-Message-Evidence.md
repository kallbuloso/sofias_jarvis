# JARVIS — TB-02 B-01 Acceptance / B-02a Message Evidence

**Branch:** `feat/tb-02-memory-knowledge`
**Status B-01:** functional and offline acceptance PASS; no TB-02 Product Done yet.
**Status B-02a:** implementation committed, Windows and desktop validation pending.

## B-01 — Final human evidence (2026-11-01)

Owner ran 202 tests successfully (7.54s) after the v4 migration test-fixture fix.
Vite v7.3.7 compiled 559 modules in 5.55s, with only the non-blocking
>500 kB chunk warning.

Owner ran `main.py --memory-operation 6e925d24-1205-4864-9a69-79fc6616d154`
against the operational SQLite database; it returned the previously confirmed
Forget operation linked to memory
`53fd477d-2061-46c3-89b7-d265cd48a2a1`, `error_code=null`, and
`confirmation_ref=null`, `confirmation_method=null`,
`confirmation_conversation_id=null`, `confirmed_by_user_at=null`.
This is correct **non-retroactive** treatment of a historical journal entry.
The same disposable memory previously returned `lifecycle=forgotten`,
`content=null`, `scope=null` on real Sofias Memory.

Prior owner evidence covers Create, Get, Supersede, Forget, read-only preview,
cancelled previews, single-use authorization, and separate journal confirmation.
Newly introduced durable typed-consent fields were verified in automated
tests using offline fake services. No additional live mutation was needed.

**B-01 functional and audit-contract checkpoint: PASS.** The existing real
historic operations are not falsely claimed as bearing v4 consent receipts.
This is not authorization to merge, broaden scope or start TB-03.

## B-02a — Persistence design and behavior

The original TB-02 Final Acceptance Review finding B-02 requires durable,
message-specific retrieval metadata that survives desktop restart and
conversation changes, without storing complete chunks/documents.

- SQLite **schema v5** adds `message_knowledge_evidence`, a 1:1 table keyed
  by `assistant_message_id` with FK to `messages.id` and cascade delete.
- The row stores `query_id`, fixed pilot dataset `jarvis-knowledge`,
  retrieval status, retrieval time and a bounded list of validated
  `source_id/document_id/chunk_id/source_name` tuples.
- No user prompt, chunk text, quote, provider token or URL is stored in the
  metadata. No URL is fabricated, and generated LLM citations are never
  treated as verified retrieval evidence.
- `ConversationRuntime` exposes the assistant message ID created during
  streaming; `ReplyWorker` writes Knowledge metadata to that exact message
  **before** its final desktop event. A write error is surfaced as
  `evidencePersistence=FAILED` and never claims successful durable sources.
- `listMessages` loads evidence from SQLite for each assistant message.
  Vue renders the historical references inside the response bubble,
  independent of the current Knowledge switch setting.
- Incomplete streaming is marked `interrupted` or `failed` and still
  explicitly labeled incomplete when Knowledge retrieval metadata exists.
  An interrupted response is not silently upgraded to `completed`.
- Existing conversation messages are untouched and gain **no fabricated**
  historical references. Other datasets, general plugin discovery and
  additional autonomous capabilities are out of scope.

### Next Windows gate (no remote mutations)

Close the desktop, make a fresh SQLite backup **before** v4→v5 migration,
then run:

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

Baseline is **202 tests**, with **12** additional parametrized SQLite
provenance cases, for **214 expected tests**. The expected number is not
an execution claim. Review local pytest/build results first; after that,
an explicit human smoke should open the desktop, send a Knowledge-enabled
question about ADR-0001, inspect sources attached to that assistant message,
switch conversations, restart the desktop, and verify that its exact
source/document/chunk IDs still appear with the same message. Observe
desktop exit status and shutdown logs; do not write/delete Sofias Memory
records during the smoke.

**B-02a NOT accepted** until automated and human visual evidence.
Do not declare TB-02 Product Done or merge into main.

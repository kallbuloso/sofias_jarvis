# JARVIS

Local-first independent AI assistant. TB-01 is Product Done, merged to main
after 16 passing tests and owner validation. TB-02 is in progress on its
own feature branch.

## TB-01 implemented so far

- Python Core and independent application bootstrap;
- SQLite conversation history and conservative incomplete-message handling;
- OpenAI Responses API streaming adapter, with a real console smoke confirmed;
- native Windows Credential Manager via verified `keyring` backend;
- candidate desktop: PySide6 WebEngine + Vue 3 + Vuetify 3 with a restricted Qt WebChannel bridge.

The desktop was validated by the owner on Windows 11. The Core is independent of Qt.

## Development on Windows 11

Requires Python 3.13 and recent Node.js/npm (Node.js is only a frontend build
tool, **not** the Core runtime).

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ui]"
.\.venv\Scripts\python.exe -m pytest -q

cd frontend
npm install
npm run build
cd ..

$env:JARVIS_MODEL = "gpt-6-luna"
.\.venv\Scripts\python.exe main.py --desktop
```

The default model is intentionally **not** hard-coded. Use any supported
model enabled for your own API account. You can change the model in the desktop.

If you have not configured an OpenAI key on this Windows account:

```powershell
.\.venv\Scripts\python.exe main.py --configure-openai-key
```

This prompts for the API key without echoing it and stores it through Windows
Credential Manager. Never commit secrets or send them through chat.

## Console commands

```powershell
.\.venv\Scripts\python.exe main.py --diagnose
.\.venv\Scripts\python.exe main.py --list-conversations
.\.venv\Scripts\python.exe main.py --chat --model gpt-6-luna
```

Use `--conversation-id UUID` to continue a console conversation. All modes
use the same local operational store under
`%LOCALAPPDATA%\JARVIS\jarvis.sqlite3`. For isolated development, set
`JARVIS_DATA_DIR` before startup.

## Current constraints and next checks

- TB-01 requires Windows UI tests for Qt WebChannel, incremental rendering,
  conversation switching, restart, shutdown, and loss of API connectivity.
- The first user confirmation of a live OpenAI response does not demonstrate
  the UI stream or the full TB-01 acceptance criteria.
- The Vue desktop intentionally cannot open arbitrary internet pages or call
  provider APIs; all access runs through the Python Core.
- Voice, Sofias Memory, tools, fallback, background execution, and final
  installer are outside TB-01 scope.
- Frontend dependency lock and Python dependency pinning will be finalized
  after compatibility validation, not silently assumed complete.

See `docs/product-manager/08-JARVIS-Technical-Backlog.md` for acceptance tests.

## TB-02 step 01 — connection (under validation)

Configure a non-secret Sofias Memory URL in the local data directory and
a separate API key in Windows Credential Manager. The diagnostic checks
health and authenticated capability negotiation only, without memory writes.

    .\.venv\Scripts\python.exe main.py --configure-memory-url "https://pefil-sofias-memory.q8cqqr.easypanel.host"
    .\.venv\Scripts\python.exe main.py --configure-memory-key
    .\.venv\Scripts\python.exe main.py --memory-check

Expected status: COMPATIBLE. Never provide the API key in chat or command arguments.

## TB-02 step 02 — Cognitive Memory adapter (under validation)

The Core now has a separate API client for **Create / Get / typed Recall /
Supersede / Forget**. It uses explicit scopes and provenance, checks the
returned lifecycle, and requires a caller-owned UUID idempotency key on every
mutation. It does not perform blind retries after uncertain writes.

The first live smoke is intentionally **read-only**, without storing or
deleting data in your Sofias Memory instance:

    .\.venv\Scripts\python.exe main.py --memory-recall --memory-scope global
    .\.venv\Scripts\python.exe main.py --memory-recall --memory-scope project:jarvis
    .\.venv\Scripts\python.exe main.py --memory-get EXISTING_MEMORY_UUID

The recall command prompts for the query locally, avoiding shell-history
storage. Scope is mandatory and exact; global is never silently added to
project-specific queries. Expect \`NO_RESULTS\` when there are no relevant
memories; network failures and incompatible responses are *not* empty results.

Mutating methods are **not yet wired to the chat UI/CLI**. Before using those
against a live service, the JARVIS Core must persist authorization, operation
identity and outcome evidence to reconcile uncertain results correctly.
No conversational automatic cognitive writes are enabled.


### Explicit memory write smoke (requires your local confirmation)

Once the automated tests pass, you can deliberately save **one
non-sensitive test preference** to the live service. This is an intentional
persistent write, not just a diagnostic read:

    .\.venv\Scripts\python.exe main.py --memory-create --memory-scope global --memory-type profile

At \`Informação para lembrar:\`, enter a harmless preference, e.g.
\`Para interfaces gráficas, prefiro a cor teal.\`. Check scope and type, then
type **GRAVAR** to consent. Any other response cancels. Success returns
\`CONFIRMED\` and a \`memory_id\`. This write is durable in Sofias Memory.

Then verify:

    .\.venv\Scripts\python.exe main.py --memory-recall --memory-scope global
    .\.venv\Scripts\python.exe main.py --memory-get UUID_FROM_CONFIRMED_RESULT

An operation can be inspected locally without sending it again:

    .\.venv\Scripts\python.exe main.py --memory-operation OPERATION_UUID

If a write yields \`RESULT_UNKNOWN\`, do **not** repeat it with a fresh key.
The original attempt is journaled locally for deliberate reconciliation.
Confirmed and rejected operations have their original content removed from
the local journal. This version has no automatic retry/reconciliation.
A conservative credential-content filter blocks common secret markers.


## TB-02 step 03 — memory-assisted console chat (opt-in)

A live Cognitive Memory Create and Recall have been verified by the owner.
**A memory-assisted OpenAI answer is not yet validated**; the next smoke
uses the explicit \`--use-memory\` switch:

    .\.venv\Scripts\python.exe main.py --chat --model gpt-6-luna --use-memory --memory-scope global

When prompted, ask: \`Qual minha cor preferida para interfaces gráficas?\`.
A successful response should use the retrieved teal preference and report
\`"memory_retrieval": "RESULTS_FOUND"\` with the memory ID. This runs one
read-only cognitive recall before normal inference and transmits the prompt
to the configured Sofias Memory instance. The prompt is sent there only
because \`--use-memory\` was explicitly selected.

Without the opt-in flag, \`--chat\` remains unchanged. With missing or
unavailable Memory, the OpenAI text turn can still proceed, while the model
receives an explicit \`UNAVAILABLE\` retrieval status and must not claim
to have recovered a memory. If Memory returns no matches, status is
\`NO_RESULTS\` (not an outage). Memory data and references are ephemeral
context, not persistent SQLite conversation messages or privileged
instructions. The JARVIS UI is **not yet** memory-aware; this smoke is
console-only.

Scope is mandatory and exact; use multiple \`--memory-scope\` options
only when intentionally querying more than one scope. Writes remain
disabled by default during conversation.


## TB-02 step 05 — Knowledge Retrieval (first read-only adapter)

Knowledge Memory is **not** the same API as Cognitive Memory. The
new CLI lists existing dataset slugs, then queries a **selected dataset**
using \`POST /api/v1/recall\` with \`mode=chunks\`, \`only_context=true\`
and \`include_references=true\`. This avoids a second generated answer
from Sofias Memory. The service **does record a Query audit ID** for
each recall; the command does not ingest, edit, forget or delete knowledge.

    .\.venv\Scripts\python.exe main.py --knowledge-datasets
    .\.venv\Scripts\python.exe main.py --knowledge-query --knowledge-dataset YOUR_DATASET_SLUG

At \`Consulta documental:\`, enter your question. The output preserves
\`query_id\`, \`source_id\`, \`document_id\`, \`chunk_id\` and any returned
reference/quote. If the dataset is not already populated, discovery can
work yet retrieval may return \`NO_RESULTS\`. Choose an existing dataset
from the first command; do not assume \`main\` is populated.

The Python adapter and its CLI are an **intermediate TB-02 increment**.
Knowledge integration into desktop response/context and full provenance
display have **not** been accepted yet.

## Desktop presentation mini-fix

After the owner reported 88 PASS and a successful Vite build, screenshot
inspection found an oversized generic warning panel (missing scope) and
raw Markdown \`**teal**\` text. The feature branch now uses bounded,
non-expanding warning elements and escaped Vue-text rendering of basic
inline **bold** only. Full CommonMark, rich HTML and arbitrary clickable
links are intentionally not supported; do not add \`v-html\` for
untrusted model content. Rebuild the frontend after updating.

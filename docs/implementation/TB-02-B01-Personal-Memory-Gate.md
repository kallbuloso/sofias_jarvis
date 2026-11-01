# TB-02 / B-01 — Personal Memory Mutations, Core/CLI Gate

**State:** code committed in `feat/tb-02-memory-knowledge`; **Windows pytest
and real smoke pending**. This is B-01a (safe Core/CLI boundary), not
the completed conversational/Desktop flow. B-02 provenance persistence
has not been implemented. No merge to `main`.

## Contract

- Cognitive `Create` remains opt-in and unchanged.
- New CLI commands: `--memory-supersede UUID` and `--memory-forget UUID`.
- The target must be recorded as a **confirmed personal Create or confirmed
  personal Supersede by THIS JARVIS installation and SAME HTTPS service**.
  A remote UUID alone is never enough. TB-02 disposable test memories and
  other users'/installations' memories are not eligible.
- The exact remote UUID, `user_asserted` provenance, JARVIS source reference,
  lifecycle, scope and type are checked before confirmation AND immediately
  before dispatch. Remote state changes invalidate the prior confirmation.
- The person must type `SUBSTITUIR <target UUID>` or `ESQUECER <target UUID>`
  exactly. Not even reading an explicit instruction in the chat causes a
  mutation in this increment.
- Supersede preserves scope and type, creates a distinct active memory with
  new `memory-operation:<operation_id>` provenance.
- Forget affects **only** the confirmed target UUID, not its lineage or
  related documents. The service returns a redacted `forgotten` tombstone.
- The journal commits the intent and idempotency key before network effects.
  No automatic retries. `RESULT_UNKNOWN` or local post-dispatch ambiguity
  remains unresolved; further mutations on that UUID are blocked.
- The CLI does not run mutations automatically on startup, inference,
  retrieval, provider fallback or any Knowledge operation.

## Next validation — local tests only

```powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

**Do not** run `--memory-forget` or `--memory-supersede` against any
existing personal UUID during this first check. New unit tests use fake
services and SQLite in temporary folders. Expected increase over the
previous 172-pass baseline: 14 collected cases (subject to pytest collection).

## Pending acceptance within B-01

1. Verify all unit tests in the user's Windows/PySide6 environment.
2. Add a conversational intent-to-preview boundary and desktop confirmation
   path. The model may propose a candidate, but **cannot authorize effects**;
   no implicit operations for free-form text without UI confirmation.
3. Smoke with a NEW, explicitly authorized disposable personal memory; never
   reuse the existing `global/profile` teal preference or TB-02 test allowlist.
4. Confirm failed/unknown outcomes, shutdown and operational audit again.
5. Proceed to B-02 only after B-01 end-to-end user interaction is accepted.

## B-01b / Preview-only desktop checkpoint — implementation pending human smoke

A conservative integration was added without enabling mutating desktop slots:

- In chat, typing `/esquecer UUID` or
  `/atualizar UUID | nova informação` is intercepted **before**
  sending a user turn to the LLM.
- `JarvisBridge.previewPersonalMemory(action, uuid)` accepts only
  `forget` or `supersede` and a canonical UUID. It queues a
  `MemoryPreviewWorker` on its own `QThread`.
- The worker reads the configured Memory credential only in Python,
  checks the negotiated contract, and calls `PersonalMemoryLifecycle.preview`
  (ownership, state and provenance validation). It **does not expose** any
  create/supersede/forget RPC to the frontend.
- The web UI shows the existing record and proposed replacement as
  escaped Vue text, with a single button **Fechar sem alterar**.
  The preview does not appear as a persisted chat turn.
- The bridge reuses the Qt GUI-thread finished-slot convention; the
  window will not shut down until any preview worker finishes.
- Four isolated regression tests cover bad IDs, read-only behavior,
  sanitized errors and QThread cleanup.

**Not yet authorized/implemented:** confirm-and-execute from the desktop,
memory Create by conversational command, persistence of Knowledge provenance
(B-02). No live memories have been mutated during this increment.

### Required validation

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

Baseline 185 + four new Qt preview tests = **189 expected**, provided
all optional dependencies are installed and tests pass. The automated
suite and Vite build were not executed by the authoring environment;
the local Windows output is authoritative.

For optional **read-only** human smoke, run `main.py --desktop`,
type `/esquecer <UUID of a personally created, confirmed local memory>`
or `/atualizar <UUID> | texto novo`, and inspect the preview.
**Close without altering**; no persistent operation should occur.
A foreign UUID, an unowned Memory record, or a test-lab record
must be denied before presenting its content. Check process exit code
and `desktop-lifecycle.jsonl` if diagnostics are enabled.

The exact UUID displayed in the preview is the remote target, not a
permission token. Later implementation must still bind a one-use
pending intent to the confirmed preview and **revalidate** before
dispatching a mutation. The LLM must never authorize changes.

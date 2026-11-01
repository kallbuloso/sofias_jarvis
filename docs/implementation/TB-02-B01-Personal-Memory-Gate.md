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

## B-01b — Validação automatizada Windows (relato do proprietário)

Após atualização `8965304..fe35025` pelo comando
`git pull --ff-only origin feat/tb-02-memory-knowledge`:

- `python -m pytest -q`: **189 passed in 6.01s**
- `npm run build`: **PASS** — Vite 7.3.7, 559 módulos,
  `built in 5.54s`
- Alerta de chunk acima de 500 kB: aviso de otimização,
  **não falha de build**

**Estado:** validação de código/compilação B-01b = PASS.
**Ainda pendente:** smoke humano de prévia de memória no desktop
usando `/atualizar UUID | texto` e `/esquecer UUID` com a única
ação `Fechar sem alterar`, sem mutação real; observar saída Qt
e logs opcionais. Não considerar B-01b Product Done antes desse teste.
Nenhuma alteração de memória real foi relatada nesta validação.

## Human verification of B-01b and B-01c implementation (2026-11-01)

The owner confirmed both read-only desktop previews worked without errors,
and `--memory-get ab89ac04-7134-49c6-9fa2-2880a296d50a`
returned identical before/after values: `global`, `profile`,
`content="Para interfaces gráficas, prefiro a cor teal."`,
`lifecycle=active`. This completes the B-01b visual preview checkpoint.

B-01c (implementation awaiting Windows test) introduces:
- `PersonalMutationGate` with random one-use token, 180-second TTL,
  exact `SUBSTITUIR UUID` or `ESQUECER UUID`, single-use consumption
  and conversation-bound confirmation.
- The new `previewPersonalMutation` bridge method: validates canonical
  UUID, selected conversation, replacement length and credential-like
  content, and fetches an owner-verified remote preview.
- The existing read-only `previewPersonalMemory` bridge path remains
  for backwards compatibility and cannot authorize a mutation.
- A second, explicit confirmation text field in the desktop and a
  distinct `Confirmar substituição` or `Confirmar esquecimento` button.
  Closing cancels the pending token and preserves the original memory.
- The one-use intent is consumed **before** starting the mutation
  worker. A remote state/provenance recheck and journal/idempotency
  still occur before the external request. Results cannot be retried
  automatically after ambiguity.
- The mutation runs on a separate Qt thread; its final status is
  delivered on the GUI thread. Application shutdown waits for active
  workers. Active mutation cannot be cancelled by closing the preview.
- No model-generated text or Knowledge Retrieval result has an execution
  tool for personal memory operations.

### Mandatory first validation (no real writes)

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

The last validated suite was **189 passed in 6.01s**. Five new test
functions (three token gate tests and two desktop confirmation tests)
were added, so the expected collection is **194 passed**, subject to
actual Windows testing. No rebuild-free runtime guarantee is asserted.

**Do not confirm an operation on the existing teal memory**, even if
the new button is available. Do not run destructive tests against the
already ingested ADR or the earlier discarded lab memories.

The next safe smoke is a **cancellation-only** check: use a personal
memory preview, leave the confirmation text empty, click
`Fechar sem alterar`, verify the remote record remains active.
After that, any real mutation smoke must use a NEW explicitly
authorized, disposable personal test memory; use the same owner
checks, real operation IDs and independent remote verification.

**TB-02/B-01c is NOT accepted yet. B-02 remains pending.**

## B-01c — Windows automated validation (2026-11-01)

The owner executed the post-confirmation suite:
- `python -m pytest -q`: **194 passed in 7.86s**.
- `npm run build`: **PASS**, Vite 7.3.7, 559 transformed modules,
  completed in 5.53s. The >500 kB bundle warning was non-fatal.

**Result:** offline automated checks and production frontend compilation PASS.
**Not yet accepted:** Qt desktop cancel-only smoke and later authorized
mutation using a *new disposable personal record*. Avoid destructive use
of the preserved global teal preference UUID.

The next human test opens the existing teal record using the explicit
`/atualizar UUID | Prefiro a cor azul.` and `/esquecer UUID` commands
but clicks only `Fechar sem alterar` each time. A subsequent
`--memory-get` must still report `lifecycle=active` and unchanged teal
content. **Do not type the confirmation phrase or click the confirm button.**

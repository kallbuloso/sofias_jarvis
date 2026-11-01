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

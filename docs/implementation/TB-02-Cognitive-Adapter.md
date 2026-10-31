# TB-02 Step 02 — Cognitive Memory API adapter

**Status:** Implementation committed in feature branch; real Windows tests pending.
**Contract:** Sofias Memory v0.7.0 Cognitive Memory API version 1.

## Implemented

- Get by memory UUID, typed Recall with required exact scopes; no automatic global scope.
- Create with explicit provenance, scope, content and caller-controlled idempotency UUID.
- Supersede with inherited scope/type, lineage verification and idempotency UUID.
- Forget by exact memory UUID, requiring tombstone without cognitive content.
- Network/5xx/invalid-acknowledgment after mutation => RESULT_UNKNOWN, no blind retry.
- Rejected HTTP codes mapped to stable error codes; never expose raw errors or API key.
- No actual mutations requested from the deployed service.

## Security and behavioral boundaries

Cognitive memory items are **data**, not instructions or grants. The adapter
does not authorize writes; a future Core policy / operation journal will
provide the necessary authority and durable idempotency tracking. This is
why create/supersede/forget exist as Python methods but are **not** exposed
as direct chat/CLI mutations yet.

The initial real integration test uses only read-only endpoints:

\`\`\`powershell
git fetch origin
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --memory-recall --memory-scope global
.\.venv\Scripts\python.exe main.py --memory-recall --memory-scope project:jarvis
\`\`\`

You are prompted for the query. Empty scope-specific results are legitimate.
A service error or incompatible response must not be shown as NO_RESULTS.

Next: Core authorization/journal for mutating operations; context injection,
knowledge dataset retrieval with references, minimal UI and live validation.

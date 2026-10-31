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


## Explicit Create CLI (new controlled validation)

The user may call \`--memory-create --memory-scope global --memory-type profile\`.
The local terminal prompts for content and explicit \`GRAVAR\` confirmation.
Only then does the Core record the Create intent in the existing SQLite
operational database, assign a stable UUID idempotency key, and dispatch.

The journal records \`prepared\` → \`in_flight\` → one of
\`confirmed\`, \`rejected\` or \`unknown\`. A restart never blindly retries
\`in_flight\` or \`unknown\`. On a terminal confirmed/rejected outcome the
journal removes the request payload; on unknown it retains the original for
future explicit reconciliation. The public status command never displays
the payload. Sensitive-looking credential text is blocked by a conservative
preliminary filter; this is not a replacement for privacy policy.

\`--memory-operation OPERATION_UUID\` is a local read-only status check.

**Real Create/Recall/Get against the VPS remain unvalidated until the owner
explicitly types GRAVAR and reports the result.** Do not send credentials.


## Real integration evidence (reported by owner, 2026-10-31)

- Windows test suite passed **55 tests** before the later journal/context changes.
- Explicit \`--memory-create --memory-scope global --memory-type profile\`
  returned \`CONFIRMED\`, with a durable memory ID and operation ID.
- A subsequent \`--memory-recall --memory-scope global\` returned
  \`RESULTS_FOUND\`: the same ID, \`lifecycle=active\`,
  \`origin_kind=user_asserted\`, \`source_system=jarvis\`,
  \`is_current_truth=true\`, and cosine relevance around 0.774.
- This establishes real Create→Recall and provenance, but **does not
  establish Get, Supersede, Forget or conversation context**.
- The more recent automated tests have not yet been reported by the owner.

## Step 03 in progress — opt-in context

\`MemoryAwareTextProvider\` wraps the text provider without changing
the conversation store or the normal provider adapter. The explicit
\`--chat --use-memory --memory-scope global\` path makes exactly one
Cognitive Memory read-only recall and introduces bounded, low-trust
JSON evidence into the current provider request, without persisting that
evidence as a chat message. The static developer instruction establishes
a boundary; content from Memory always has lower authority.

No memory content is used for authorization; no automatic Cognitive
Memory writes. A Memory outage remains distinct from an empty result,
and independent text chat is allowed to continue with an explicit
unavailable signal. GUI integration and live context validation remain
pending.

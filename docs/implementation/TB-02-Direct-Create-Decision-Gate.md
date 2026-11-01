# TB-02 — Direct natural-language Cognitive Create, no redundant click

**Policy:** Owner APPROVED 2026-11-01. Formal amendment:
`docs/product-manager/09-JARVIS-Direct-Memory-Authorization-Amendment.md`.
**Branch:** `feat/tb-02-memory-knowledge`.
**Implementation status:** DONE in branch / NOT YET VERIFIED on Windows.
**Product Done:** NOT AUTHORIZED. No main merge.

## User journey

> JARVIS, lembre que no projeto JARVIS a palavra de teste é morango.

The single text entry is an explicit direction and (only if Core validation
passes) sufficient authority to create this exact low-risk memory. Do **not**
open a second confirmation dialog for this class of action. The response
"Guardei essa informação ..." is emitted only after an actual confirmed
response from Sofias Memory and is persisted to the same conversation.
A scheduler reminder is **not** a cognitive memory; this branch does not
implement scheduling, microphone or TTS.

## Bounded Core decision

`TextIntentRouter` classifies `memory_create` but grants no authority.
`evaluate_direct_create()` separately checks the ORIGINAL user utterance,
its explicit imperative, short non-sensitive content, unambiguous scope
(`global` or `project:jarvis`), no compound/quoted request, no dates/tasks,
and no obvious privacy/secret patterns. Results:
`PERMITTED`, `CLARIFY`, `DENIED`.

This is a **conservative initial text pilot**. It deliberately does not
support full multi-turn anaphora or arbitrary project scopes. An uncertain
scope prompts a plain-language clarification and writes nothing.
The current LLM's proposed scope cannot contradict Core's resolution;
content is extracted from the user's original utterance rather than a
model-generated rewrite.

`ConversationRuntime` records the user message **before** the remote
Create. `PersonalMemoryLifecycle.create` verifies the exact persisted
message, conversation, content and scope **again** before journal
`prepare` and network effect. A new, strictly Create-only
`PersonalMutationAuthorization(user_direct_intent)` uses the immutable
`user-message:<source_uuid>` as `confirmation_ref`, with SQLite unique
constraint and local transaction verifying the user message exists.
This avoids duplicate operations when the same message is replayed.
Provider calls retain operation UUID/idempotency key and
`user_asserted` provenance. Uncertain results remain UNKNOWN with
no retry. No authority is inferred from retrieved Knowledge, Memory,
or the model. Update/Forget remain separately controlled.

The previous desktop-approved Create code remains in the branch but is
**not invoked by an explicit, Core-permitted text Create**. Scope
ambiguities are surfaced in natural language, not via a forced click.

## Regression gate

Prior Windows baseline: **245 passed / successful Vite build**.
Additional offline tests target:
- admissible low-risk explicit utterances and scoped original text
- quoted/inferred, temporal, compound and unsafe content rejection
- no fabricated authorization from model content or wrong scope
- local message correlation, durable audit, and unique source replay
- remote confirmed Create, remote UNKNOWN, and no Connection degradation
- preserved behavior for read-only Knowledge/Recall and other tools

**Run on owner Windows (desktop closed):**

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

Do **not** initiate a real, non-disposable Create while these are untested.
After pytest/build pass, first verify a clearly ambiguous phrase results
in a clarification without any new operation; then, only with the
owner's deliberate disposable test request, validate a real low-risk
`project:jarvis` Create without clicking anything, the remote
`active` UUID, local `confirmed` journal carrying the original
user-message reference, and persisted single assistant reply after
restarting. Do not alter original teal preference. Test no duplicates,
timeouts and safe shutdown. Only after human acceptance can the
increment be marked PASS and the next target (natural Update/Forget
decision evaluation) be approached.

## Test collection estimate (not an acceptance result)

Previous owner-validated baseline: **245 passed**. New parametrized
cases added so far: 4 permitted examples, 14 rejected risky/quoted/
compound examples, 4 ambiguous scopes, 1 classification/authority
case; plus 3 lifecycle audit/replay cases and 5 end-to-end/failure
desktop worker cases. **Expected 276 collected cases**. This number
is based on test-file inspection, not a run on the owner Windows
environment. If the count or failures differ, investigate rather
than altering safety assertions to force a green run.

One important limitation: this conservative pilot does not yet perform
semantic equivalence/contradiction checks against all existing Memory
records. Repeated, newly authored requests with *new message IDs*
remain distinct explicit requests; only replay of the exact same
source message is blocked. Record/deduplication and target-resolution
are future decision-evaluation work, not validated here.

## Owner Windows gate — 276 automated tests PASS

Owner-reported verification for this branch on Windows (2026-11-01):

- `python -m pytest -q`: **276 passed in 10.26s**.
- `npm run build`: **PASS** in **5.08s** (Vite v7.3.7, 559 modules transformed).
- The JS bundle exceeds 500 kB, yielding a non-blocking chunk warning.

**Automated regression/build acceptance: PASS.** This does **not**
establish human desktop decision routing, a live Sofias Memory Create,
remote ACK, or durability after restart. Those remain **PENDING**.

First required owner smoke: send a natural ambiguous request with no
explicit scope; JARVIS must ask whether the information is global or
project-specific and must not add a memory journal operation.
Only then may a separate, intentionally disposable request exercise
the low-risk direct Create workflow with no second click. Verify remote
active state, `user_direct_intent` receipt bound to `user-message:<uuid>`,
single successful assistant response, and restart persistence.
Do not mutate the original global teal preference. No `main` merge.

## Desktop composer regression after clearing conversations (owner report)

The owner reported that desktop launch succeeded but neither
`Ctrl+Enter` nor the `Enviar` button submitted a message. This
**blocks human direct-Create smoke**; no memory mutation was attempted.

Code audit found a plausible silent front-end lockout: after the owner
tested deleting all conversations, the Vue app correctly left
`selected = ''` and did not create a replacement conversation.
However, both `sendMessage()` and the `Enviar` button required a
preselected conversation. With none selected, the textarea remained
editable but both submission paths silently refused to run.
A second silent path was an empty OpenAI model field: the button was
disabled and sendMessage returned without a warning.

On the feature branch, the composer now creates a new conversation
**only when the user actually submits nonempty text**, under a send lock
set before any asynchronous Qt call. This preserves the intentional
empty-history state while preventing duplicate conversations if
Ctrl+Enter and click occur together. The submit button no longer
requires an already selected chat or model; when the model is missing,
the handler shows an actionable warning and retains the draft.
Missing bridge/model errors also keep the text for retry. The empty
state explains the create-on-send behavior.

Three **static wiring regression tests** were added for the send
handler, Qt call, keyboard/click binding and visible error path.
These are not proof of actual Qt WebView behavior.

**Status:** suspected UI gating bug repaired in source, not confirmed
as the owner's exact runtime cause. Windows pytest, Vite build and
a read-only chat smoke are required before resuming any Memory
write test. No schema migration, remote Memory mutation, main merge,
or Product Done is implied.

Suggested safe check: from the desktop, delete/select no conversation
(or use a disposable empty-history state), type `Oi, JARVIS`,
press Ctrl+Enter; verify a conversation appears and the reply arrives.
Then send a second ordinary text with the button. If either still
fails, report whether Enviar is disabled, whether a chat is selected,
the OpenAI model field, any on-screen warning and lifecycle logs;
do not blindly retry mutating requests.

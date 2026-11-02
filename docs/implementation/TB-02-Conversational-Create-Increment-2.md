# TB-02 — Text Increment 2: Conversational Supervised Create

**Status:** Feature branch implementation committed; **Windows pytest, Vite build and human desktop cancellation smoke PENDING**. No main merge, Product Done or live write accepted.

## Owner-facing product behavior

An explicit natural user message such as "JARVIS, lembre que no projeto JARVIS prefiro Vuetify 3" is first classified into a typed `memory_create` intent. The classifier cannot call Cognitive Memory. Only after the assistant has finished its reply does the desktop show a **Guardar esta informação?** preview containing the extracted content and scope. The user may decline via **Não guardar**. If scope is ambiguous, the dialog asks the user to choose **Minha preferência geral** or **Somente para o projeto JARVIS**; no unknown project or global preference is inferred silently.

The separate **Guardar informação** click submits a one-use, 180-second, conversation-bound approval. There are **no slash commands, target UUIDs, or technical confirmation phrases in this Create UI**. The old CLI and UUID-bound Supersede/Forget remain engineering paths, not the natural-language product interface.

## Technical / safety behavior

- `TextIntentRouter` continues to classify only; the returned content/scope are **untrusted proposal data**, not an execution grant.
- A dedicated `ReplyWorker.createProposed` Qt signal transports the proposal. The bridge holds the preview until the reply worker has shut down; it then issues a one-time random capability in `PersonalCreateGate`.
- `PersonalCreateGate.offer/consume` validates content size, preliminary credential patterns, strict scope allowlist, exact conversation UUID, expiry and one-use semantics. Wrong scope, wrong conversation, cancellation, expiry and replay fail closed.
- `PersonalMutationAuthorization.from_desktop_approval` is accepted for **Create only** and records `desktop_approved` in the existing SQLite v4/v5 operation journal; it cannot be substituted for typed approvals of Supersede/Forget.
- `PersonalMemoryLifecycle.create` verifies the approval, content, scope/type, provenance, then calls `journal.prepare` **before** the external effect. `claim`, idempotency, service ACK and `confirmed/unknown/rejected` handling follow the existing fail-closed lifecycle.
- The new remote Create preserves `user_asserted` origin, the unique `memory-operation:<operation_id>` local ownership reference, conversation UUID and confirmation reference.
- Successful remote Create is verified for active lifecycle, content, scope, type and provenance. The journal retains the approval metadata after the payload is scrubbed. No silent retry is attempted for `RESULT_UNKNOWN`.
- Only **after confirmed remote ACK**, a content-free assistant acknowledgement ("Informação guardada no Sofias Memory ...") is appended to the local conversation. Failure to persist this second acknowledgement does not undo or misrepresent remote success and is surfaced separately.
- `memory_update` and `memory_forget` remain recognized but not auto-executed. They still need secure resolution of the *current, owner-eligible target* and a readable one-use confirmation. Scheduler, voice, TTS and autonomous writes remain deferred.
- Retaining a chat transcript is distinct from retaining Cognitive Memory; deleting a local chat does not forget cognitive records or erase journal audit.

## Automated regression gate

Previous accepted Windows baseline **235 passing tests**. Ten additional automated cases were added (Create gate 3, lifecycle 3, desktop 4). Expected new collection **245 passing tests**, NOT yet run by the owner.

```powershell
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
```

Review pytest/build output first. If both pass, the first human desktop test is **preview and cancel only** with an innocuous disposable, explicit `project:jarvis` request. Check content/scope and choose **Não guardar**, never **Guardar informação** in this first smoke. Verify no remote mutation, no new `desktop_approved` journal entry, and orderly shutdown. No further live test is authorized in this checkpoint.

A separate, later owner-approved disposable real Create test must verify returned UUID, live `active` state, journal `confirmed/desktop_approved`, and persisted conversational acknowledgement. The original global teal preference remains out of scope. **Do not declare Increment 2 accepted or TB-02 Product Done before these gates.**

## Windows gate: supervised natural Create (2026-11-01)

Owner independently ran and reported:

- `python -m pytest -q`: **245 passed in 9.66s**
- `npm run build`: **PASS**, Vite v7.3.7, 559 modules transformed, completed in **5.20s**.
- Bundled JS remains >500 kB (non-blocking optimization warning).

**Verdict:** offline regression and frontend compilation **PASS**.
No Windows visual Create preview/cancel evidence yet, and no actual
new supervised Cognitive Memory Create has been authorized or verified.

**Next human check:** on Windows desktop, submit
"JARVIS, lembre que no projeto JARVIS a palavra de teste é morango."
Expected: readable Create preview with correct proposed text, intended
`project:jarvis` scope, and Cancel vs Guardar actions. The user must
press **Não guardar** (NOT Guardar informação), then confirm subsequent
normal chat/shutdown. Read-only local SQLite journal checks may be
performed before and after to ensure no `desktop_approved` write
operation was prepared. The preserved real teal memory is out of scope.

Do not declare B-01 conversational Create Product Done until real human
checks are accepted. No merge to main.

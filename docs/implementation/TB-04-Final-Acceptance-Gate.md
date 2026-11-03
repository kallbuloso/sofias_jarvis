# JARVIS — TB-04 Final Acceptance Gate

**Status:** IN PROGRESS / NOT PRODUCT DONE
**Branch:** `feat/tb-04-providers-connections`
**Date:** 2026-11-03
**Baseline:** TB-04 Providers & Connections Plan, CONTRACT-04, CONTRACT-07.

This checklist records implementation and the owner's observed evidence separately. Do not conflate published code, static assertions, simulated unit tests, real Windows checks or production readiness.

## Acceptance inventory

| Product Done gate | Evidence so far | Decision |
|---|---|---|
| 1. GitHub Connection Manager real lifecycle | Owner previously validated a real GitHub token, identity, inspection and state changes | ACCEPTED |
| 2. OpenAI behind selectable AI Connection | Owner previously validated inference, disable/re-enable and migration | ACCEPTED |
| 3. Second AI Provider works in Conversation | Anthropic and Gemini previously exercised with LiteLLM; latest Gemini Conversation screenshot shows success | ACCEPTED for exercised paths |
| 4. Manual provider/model switching preserves Conversation + Memory + Knowledge | Per-conversation profile and Gemini response observed; complete same-Conversation multi-provider Memory and Knowledge continuity not demonstrated by the latest supplied evidence | ADDITIONAL SMOKE NEEDED |
| 5. Secrets never enter SQLite/UI/log | Existing tests, keyring boundaries and new TB-04 catalog security tests cover stored/public output, isolation and rollback; end-to-end new-connection Windows smoke and log review are not newly evidenced | VERIFY FINAL |
| 6. Disabled AI Connection rejects new inference | Owner previously validated disable/re-enable with OpenAI; automated tests also protect the boundary | ACCEPTED |
| 7. Restart keeps non-secret selection/state | Owner previously validated persistence across restart | ACCEPTED; final smoke desirable |
| 8. Full tests, frontend build, desktop smoke | Owner passed full Python regression, Vite build and catalog/diagnostics desktop smoke on 2026-11-03, **before** the subsequent UX/security refinement | REPEAT AFTER LATEST COMMITS |

## Current follow-up: catalog UX and trust-boundary refinement

- The create Connection selector now lists only providers with a trusted, supported JARVIS connection contract (currently OpenAI/Anthropic/Gemini).
- Other SDK-known providers are displayed in a separate expandable **read-only catalog**, searchable by name or ID, at most 20 results on screen. This avoids a long dropdown dominated by unavailable providers.
- `ProviderDescriptor.supports_ai_api_key_connection()` is now the shared trusted predicate used by both catalog rendering and `ConnectionManager.create_ai()`. An SDK-discovered provider cannot bypass the Connection Manager's own admission policy.
- Additional focused tests cover unknown provider rejection, two independent secrets, public/SQLite redaction, vault-write rollback and incompatible auth methods.

### Expected commands on Windows

From `D:\Applications\sofias_jarvis` on `feat/tb-04-providers-connections`, after confirming a clean worktree:

```powershell
git fetch origin
git switch feat/tb-04-providers-connections
git pull --ff-only origin feat/tb-04-providers-connections
.\.venv\Scripts\python.exe -m pytest -q tests/test_ai_catalog_tb04.py tests/test_inference_profile_ui_tb04.py
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe main.py --desktop
```

### Desktop smoke (no new credentials required for UX)

1. Open Integrations: the **configured/managed provider selector** should have only OpenAI, Anthropic and Google Gemini.
2. Expand the read-only LiteLLM catalog; filter a known provider, confirm the results remain non-actionable and UI stays responsive.
3. Clear the search field; it must not generate a Vue error.
4. Verify the existing Anthropic/Gemini/OpenAI Connections and Inference Profiles remain.
5. Send a minimal conversation turn through the previously configured Gemini profile.
6. Close/reopen the desktop and verify persisted Connection/Profile data.

### Additional security/continuity gate before Product Done

A controlled end-to-end test of a **new test Connection** is still necessary (not an existing production credential): create in generic form, verify (when supported), enable, confirm no secret is returned from WebChannel or appears in SQLite/logs, then remove and confirm only that test Connection's vault entry is deleted. Avoid displaying, pasting or logging keys. Do this only with a disposable credential or approved isolated test configuration.

Also verify a same-Conversation manual switch across two working AI Providers while Memory/Knowledge context is configured, without assuming those subsystems operated just because text inference succeeded. Record actual evidence before marking gate 4 accepted.

**No automatic merge to `main`.** TB-05 is not started merely because these tests pass.

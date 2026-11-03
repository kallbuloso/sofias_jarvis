# JARVIS — TB-04E2 Dynamic AI Provider Catalog

**Status:** FUNCTIONALLY ACCEPTED BY OWNER / REMAINING FINAL SECURITY GATES
**Branch:** `feat/tb-04-providers-connections`
**Baseline:** CONTRACT-04, CONTRACT-07, TB-04C LiteLLM parity, TB-04E1 diagnostics.

## Scope delivered

- `jarvis.connections.catalog.LiteLLMProviderCatalog` merges local LiteLLM SDK provider/field metadata with the trusted JARVIS Provider Registry.
- SDK provider discovery is **read-only** and does not use provider API keys, the SQLite credential store, environment-based account verification or external discovery calls.
- `ConnectionManager.ai_catalog()` exposes a normalized, non-secret catalog.
- `loadAIProviderCatalog` uses the existing connection worker/QThread instead of loading SDK metadata on the GUI thread.
- A single Vuetify form replaces the hardcoded Anthropic/Gemini connection forms.
- The dropdown shows SDK-known providers, while **catalog-only** providers are disabled for connection creation.
- OpenAI/Anthropic/Gemini remain the three managed AI Connection descriptors with an API-key credential form.
- Existing `configureAIConnection`, `verify_ai`, `diagnose_ai`, Windows Credential Manager and explicit Provider/Connection/Model selection stay authoritative.
- SDK field defaults are **not** forwarded to the UI; only non-secret field descriptors are included.

## Critical distinction

| State | Meaning |
|---|---|
| SDK catalog presence | LiteLLM recognizes a provider identifier; this is **not** an availability or compatibility guarantee |
| `catalog_only` | Metadata can be displayed, but JARVIS has not implemented a safe Connection/runtime contract |
| `managed` | Trusted JARVIS registry allows creating a connection with its currently supported credential mechanism |
| Connection `configured` | Required local credential is present in the vault |
| Connection `available` | External check succeeded where supported; may subsequently change |
| Model selected | User selected an identifier; this alone does not verify account availability |
| Model capability hint | LiteLLM metadata suggests supported parameters; it does not prove structured JSON or streaming end-to-end |

The active JARVIS Connection Manager continues to admit only registered providers. Do **not** dynamically authorize all items in LiteLLM's `provider_list`.

## Why arbitrary SDK fields are not actionable yet

The current CONTRACT-07 implementation securely stores exactly one connection-owned API key. A provider may require non-API-key credentials, multiple secrets, endpoint configuration, OAuth, local runtime settings or signed requests. Blindly rendering those fields and calling `create_ai(provider_id, api_key)` would give a false guarantee of support and risk misconfiguration. Metadata-only fields are available in the catalog, but the actionable form uses only the supported JARVIS connection-field contract.

For the same reason, `get_valid_models()` is not treated as proof of per-Connection availability: SDK/environment-level credentials must not substitute for the selected JARVIS Connection. Existing authenticated provider verification is still the authority for observed models.

## Next acceptance gate

1. Run `python -m pytest -q tests/test_ai_catalog_tb04.py tests/test_litellm_diagnostics_tb04.py`.
2. Run `python -m pytest -q`.
3. Run `cd frontend && npm run build`.
4. Windows desktop smoke: open Integrations and confirm the searchable catalog loads without freezing.
5. Confirm catalog-only providers cannot be connected and the three registered AI providers use the same form.
6. Create and verify a test Connection with the generic form, with its key absent from SQLite, console logs and WebChannel responses.
7. Verify existing OpenAI/Anthropic/Gemini Connections, inference profiles and model preferences are preserved after restart.
8. Repeat TB-04E1 three-probe diagnostics on the configured Gemini Connection and separate provider/model faults from schema/streaming faults.

No PRODUCT DONE claim until these checks and real Windows/credential smoke pass.

## Owner validation evidence — 2026-11-03

The owner confirmed that the Python regression, frontend production build and manually exercised desktop checks passed.

Observed in supplied Windows desktop screenshots:

- The LiteLLM catalog loads and reports **158 providers catalog-only**.
- Existing Anthropic and Google Gemini Connections are configured, enabled and reported `available`.
- The existing OpenAI Connection is configured and enabled with `availability=unknown`; OpenAI has no current authenticated status-check flow in this TB-04 implementation, so the state is intentionally not promoted to available.
- Gemini `gemini-3.5-flash` diagnostic on LiteLLM 1.106.6: `plain=OK (1269ms)`, `structured=OK (2462ms)`, `streaming=OK (2209ms)`, `first_token=2183ms`.
- A Gemini-bound Conversation profile produced the expected text response `funcionou` for the owner's test prompt.

**Decision:** TB-04E2 catalog/form functional acceptance recorded. This does not assert that a new Connection was created and verified during this smoke, that every LiteLLM provider is connectable, that the Windows vault exposure paths were re-audited, or that TB-04 overall has satisfied the Product Done gate.

**UX follow-up:** the alphabetic autocomplete surfaces a long run of unsupported `catalog_only` entries before manageable providers. Prefer a distinct supported group or sort connectable entries first in a later UI refinement, without changing Connection Manager trust boundaries.

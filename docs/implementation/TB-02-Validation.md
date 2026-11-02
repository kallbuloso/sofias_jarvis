# JARVIS — TB-02 Completion Evidence

**Slice:** TB-02 — Memória e conhecimento  
**Status:** PRODUCT DONE — validated by owner  
**Validation date:** 2026-11-01  
**Repository:** `kallbuloso/sofias_jarvis`  
**Implementation branch:** `feat/tb-02-memory-knowledge`  
**Target branch:** `main` — PR prepared after Product Done

## Delivered capability

TB-02 closes the first usable Memory + Knowledge vertical slice of JARVIS:

- real Sofias Memory contract/capability negotiation;
- Cognitive Memory Create/Get/Recall/Supersede/Forget;
- natural-language-first desktop routing;
- explicit low-risk Create executes directly from the persisted user request;
- explicit unambiguous Update executes directly after Core-owned target resolution;
- Forget resolves the target, asks for confirmation in the conversation and consumes one explicit `Confirmo` bound to that pending operation;
- ambiguous, foreign, test or unresolved memories are not mutated;
- mutation journal/idempotency and RESULT_UNKNOWN no-auto-retry behavior;
- Knowledge Retrieval through the approved `jarvis-knowledge` dataset;
- durable per-assistant-message Knowledge evidence in SQLite;
- conversation switching/restart preserves Knowledge evidence;
- Sofias Memory unavailable/incompatible states fail closed without claiming success;
- legacy UUID/slash mutation paths remain engineering/diagnostic surfaces, not the normal UX.

## Human validation

Owner validated on Windows 11:

1. **Create:** natural request persisted successfully in Sofias Memory without a second confirmation.
2. **Update:** natural explicit request changed the target memory directly, with no modal.
3. **Forget:** JARVIS asked for confirmation in the conversation; `Confirmo.` executed the Forget and returned `Informação esquecida.`.
4. Desktop remained open and usable after the mutation lifecycle.
5. **Degraded Memory:** with an unreachable Memory URL, JARVIS refused the write and did not claim success.
6. Previous Knowledge smoke validated real ADR-0001 retrieval with Source/Document/Chunk provenance surviving conversation switching and restart.

## Final automated validation

Owner-reported final regression:

```text
297 passed in 11.71s
```

Final frontend production build:

```text
vite v7.3.7
559 modules transformed
built in 5.49s
```

Vite emitted only the existing chunk-size warning (>500 kB); build succeeded.

## Authorization semantics accepted in TB-02

| Operation | Normal conversational authority |
|---|---|
| Create low-risk, explicit and unambiguous | Direct execution from persisted user request |
| Update low-risk, explicit and unambiguous | Direct execution from persisted user request after owned-target resolution |
| Forget | Conversational confirmation required; pending target + conversation + one-use gate |
| Ambiguous target | No mutation; require clarification |
| Critical future side effect | Outside TB-02; expected to require stronger proportional confirmation, potentially conversational + explicit UI approval |

The last row records the product direction agreed during TB-02 but does not implement TB-06 execution policy.

## Degradation and safety evidence

- A write is never reported as complete without a confirmed Memory acknowledgement.
- Unknown mutation outcome is not retried automatically.
- Target resolution accepts only memories locally proven as JARVIS-owned for the configured service.
- Test/foreign records are ineligible for natural mutation.
- Forget confirmation is consumed before LLM intent routing and is bound to the pending conversation/target.
- Sofias Memory unavailability blocks the dependent function without taking down the desktop.

## Deferred / not claimed

- Voice/STT/TTS and spoken confirmation are TB-03+ work.
- General execution-risk policy and critical side-effect UI authorization are not implemented by TB-02.
- Multi-user/multi-space tenancy remains outside the MVP architecture.
- Knowledge contradiction resolution across multiple competing sources was not proven by the single-ADR pilot.
- Frontend bundle splitting is an optimization, not a TB-02 acceptance blocker.

## Product Done decision

All material TB-02 acceptance gaps identified during implementation were closed and revalidated. Final full regression, production frontend build, real desktop mutation smoke and degraded-service smoke passed.

**TB-02 = PRODUCT DONE.**

No claim is made that TB-03 or later slices are implemented by this completion record.

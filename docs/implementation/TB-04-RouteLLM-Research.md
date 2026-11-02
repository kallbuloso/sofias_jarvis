# JARVIS — RouteLLM / Dynamic Model Routing Research

**Status:** DISCARDED — no implementation planned  
**Date:** 2026-11-02  
**Scope:** assess whether RouteLLM should enter TB-04 now or later as a cost/quality optimization.

## Executive finding

Do **not** add the LMSYS RouteLLM package as a TB-04 dependency now.

Keep the approved LiteLLM transition SPEC frozen and complete LiteLLM parity first.

However, preserve a future architectural extension point for **dynamic model selection** inside JARVIS `InferenceResolver` / `InferenceProfile`.

The future implementation should evaluate:

1. LiteLLM Auto Router / Autorouter SDK;
2. a JARVIS-owned custom routing strategy;
3. LMSYS RouteLLM only if it provides measurable value on JARVIS traffic.

## Why RouteLLM is interesting

RouteLLM is specifically designed to route prompts between a stronger/more expensive model and a weaker/cheaper model according to an estimated quality/cost tradeoff.

Its published work reports large benchmark cost reductions while attempting to preserve most strong-model quality.

That is conceptually valuable for JARVIS.

## Why it should not enter the frozen SPEC now

### 1. RouteLLM already depends on LiteLLM

RouteLLM's controller calls LiteLLM for provider/model execution.

Adding it now would create:

```text
JARVIS
  → RouteLLM
    → LiteLLM
      → provider
```

while our approved architecture already needs:

```text
JARVIS policy
  → LiteLLM
    → provider
```

The extra layer must therefore justify itself by routing quality, not provider compatibility.

### 2. Current RouteLLM model is primarily binary strong-vs-weak

Its core abstraction routes between two models using a threshold.

JARVIS needs a broader policy space:

- multiple providers;
- multiple models per provider;
- Agent-specific profiles;
- Project/Task/Conversation bindings;
- capability constraints;
- local/cloud privacy;
- budget;
- reasoning effort;
- context-window requirements;
- fallback eligibility.

Binary strong/weak selection is useful as one strategy, not as the JARVIS inference architecture.

### 3. Multi-turn semantics are a weak fit

Current RouteLLM controller routes using the last message content and contains an explicit note that the available routers were trained on first-turn data and that multi-turn requires more research.

JARVIS is explicitly conversation-continuous and future agent/task context is multi-turn by design.

### 4. The packaged research routers are old relative to current models

The released routers were trained around GPT-4-1106-preview vs Mixtral-8x7B preference data.

The project claims transfer to other strong/weak pairs, but JARVIS should not assume that transfer quality is adequate for 2026 model families without evaluation on its own traffic.

### 5. Desktop dependency weight

RouteLLM 0.2.0 currently declares dependencies including:

- torch;
- transformers;
- datasets;
- pandas;
- scikit-learn;
- numpy;
- LiteLLM.

That is a large dependency footprint for the local-first Windows desktop merely to gain a routing heuristic.

### 6. Some supplied routers still require OpenAI embeddings

RouteLLM documentation states that MF and SW-ranking still require an OpenAI API key for embeddings even when the routed strong/weak models are different.

That conflicts with the desired provider-neutral/local-private direction unless deliberately accepted.

## Important 2026 development: LiteLLM now has Auto Routing

Current LiteLLM provides an Autorouter SDK for Python applications.

It can classify into tiers such as:

```text
SIMPLE
MEDIUM
COMPLEX
REASONING
```

and map each tier to a model or pool.

Current classifiers include:

- heuristic;
- LLM classifier;
- JEV;
- lexical/semantic keyword rules;
- custom classifier plugin.

It also supports:

- model pools;
- adaptive Thompson sampling;
- session affinity;
- context-window escalation;
- routing by reasoning effort;
- custom Python classification;
- routing observability/evaluation.

This overlaps substantially with the problem RouteLLM would solve, but lives directly inside the LiteLLM layer already proposed for JARVIS.

Auto Router is currently marked Beta, so it should not be treated as unquestioned production policy without JARVIS-specific evaluation.

## Recommended JARVIS architecture

The frozen SPEC should remain unchanged for the LiteLLM migration.

Future routing should plug into the JARVIS-owned resolver:

```text
Invocation / Task / Agent / Project
              ↓
       InferenceResolver
              ↓
       InferenceProfile
              ↓
      ModelSelectionStrategy
        ├─ FIXED
        ├─ TIERED
        ├─ AUTO_COMPLEXITY
        └─ CUSTOM (future)
              ↓
      ResolvedInferencePlan
              ↓
         CONTRACT-04
              ↓
           LiteLLM
              ↓
           Provider
```

A router chooses a **model candidate**, not authority.

## Proposed future InferenceProfile shape

```yaml
id: general

selection:
  mode: fixed

primary:
  connection: openai-principal
  model: openai/gpt-6-luna

fallbacks:
  - connection: anthropic-principal
    model: anthropic/claude-sonnet-5-5

requirements:
  streaming: true
  structured_output: true
```

Later:

```yaml
id: general-economical

selection:
  mode: auto_complexity

tiers:
  simple:
    connection: cheap-provider
    model: provider/cheap-model

  medium:
    connection: openai-principal
    model: openai/mid-model

  complex:
    connection: anthropic-principal
    model: anthropic/claude-sonnet

  reasoning:
    connection: frontier-provider
    model: provider/frontier-model

constraints:
  max_cost_per_request: ...
  cloud_allowed: true
```

The Agent still points only to an `InferenceProfile`.

## RouteLLM possible future role

If later benchmarks show RouteLLM materially outperforms LiteLLM Auto Router or our own classifier on JARVIS traffic, it can become another `ModelSelectionStrategy`:

```text
ModelSelectionStrategy
   ├─ FixedSelection
   ├─ LiteLLMAutoRouterSelection
   └─ RouteLLMSelection
```

It must not sit between JARVIS authority/policy and the provider in a way that owns Agent/Task/Project policy.

## Evaluation before enabling dynamic routing

Never enable automatic cost routing from benchmark marketing claims alone.

Required JARVIS evaluation dataset should contain real or representative categories:

- normal conversation;
- memory intent routing;
- knowledge retrieval;
- coding;
- long-context analysis;
- structured output;
- agent planning;
- tool proposals;
- tasks with different risk/cost profiles.

Measure:

- task success / quality;
- structured output correctness;
- chosen model;
- input/output tokens;
- classifier cost;
- total inference cost;
- routing latency;
- fallback rate;
- under-routing failures;
- over-routing waste.

Under-routing a hard task to a cheap model is more damaging than over-routing a trivial task to an expensive model, so policy thresholds should be asymmetric where appropriate.

## Recommended timing

### Now

Freeze the approved LiteLLM transition SPEC.

Complete:

1. LiteLLM parity;
2. InferenceProfile;
3. InferenceResolver;
4. third-provider proof without native adapter.

### Then

Add a **routing experiment phase**:

1. fixed profile baseline;
2. LiteLLM heuristic Auto Router in shadow/evaluation mode;
3. optional LLM/custom classifier;
4. optionally RouteLLM benchmark;
5. compare quality/cost on JARVIS traffic;
6. enable dynamic routing only if measured benefit is material.

## Decision recommendation

Treat **dynamic routing as a policy optimization after the provider abstraction**, not as part of the LiteLLM migration itself.

Freeze the current approved SPEC and do not add LMSYS RouteLLM as a required dependency.

Design the future `InferenceResolver` so RouteLLM, LiteLLM Auto Router, or a JARVIS-native classifier can be swapped as a model-selection strategy without changing Agents, Projects, Tasks, Connections or CONTRACT-04.

## Final owner decision — 2026-11-02

RouteLLM was explicitly discarded by the owner.

It is not a dependency, roadmap requirement, fallback mechanism or planned `ModelSelectionStrategy` for the current JARVIS architecture.

Future dynamic routing remains an independent architectural concern and may be revisited using LiteLLM-native routing or another deliberately evaluated strategy, but this research document does not authorize RouteLLM implementation.


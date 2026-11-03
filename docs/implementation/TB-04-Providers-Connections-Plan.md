# JARVIS — TB-04 Providers & Connections Plan

**Slice:** TB-04 — Providers e conexões  
**Status:** APPROVED / IN PROGRESS  
**Branch:** `feat/tb-04-providers-connections`  
**Baseline:** SPEC-05, SPEC-06, CONTRACT-01, CONTRACT-07, ARCH-06 e ADR-0006 já aprovados.

## Objective

Entregar uma arquitetura utilizável de **AI Providers & Connections** para que o JARVIS possa trocar explicitamente de provedor/modelo de inferência sem alterar Conversation, Memory, Knowledge, Voice ou autoridade do Core.

O Connection Manager genérico continua válido e o GitHub permanece como prova real já implementada do lifecycle de conexões externas, mas deixa de ser a direção principal do TB-04.

TB-04 não executa tools de negócio. Consultas externas ficam no TB-05; efeitos externos permanecem no TB-06.

## Correção de escopo — 2026-11-02

A implementação inicial interpretou "Providers e conexões" prioritariamente como integrações externas. Após validação do GitHub, o proprietário esclareceu que o valor prioritário esperado é **rotacionar providers de LLM**.

Decisão revisada:

- manter GitHub como foundation validada do Connection Manager;
- **não implementar Google Calendar neste momento**;
- reorientar o restante do TB-04 para AI Providers;
- `ARCH-R05 / PRD OQ-01` volta a **OPEN** para escolha futura dos dois domínios externos do MVP, a ser fechada antes dos Slices realmente dependentes (TB-05/TB-06);
- fallback automático de provider continua DEFERRED; o TB-04 entrega seleção/rotação explícita.

## Invariantes do Slice

- `Provider != Connection != Capability`.
- `registered != configured != enabled != authorized != available`.
- Nenhuma conexão autenticada concede grant de execução.
- Credencial externa nunca entra no SQLite, logs, Conversation ou Sofias Memory.
- Vue/WebChannel nunca recebe segredo armazenado.
- Uma conexão usa somente seu próprio `credential_ref`.
- Multi-conexão do mesmo provider usa identidades e secrets independentes.
- Estado desconhecido permanece `unknown`; nunca virar `allowed` ou `available` por inferência.
- Remove local não significa revoke remoto.
- Disable bloqueia novas admissões futuras, mas não inventa cancelamento de operação já enviada.
- Nenhum adapter externo entra por import/download dinâmico neste Slice.

## Technical baseline

### Provider Registry

Registry explícito e local de adapters confiáveis compostos com o aplicativo.

Descriptor mínimo:

- `provider_id`
- `provider_type`
- `contract_versions`
- `capabilities`
- `connection_requirements`
- `supported_auth_methods`
- `multi_connection_support`
- `status_check_support`
- `reconnect_support`
- `provider_revoke_support`

TB-04 registra GitHub como integração externa já validada e passa a registrar **OpenAI como primeiro AI Provider real**. O retrofit de OpenAI é agora parte deliberada do Slice; Voice e Sofias Memory não serão migrados para o Registry sem necessidade concreta.

### Connection Store

SQLite mantém somente estado operacional não secreto:

- `connection_id` UUID estável
- `provider_id`
- `display_identity`
- `external_account_ref`
- `credential_ref`
- configuração não secreta
- `enabled`
- permissões observadas
- disponibilidade observada
- `last_verified_at`
- timestamps

`configured`, `authorized` e `available` permanecem dimensões independentes; não criar um único status linear que esconda essa diferença.

### Secret Store

Adicionar armazenamento genérico de segredo de conexão sobre Windows Credential Manager.

- segredo indexado por `connection_id`;
- SQLite guarda apenas `credential_ref`;
- OpenAI/Sofias Memory atuais permanecem funcionando sem migração forçada;
- falha do vault é fail-closed;
- nenhum fallback plaintext.

## Increment 1 — Connection Core + GitHub

**Implementation status:** DONE and owner-validated on Windows. Focused suite: 39 passed; frontend build PASS; real GitHub connection lifecycle PASS.

### Auth

Fine-grained Personal Access Token fornecido pelo proprietário e armazenado no Windows Credential Manager.

### Flow

`Registry → Create Connection → store secret → Inspect → identity/status → Enable/Disable/Remove`

### Acceptance

- GitHub aparece como provider conhecido;
- conexão recebe UUID local;
- token nunca é retornado pela UI/Core query;
- inspeção real identifica a conta GitHub;
- falha 401/403/timeout é normalizada;
- conexão pode ser habilitada/desabilitada;
- restart preserva identidade/configuração e enabled state;
- remover apaga vínculo local e segredo, sem alegar revogação no GitHub;
- duas conexões GitHub, se criadas, permanecem isoladas;
- nenhuma capability de negócio é executada por TB-04.

## Increment 1B — OpenAI como AI Connection real

**Goal:** manter o comportamento atual do JARVIS, mas remover OpenAI hardcoded da composição do runtime.

### Flow

`Conversation → Inference Runtime → AI Provider Registry → OpenAI Connection → OpenAI Adapter`

### Acceptance

- OpenAI aparece como `provider_type=ai_inference`;
- credencial atual é migrada internamente para uma connection sem exposição ou nova digitação;
- runtime recebe `provider_id + connection_id + model_id`;
- Conversation continua usando o mesmo histórico/contexto;
- intent classification usa a mesma AI Connection selecionada, sem chamada OpenAI escondida fora do adapter;
- Memory/Knowledge continuam envolvendo o provider selecionado sem conhecer sua implementação;
- comportamento existente de OpenAI permanece funcional;
- conexão desabilitada não pode iniciar nova inferência;
- seleção default persiste sem armazenar secret.

## Increment 2 — Segundo AI Provider real

Adicionar um segundo provider somente depois que OpenAI estiver totalmente atrás do CONTRACT-04/Connection Manager.

A escolha entre Anthropic, Gemini ou outro provider será feita contra as APIs atuais e deverá provar que o contrato é realmente provider-neutral.

Acceptance central:

`mesma Conversation → turno com provider A → troca explícita → turno com provider B`

Sem perda de histórico, Memory, Knowledge ou autoridade.

## Increment 3 — AI Provider / Connection / Model selector

Superfície simples no desktop:

- Provider;
- Connection;
- Model;
- seleção default persistida;
- disponibilidade/capabilities observadas;
- troca manual explícita.

Sem fallback automático, cost router, load balancing ou seleção autônoma pelo LLM.

## Desktop — Integrations & Settings

Adicionar uma superfície simples, sem dashboard genérico:

- lista de providers conhecidos;
- conexões por provider;
- identidade amigável;
- configured / enabled / availability / permissions observadas;
- Configure / Check / Enable / Disable / Remove;
- fluxo OAuth quando aplicável.

A UI transmite comandos. O Core valida e mantém o estado canônico.

## Out of Scope

- execução de GitHub/Calendar ou outras tools externas na conversa — TB-05;
- CREATE/UPDATE/DELETE externo — TB-06;
- provider marketplace;
- plugin download/dynamic loading;
- MCP obrigatório;
- automatic provider fallback;
- universal router;
- skill/agent framework;
- remote provider revocation obrigatória;
- multi-user.

## Product Done gate

TB-04 poderá ser marcado Product Done quando:

1. foundation do Connection Manager continuar validada com GitHub real;
2. OpenAI operar integralmente como AI Connection selecionável;
3. um segundo AI Provider real operar na mesma Conversation;
4. troca manual Provider/Connection/Model preservar Conversation, Memory e Knowledge;
5. secrets permanecerem fora de SQLite/UI/log;
6. conexão AI desabilitada impedir nova inferência dependente;
7. restart preservar seleção e estado não secreto;
8. focused tests, regressão completa e frontend production build passarem.

TB-05 não é autorizado automaticamente pelo fechamento do TB-04.

## Increment 1 implementation checkpoint — 2026-11-02

Implemented:

- SQLite schema v6 with non-secret `integration_connections`;
- stable UUID connection identity and `credential_ref`;
- generic per-connection Windows Credential Manager storage;
- explicit trusted Provider Registry;
- GitHub provider descriptor;
- GitHub connection inspection through `GET /user`;
- normalized connection/auth/provider failure semantics;
- Connection Manager with Create/Inspect/Enable/Disable/Remove;
- multi-connection isolation by `connection_id`;
- asynchronous desktop Configure/Check through QThread;
- minimal `Integrations` desktop surface;
- password input is cleared after handoff and stored secrets are never rehydrated into Vue;
- existing OpenAI and Sofias Memory secret paths remain untouched;
- focused regression module: `tests/test_connections_tb04.py`.

No GitHub repository/issues tool execution is implemented in this increment.

## Direction checkpoint — 2026-11-02

Owner validated the Connection Manager foundation:

- focused regression: **39 passed**;
- frontend build: PASS;
- real GitHub fine-grained PAT connection: PASS;
- identity `kallbuloso` observed correctly;
- connection reported configured and available.

This proves the generic connection lifecycle. Work now continues with **Increment 1B — OpenAI as an AI Connection**; Google Calendar is intentionally paused.

## Increment 1B implementation checkpoint — 2026-11-02

Implemented:

- OpenAI registered as `provider_type=ai_inference`;
- existing OpenAI Credential Manager entry represented by a normal AI Connection via non-secret `credential_ref=legacy:openai:default`;
- no duplicate API key is created during migration;
- desktop bootstrap materializes the OpenAI AI Connection lazily when the legacy credential exists;
- desktop reply dispatch resolves `provider_id + connection_id + credential` through Connection Manager;
- CLI `--chat` uses the same AI Connection resolution path;
- inference provider construction moved behind `jarvis.inference.factory`;
- `ReplyWorker` no longer imports or constructs OpenAI directly;
- `TextIntentRouter` now depends on provider-neutral structured JSON capability;
- OpenAI adapter implements both streaming text and structured JSON under the CONTRACT-04 boundary;
- Memory and Knowledge wrappers continue to wrap the resolved provider without knowing its implementation;
- desktop labels changed from `Modelo OpenAI` to `Modelo de IA`;
- Integrations UI now separates **AI Providers** from **External Integrations**;
- OpenAI AI Connection can be enabled/disabled independently;
- automatic provider fallback remains unimplemented.

Focused regression additions:

- `tests/test_ai_connections_tb04.py`;
- provider-neutral intent-router tests;
- existing worker tests updated from `api_key` to generic `credential`.

Real Windows validation is still pending.

## Increment 1B human acceptance — 2026-11-02

Owner validated the OpenAI AI Connection refactor on Windows:

- focused regression requested for the AI Connection boundary: PASS;
- frontend production build: PASS;
- OpenAI AI Provider visible/configured/enabled in the desktop: PASS;
- normal conversation after migration: PASS;
- disabling OpenAI blocks dependent inference in a controlled way: PASS;
- re-enabling OpenAI restores inference: PASS;
- restart preserves the connection/state: PASS.

**Increment 1B = ACCEPTED.**

The next implementation target is **Increment 2 — Anthropic as the second real AI Provider**, followed by explicit Provider/Connection/Model rotation in the same Conversation.

## Increment 2 implementation checkpoint — 2026-11-02

Implemented in feature branch:

- Anthropic registered as a second `ai_inference` provider;
- `anthropic>=2,<3` added as runtime dependency;
- `AnthropicMessagesAdapter` implements CONTRACT-04 streaming and structured JSON capabilities;
- provider-specific role translation keeps `developer/system` policy outside ordinary conversation messages;
- unsafe/non-final Anthropic stop reasons are not treated as completed responses;
- Anthropic API keys use the same per-connection Windows Credential Manager boundary;
- Anthropic connections are created configured but disabled until explicitly enabled;
- active AI selection is now `provider_id + connection_id + model`;
- non-secret selection is persisted in `desktop-ai-selection.json`;
- per-provider model preferences are preserved;
- no bootstrap or runtime fallback silently rotates a disabled/missing selected provider to OpenAI;
- desktop toolbar exposes Provider / Connection / Model;
- Integrations surface can configure, enable/disable and remove non-legacy Anthropic connections;
- OpenAI legacy connection remains non-removable in UI during compatibility migration;
- voice STT remains a separate CONTRACT-05 OpenAI adapter and is not claimed as part of LLM provider rotation.

Focused tests added:

- `tests/test_anthropic_ai_provider_tb04.py`;
- `tests/test_ai_rotation_desktop_tb04.py`.

Real Anthropic API and same-Conversation provider-rotation smoke are PENDING.

## Anthropic verification hardening — 2026-11-02

After the first real provider-rotation smoke, the OpenAI turn succeeded but the
Anthropic turn failed closed at conversational intent routing. The owner noted
that the Anthropic API key is old and may have been revoked.

Hardening added before further inference diagnosis:

- Anthropic now advertises `status_check_support=true`;
- AI Provider cards expose a `Verificar` action;
- Anthropic verification uses the authenticated Models API and performs no
  inference;
- successful verification records `availability=available` and
  `last_verified_at`;
- revoked/invalid key records `availability=auth_required` with
  `AUTHENTICATION_FAILED`;
- permission/provider/network failures are normalized separately;
- a connection that has failed verification is fail-closed for inference even
  if its local `enabled` flag remains true;
- the UI shows persisted availability and last verification error;
- available model count is shown for the live verification result;
- no secret is returned to the UI or persisted in SQLite.

The current Anthropic documentation confirms `GET /v1/models` as the
authenticated model-discovery endpoint. The current structured-output syntax
used by the adapter remains `output_config.format` with
`type=json_schema`.

Next real diagnostic: run `Verificar` on the existing Anthropic connection.
If it reports `available`, investigate the classifier request/error
separately; do not replace the key blindly.

## Anthropic structured-output compatibility fix — 2026-11-02

Real Anthropic inference returned the precise rejection:

`invalid_request_error: output_config.format.schema: Invalid schema: Enum value None does not match declared type ['string', 'null']`

Root cause:
- the canonical Core intent schema represents nullable enum `scope` as
  `type=["string","null"]` + `enum=[null,...]`;
- Anthropic's structured-output validator rejected that specific combination.

Fix:
- keep the canonical Core schema unchanged;
- normalize only the schema sent through `AnthropicMessagesAdapter`;
- nullable enums are translated to `anyOf` with a typed enum branch plus a
  `{"type":"null"}` branch;
- ordinary nullable fields without enum remain untouched;
- normalization creates a provider-specific copy and never mutates the Core
  schema in place.

This keeps CONTRACT-04 provider-neutral while containing Anthropic-specific
schema quirks inside the adapter boundary.

## TB-04C — LiteLLM transition implementation checkpoint — 2026-11-02

Implementation started after owner approval of
`TB-04-LiteLLM-Inference-Architecture-Spec.md`.

Implemented:

- `litellm-core>=1.106.6,<2` added as the in-process provider-compatibility SDK;
- Provider Registry now exposes `transport` and `litellm_prefix` metadata;
- OpenAI → `openai/`;
- Anthropic → `anthropic/`;
- new `LiteLLMInferenceAdapter` implements the current CONTRACT-04 subset:
  - streaming text;
  - structured JSON;
  - provider-qualified model names;
  - explicit per-request credential passing;
  - normalized provider failures;
- Anthropic nullable-enum schema compatibility remains inside the single
  provider-compatibility adapter, not the Core;
- inference factory supports two explicit backends:
  - `native` — existing validated OpenAI/Anthropic adapters;
  - `litellm` — candidate LiteLLM path;
- runtime switch: `JARVIS_INFERENCE_BACKEND=native|litellm`;
- default remains `native` until owner-validated parity;
- no automatic fallback, Router, InferenceProfile or third provider has been
  enabled yet;
- focused tests added in `tests/test_litellm_inference_tb04.py`.

The current LiteLLM SDK documentation states that provider credentials can be
passed per call and model identifiers use `provider/model`. The SDK is not
thread-safe for process-global settings, therefore JARVIS does not use global
LiteLLM API-key state for connection routing.

## TB-04C owner validation — 2026-11-02

Real owner smoke passed for both OpenAI and Anthropic through the LiteLLM
backend.

The inference factory default has therefore moved from `native` to
`litellm`.

Rollback remains explicit:

```text
JARVIS_INFERENCE_BACKEND=native
```

No environment override means LiteLLM.

TB-04C is functionally accepted at provider-parity level. Full regression,
frontend production build and final Windows desktop smoke remain the gate before
advancing implementation to TB-04D InferenceProfile / InferenceResolver.

## TB-04E2 — Dynamic AI Provider Catalog implementation checkpoint — 2026-11-02

A first safe, schema-driven catalog implementation is committed on the feature branch:

- `LiteLLMProviderCatalog` reads local LiteLLM SDK provider/field metadata and merges it with the trusted JARVIS Provider Registry.
- A catalog entry does not become an executable adapter or authorized Connection merely because LiteLLM recognizes its provider ID.
- `ConnectionManager.ai_catalog()` provides read-only, non-secret descriptors.
- The QThread Connection worker loads catalog metadata without blocking the GUI thread.
- The Integrations UI now uses one generic schema-driven Connection form in place of the separate Anthropic and Gemini forms.
- The autocomplete exposes the LiteLLM catalog and marks unsupported providers as catalog-only and non-selectable.
- Existing per-Connection Windows Credential Manager boundary, verifier/diagnostic, profile bindings and explicit inference selection are unchanged.
- Added catalog-focused tests in `tests/test_ai_catalog_tb04.py`.

**Validation status:** code published; focused tests, full regression, production frontend build and Windows credential/Desktop smoke have not yet been executed in the owner's environment. Do not mark TB-04E2 or TB-04 as Product Done.

See `docs/implementation/TB-04E2-Dynamic-AI-Provider-Catalog.md` for the trust boundary and remaining acceptance gate.

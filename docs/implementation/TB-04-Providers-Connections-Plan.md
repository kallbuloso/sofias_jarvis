# JARVIS — TB-04 Providers & Connections Plan

**Slice:** TB-04 — Providers e conexões  
**Status:** APPROVED / IN PROGRESS  
**Branch:** `feat/tb-04-providers-connections`  
**Baseline:** SPEC-05, SPEC-06, CONTRACT-01, CONTRACT-07, ARCH-06 e ADR-0006 já aprovados.

## Objective

Entregar um Connection Manager utilizável no desktop para registrar adapters confiáveis, configurar conexões reais, preservar credenciais de forma protegida, verificar identidade/permissões/disponibilidade e habilitar/desabilitar/remover conexões sem conceder autoridade operacional implícita.

TB-04 não executa tools de negócio. As primeiras consultas reais via capabilities ficam no TB-05; efeitos externos permanecem no TB-06.

## Resolução de ARCH-R05 / PRD OQ-01

Os dois domínios externos reais do MVP serão:

1. **GitHub**
2. **Google Calendar**

Motivos:
- são domínios funcionalmente distintos;
- ambos têm identidade de conta real e permissões verificáveis;
- GitHub fornece um primeiro caminho simples com fine-grained PAT;
- Google Calendar exercita OAuth 2.0 Desktop, scopes e refresh/reconnect;
- ambos servem naturalmente ao TB-05 para READ;
- Calendar oferece depois um WRITE reversível e verificável para o TB-06.

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

TB-04 registra GitHub e Google Calendar. Não fará retrofit obrigatório de OpenAI, Voice ou Sofias Memory para o novo Registry; isso só ocorrerá quando trouxer valor real e sem regressão.

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

**Implementation status:** DONE in feature branch; focused tests/build/real Windows GitHub smoke PENDING.

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

## Increment 2 — Google Calendar OAuth Desktop

### Auth

OAuth 2.0 para aplicativo Desktop/installed application.

Persistência:
- client configuration não secreta conforme necessidade;
- refresh token no Windows Credential Manager;
- access token efêmero/renovável;
- granted scopes observados registrados sem segredo.

### Flow

`Create Connection → BeginExternalAuthorization → browser consent → correlated callback → token exchange → secure persist → Inspect → Enable`

### Acceptance

- retorno OAuth só conclui a conexão pendente correta;
- callback inesperado/repetido/expirado não ativa conexão;
- granted scopes são preservados como observação;
- refresh/reconnect não troca silenciosamente de identidade;
- falha de refresh não declara conexão pronta;
- conexão Calendar pode ser desabilitada/removida sem apagar eventos externos;
- segredo não aparece na UI/log/SQLite.

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

- execução de GitHub/Calendar tools na conversa — TB-05;
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

1. GitHub connection lifecycle real passar no Windows;
2. Google Calendar OAuth connection lifecycle real passar no Windows;
3. secrets permanecerem fora de SQLite/UI/log;
4. restart preservar estado não secreto;
5. disable/remove funcionarem com semântica correta;
6. serviço/credencial inválida degradar somente a conexão afetada;
7. focused tests passarem;
8. regressão completa e frontend production build passarem.

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


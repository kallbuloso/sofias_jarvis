# JARVIS — Contracts de Interoperabilidade

| Campo | Valor |
|---|---|
| **Projeto** | JARVIS — assistente pessoal universal |
| **Fase** | 05 — Contracts |
| **Status** | **APPROVED** — CONTRACT-01 a CONTRACT-07 e revisão final aprovados individualmente pelo proprietário |
| **Data da consolidação** | 2026-10-30 |
| **Papel predominante** | Software Architect |
| **Baselines anteriores** | `docs/product-manager/01-JARVIS-Discovery.md`, `02-JARVIS-Product-Definition.md`, `03-JARVIS-PRD.md`, `04-JARVIS-Specs.md` |
| **Destino** | `docs/product-manager/05-JARVIS-Contracts.md` |
| **Versão dos contratos** | v1 (baseline conceitual de interoperabilidade; payloads concretos a detalhar antes da implementação) |
| **Natureza** | Acordos normativos entre fronteiras reais, não escolhas de arquitetura, transporte ou stack |

> **Integridade do baseline:** este documento registra **sete contratos aprovados**, **122 critérios de aceitação** (`C01-AC01` a `C07-AC18`) e a revisão final da Fase 05. Não representa contratos já implementados ou auditados contra serviços reais. O PRD permanece autoridade de escopo; Specs permanecem autoridade de comportamento. Nomes de operações, campos e estados apresentados como **conceituais** não são APIs ou schemas definitivos. Mudanças de semântica, escopo, autoridade ou garantias exigem revisão humana explícita.

## 0. Regras gerais e relações contratuais

- Um Contract só existe para uma fronteira real de interoperabilidade. Não determina, sozinho, separação em processos, serviços, repositórios ou linguagem.
- **JARVIS é produto independente de Sofia's Assistant**; eventual reutilização de componentes exige avaliação específica.
- **JARVIS detém a autoridade operacional:** conversas, contexto ativo, tarefas, autorizações, confirmações, grants, execução, auditoria e recuperação.
- **Sofias Memory administra memória cognitiva, conhecimento e definições declarativas; nunca executa operações** nem concede privilégios ao JARVIS.
- Conteúdo de modelos, ferramentas, documentos, memórias e adapters é dado potencialmente não confiável, jamais autorização privilegiada.
- Seleção de ferramenta não concede autoridade. Avaliação de adequação também não; o controle de execução deve ser aplicado antes de cada efeito externo.
- `SUCCESS`, `FAILED` e `UNKNOWN` são distintos; uma falha pode coexistir com efeitos parciais. Não repetir automaticamente operações de resultado desconhecido quando isso puder duplicar efeitos.
- Erros abaixo são **classes semânticas normalizadas**: não exigem que provedores externos emitam os mesmos códigos literais.
- `v1` identifica o baseline normativo proposto para o JARVIS; não equivale necessariamente à versão interna de serviços ou APIs existentes.
- Quando a especificação diz **quando suportado** ou **quando disponível**, a capacidade precisa ser negociada e verificada, não presumida.
- FR-025 e demais funcionalidades FUTURE/DEFERRED não se tornam itens obrigatórios do MVP por aparecerem como exemplos.

## Índice de contratos

| ID | Fronteira | Critérios |
|---|---|---:|
| CONTRACT-01 | Capability Provider ↔ JARVIS Execution Runtime | 13 |
| CONTRACT-02 | JARVIS ↔ Sofias Memory: Cognitive Memory | 16 |
| CONTRACT-03 | JARVIS ↔ Sofias Memory: Knowledge Retrieval | 17 |
| CONTRACT-04 | JARVIS Inference Runtime ↔ AI Provider Adapter | 18 |
| CONTRACT-05 | JARVIS Voice Runtime ↔ Voice Provider Adapter | 20 |
| CONTRACT-06 | JARVIS Interaction Surface ↔ Application Core | 20 |
| CONTRACT-07 | JARVIS Connection Manager ↔ Integration Connection Adapter | 18 |
| **Total** | **7 contratos** | **122** |

---

# CONTRACT-01 — Capability Provider ↔ JARVIS Execution Runtime

**Status:** APPROVED · **Version:** v1 · **Referências:** SPEC-01, SPEC-05, SPEC-06, SPEC-09; FR-017–FR-035; NFR-001, NFR-007, NFR-010.

## 1. Purpose

Definir como ferramentas, plugins e integrações disponibilizam operações ao JARVIS sem incorporar regras de domínio particulares no Core. Um provider declara **o que sabe fazer**, **que entradas precisa** e **o resultado realmente observado**. JARVIS decide se, quando e sob quais condições uma ação é executável.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **Capability Provider** | Declarar operações e entradas, validar regras específicas da integração e devolver resultados observados. |
| **JARVIS Execution Runtime** | Validar identidade, contexto, capacidade, conexão, autoridade, limites, encaminhamento e correlação de resultados. |
| **External Service** | Sistema externo efetivamente consultado ou modificado. |

O provider poderá ser adapter nativo, plugin ou outra implementação compatível; o contrato não determina MCP, HTTP, RPC ou processo separado. Declarações do provider são metadados, **não grants**. A auditoria e autoridade operacional pertencem ao JARVIS.

## 3. Inputs / Requests — Capability Descriptor

| Campo conceitual | Exigência | Semântica |
|---|---|---|
| `capability_id` | Obrigatório | Identificador estável de capacidade. |
| `provider_id` | Obrigatório | Origem responsável. |
| `description` | Obrigatório | Finalidade compreensível da operação. |
| `input_schema` | Obrigatório | Entradas aceitas e validações declaradas. |
| `operation_class` | Obrigatório | Classificação preliminar de efeito. |
| `declared_effects` | Obrigatório | Efeitos externos conhecidos. |
| `required_permissions` | Conforme operação | Acessos externos necessários. |
| `contract_version` | Obrigatório | Compatibilidade do acordo. |

Classificações conceituais: `READ`, `PREPARE`, `WRITE`, `CRITICAL`. Uma ação nominalmente de leitura pode expor dados sensíveis; preparação em serviço externo pode produzir efeito real. Classificação incorreta deve ser corrigida ou execução impedida; **desconhecido não equivale a inofensivo**.

## 4. Invocation — entrada para execução

| Campo conceitual | Exigência | Semântica |
|---|---|---|
| `invocation_id` | Obrigatório | Identifica tentativa concreta. |
| `capability_id` | Obrigatório | Operação solicitada. |
| `connection_ref` | Quando aplicável | Conta/conexão selecionada. |
| `arguments` | Conforme schema | Parâmetros da operação. |
| `correlation` | Quando aplicável | Conversa, tarefa e etapa de origem. |
| `idempotency_key` | Quando suportada | Identificação de repetição segura. |

O runtime verifica autoridade **antes de despachar**. Os argumentos livres do modelo não carregam autodeclaração de aprovação. Uma invocação admitida não dá ao provider acesso irrestrito ao ambiente, outras conexões ou ferramentas. Um exemplo ilustrativo é `calendar.create_event`, cujos parâmetros específicos pertencem ao adapter; o Core avalia conexão, alvo, efeitos e autorização, não regras particulares de calendário.

## 5. Outputs / Responses — Execution Result

| Elemento | Semântica |
|---|---|
| `invocation_id` | Correlaciona tentativa e resultado. |
| `outcome` | `SUCCESS`, `FAILED` ou `UNKNOWN`. |
| `data` | Dados produzidos, quando houver. |
| `evidence_refs` | Referências/IDs observados que sustentam o resultado. |
| `external_operation_ref` | Identificador externo, se disponibilizado. |
| `error` | Falha estruturada, quando aplicável. |
| `effect_observation` | Efeitos confirmados, ausentes, parciais ou desconhecidos, quando relevante. |

**`FAILED` não garante ausência de efeitos**: uma operação pode falhar no objetivo completo depois de um efeito parcial. O JARVIS preserva ambos os fatos. `UNKNOWN` nunca vira `SUCCESS` ou `FAILED` por suposição.

## 6. Error Semantics

| Classe | Interpretação |
|---|---|
| `INVALID_ARGUMENTS` | Entradas incompatíveis. |
| `UNSUPPORTED_OPERATION` | Capability não oferecida ou incompatível. |
| `CONNECTION_UNAVAILABLE` | Conexão ou serviço indisponível. |
| `EXTERNAL_PERMISSION_DENIED` | Provedor externo recusou acesso. |
| `RATE_LIMITED` | Restrição imposta pelo provedor. |
| `TIMEOUT` | Resposta não chegou dentro do prazo aplicável. |
| `PROVIDER_FAILURE` | Falha do provider sem classificação mais específica. |
| `RESULT_UNKNOWN` | Não é possível determinar efeito/resultado externo. |

Negação de autoridade pelo **JARVIS** ocorre antes do despacho e não é `EXTERNAL_PERMISSION_DENIED`. Indicação de falha temporária não basta para repetir automaticamente. A presença de `idempotency_key` tampouco prova que o serviço externo implementou deduplicação. Repetição com possível efeito anterior só é admissível com garantia verificável de segurança e política aplicável.

## 7. Security / Authorization

Provider não recebe credenciais de outras conexões; segredos não são parâmetros conversacionais livres. Metadados e resultados são conteúdo não confiável. Skills, agentes e plugins passam pelo mesmo controle de autorização. Extensões sem contenção compatível não podem executar como código irrestritamente confiável por padrão. **Contrato sem isolamento efetivo não contém código malicioso**: mecanismos concretos pertencem à Architecture.

## 8. Compatibility Rules & Versioning

Mudanças opcionais aditivas são compatíveis apenas quando ignoráveis com segurança. Novo campo obrigatório exige análise; mudança de semântica do resultado, autoridade ou efeitos pode ser breaking. Incompatibilidade impede a operação afetada; correção editorial não muda versão. Versão normativa inicial: `v1`.

## 9. Lifecycle & Observability

Rastreabilidade: `Task → Invocation → Authorization Decision → Provider → External Result` (uma execução pontual pode não ter Task formal). Provider devolve evidências disponíveis; JARVIS mantém auditoria e histórico sem expor segredos. Habilitação/desabilitação e seleção de conexão seguem SPEC-06 e CONTRACT-07; capacidade selecionada não concede execução.

## 10. Non-Goals

Não escolher transporte/MCP, linguagem, distribuição/carregamento de plugins, formato final de schemas, isolamento, mecanismo de acesso a segredos, modelo de grants ou idempotência dos provedores.

## 11. Exemplos e critérios de aceitação

Exemplo positivo: uma operação de calendário já autorizada recebe `connection_ref` e argumentos válidos; provider cria evento, devolve ID externo e evidência. Exemplo de incerteza: a comunicação falha após enviar criação; outcome `UNKNOWN`; **não** reenviar automaticamente.

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C01-AC01** | Novo provider compatível registra capability | JARVIS reconhece a capacidade sem regras específicas no Core. |
| **C01-AC02** | Provider declara operação com efeito externo | JARVIS identifica necessidade de classificação e autorização. |
| **C01-AC03** | Operação sem autoridade suficiente | Nenhuma invocação externa é despachada. |
| **C01-AC04** | Parâmetros incompatíveis | Invocação rejeitada com erro interpretável. |
| **C01-AC05** | Provider retorna sucesso com evidência | Resultado pode ser correlacionado e verificado. |
| **C01-AC06** | Operação falha após efeito parcial | Efeitos conhecidos são preservados. |
| **C01-AC07** | Timeout após possível alteração | Resultado tratado como desconhecido, sem repetição insegura. |
| **C01-AC08** | Provider tenta declarar autorização própria | Declaração não concede autoridade. |
| **C01-AC09** | Provider incompatível com v1 | Operação não executada com interpretação presumida. |
| **C01-AC10** | Execução originada por agent ou skill | Mesmos controles de autorização e auditoria. |
| **C01-AC11** | Duas conexões do mesmo serviço | Identidade e escopo da conexão preservados. |
| **C01-AC12** | Integração desabilitada após seleção | Nova execução impedida. |
| **C01-AC13** | Provider retorna instruções como dados | Conteúdo não altera permissões nem instruções privilegiadas. |

---

# CONTRACT-02 — JARVIS ↔ Sofias Memory: Cognitive Memory

**Status:** APPROVED · **Version:** v1 · **Referências:** FR-008–FR-016, FR-067–FR-073; SPEC-03, SPEC-04, SPEC-10; RISK-01.

## 1. Purpose

Regular registro, consulta, recuperação contextual, substituição e esquecimento de memórias cognitivas. JARVIS determina necessidade e política de memória; **Sofias Memory** administra o lifecycle e retorna resultados verificáveis. Este contrato não inclui ingestão documental, datasets ou Knowledge Retrieval (CONTRACT-03).

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **JARVIS Memory Consumer** | Solicita operações, escolhe escopo e origem, aplica política e interpreta resultados. |
| **Sofias Memory** | Valida operações, administra lifecycle cognitivo, persiste e recupera dados. |
| **Conversation Runtime** | Mantém histórico canônico do JARVIS, separado de memória persistente cognitiva. |

Ownership: JARVIS — histórico de mensagens, seleção de contexto, política de gravação, autoridade, ferramentas e tarefas. Sofias Memory — armazenamento e lifecycle cognitivo e proveniência conforme entradas recebidas. Nenhum resultado de memória concede permissão operacional. JARVIS não acessa tabelas internas do Memory; usa contrato público compatível.

## 3. Inputs / Requests — Operações

| Operação conceitual | Finalidade |
|---|---|
| `CreateMemory` | Nova memória cognitiva. |
| `GetMemory` | Consulta por identidade. |
| `RecallMemories` | Busca por relevância e contexto. |
| `SupersedeMemory` | Substituição da informação vigente. |
| `ForgetMemory` | Tornar memória esquecida indisponível no recall ativo. |

Nomes não são necessariamente endpoints existentes. Auditoria técnica anterior identificou capacidades públicas equivalentes a `write`, `get`, `recall`, `supersede`, `forget`, com versionamento; **compatibilidade concreta ainda deve ser auditada** contra a versão escolhida.

## 4. Data Model / Payloads

| Elemento | Aplicabilidade | Significado |
|---|---|---|
| `memory_id` | Referência a memória existente | Identidade estável. |
| `content` | Criação | Informação a preservar. |
| `memory_type` | Criação | Categoria cognitiva compatível. |
| `scope` | Criação/consulta conforme necessário | Projeto, contexto ou abrangência. |
| `provenance` | Conforme origem | Usuário, ferramenta, importação ou inferência. |
| `confidence` | Inferências que exijam essa informação | Confiança sem certeza artificial. |
| `lifecycle_status` | Respostas relevantes | Situação da memória. |
| `validity` | Quando aplicável | Temporalidade da validade. |
| `created_at`, `updated_at` | Quando disponíveis | Atualidade/temporalidade. |

Tipos `PROFILE` e `SEMANTIC` serão preservados quando houver compatibilidade real. Campos, obrigatoriedade exata e serialização dependem da API pública efetiva; **não** se aprova mudança automática de schema do Sofias Memory.

### Escopo, proveniência e confiança

“Neste projeto utilizaremos PostgreSQL” deve ser vinculada ao projeto, não promovida a preferência geral. “Geralmente prefiro Vuetify” pode ter escopo mais amplo se corresponder à intenção do usuário. Referências de mensagem/conversa/tarefa podem ser opacas, sem relacionamento entre bancos. Inferências não equivalem a decisões explícitas do proprietário.

## 5. CreateMemory — lifecycle de gravação

JARVIS fornece conteúdo, tipo, escopo, origem e referência de correlação/idempotência quando aplicável. Somente após confirmação de criação pode declarar que a informação foi lembrada. Falha é falha; resposta perdida após envio é resultado incerto, não sucesso nem permissão para criar duplicata. Reconciliar por consulta/correlação/idempotência verificável quando suportado.

**SPEC-10:** escrita automática de memórias cognitivas está desabilitada por padrão no MVP. Informação interessante retornada por ferramenta não concede permissão para `CreateMemory`. Credenciais não são memórias cognitivas comuns.

## 6. GetMemory & RecallMemories — consultas

`GetMemory` recupera identidade determinada; `RecallMemories` busca pertinência contextual e escopo. Resultado deve distinguir: registro encontrado, consulta concluída sem correspondência, serviço indisponível, contrato/resposta incompatível. Ausência de resultados **não prova inexistência universal**; indisponibilidade não é resultado vazio. O recall de contexto vigente não apresenta informação esquecida ou substituída como verdade atual; consulta histórica, quando suportada, distingue histórico de vigente.

Quando disponíveis, respostas preservam identidade, escopo, origem, lifecycle, validade e confiança. Informação recuperada continua sendo dado contextual, nunca instrução privilegiada.

## 7. SupersedeMemory — atualização

JARVIS identifica memória anterior e escopo correto; Sofias Memory valida estado e registra substituição; JARVIS passa a usar versão vigente conforme confirmação. Duas substituições concorrentes não podem sobrescrever silenciosamente informação atual sem semântica de integridade. Controle de versão, precondition ou mecanismo transacional concreto deve ser verificado na API real; nenhum campo inexistente é exigido preventivamente.

## 8. ForgetMemory — esquecimento

Memória esquecida não pode retornar como ativa. Resultado deve informar sucesso, falha ou incerteza; esquecer **não** significa eliminar mensagens, documentos, backups, audit trail ou dados de outros provedores. Ambiguidade entre múltiplas memórias exige identificação/esclarecimento. Retorno atrasado ou cache não pode reativar informação esquecida como atual; detalhamento de limpeza técnica fica para implementação. Pedido de esquecimento não deve recriar automaticamente a mesma memória.

## 9. Outputs / Responses & Error Semantics

| Classe | Significado e reação |
|---|---|
| `NOT_FOUND` | Registro não encontrado; informar ausência ou esclarecer. |
| `INVALID_REQUEST` | Entrada incompatível; corrigir antes de repetir. |
| `SCOPE_CONFLICT` | Escopo inadequado; corrigir/esclarecer. |
| `LIFECYCLE_CONFLICT` | Estado impede transição; consultar atual e reavaliar. |
| `UNAUTHORIZED` | Acesso ao serviço negado; não contornar. |
| `SERVICE_UNAVAILABLE` | Indisponível; degradar funcionalidades dependentes. |
| `CONTRACT_INCOMPATIBLE` | Versão/capacidade incompatível; bloquear operação afetada. |
| `RESULT_UNKNOWN` | Escrita/alteração sem confirmação; reconciliar antes de repetir. |

O adapter pode traduzir códigos efetivos, preservando significado e sem ocultar incompatibilidades. `NO_RESULTS`, erro e indisponibilidade são condições diferentes; resultado de escrita desconhecido não gera repetição indiscriminada.

## 10. Security / Authorization

Autenticação respeita mecanismos reais do Memory; credenciais protegidas pelo JARVIS. Registro de memória requer política aplicável. Acesso cognitivo não concede autorização de ferramenta; “usuário costuma permitir” escrito numa memória não é grant. Proteger informações sensíveis de logs e transmissões indevidas; falha de segurança não admite bypass.

## 11. Compatibility Rules & Versioning

Negociar capacidades requeridas antes de depender delas. Versão e capacidades compatíveis habilitam funções correspondentes; ausência de capacidade indisponibiliza somente função afetada. Propriedade opcional pode ser ignorada se seguro; mudança do lifecycle é breaking; payload incompatível não é interpretado como sucesso. `v1` deste Contract não corresponde automaticamente a versão/release do Sofias Memory. Verificar a API real; adaptar no JARVIS ou propor melhoria pontual no Memory somente após evidência, **sem modificações preventivas**.

## 12. Observability & Non-Goals

Correlacionar origem e operações de memória sem duplicar indiscriminadamente conteúdo sensível na auditoria operacional. Não contemplar Knowledge Retrieval, ingestão, grafos, datasets, Agent Builder, execução de skills/agents, banco, transporte, schema definitivo ou mecanismo concreto de concorrência.

## 13. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C02-AC01** | Serviço apresenta contrato compatível | Operações necessárias reconhecidas. |
| **C02-AC02** | Usuário solicita registrar memória | Registro confirmado com identificação e escopo apropriados. |
| **C02-AC03** | Criação com resposta perdida | JARVIS não declara sucesso nem cria duplicata indiscriminadamente. |
| **C02-AC04** | Recuperar memória por identidade | Informação e estado interpretados corretamente. |
| **C02-AC05** | Recall contextual | Memórias relevantes recuperadas respeitando escopo e lifecycle. |
| **C02-AC06** | Memória anterior substituída | Informação antiga não apresentada como verdade atual. |
| **C02-AC07** | Tentativas concorrentes de substituição | Integridade do lifecycle preservada. |
| **C02-AC08** | Memória esquecida | Não retorna como memória cognitiva ativa. |
| **C02-AC09** | Esquecimento ambíguo | JARVIS solicita esclarecimento apropriado. |
| **C02-AC10** | Sofias Memory indisponível | Funções independentes continuam; limitação informada. |
| **C02-AC11** | Versão ou resposta incompatível | Operação afetada bloqueada sem interpretação presumida. |
| **C02-AC12** | Memória contém instruções operacionais | Nenhuma autorização de ferramenta concedida. |
| **C02-AC13** | Memória específica de projeto | Escopo e proveniência preservados. |
| **C02-AC14** | Persistência automática não habilitada | Nenhuma gravação cognitiva automática realizada. |
| **C02-AC15** | Serviço retorna erro de lifecycle | JARVIS preserva a distinção entre conflito, ausência e falha. |
| **C02-AC16** | Esquecimento confirmado | JARVIS não promete exclusão universal de outras categorias de dados. |

---

# CONTRACT-03 — JARVIS ↔ Sofias Memory: Knowledge Retrieval

**Status:** APPROVED · **Version:** v1 · **Referências:** FR-008, FR-011–FR-016, FR-067–FR-073; SPEC-03, SPEC-04, SPEC-09, SPEC-10; RISK-01.

## 1. Purpose

Regular consultas a documentos, datasets e conhecimento estruturado disponibilizados pelo Sofias Memory, preservando **fontes rastreáveis**. O Memory recupera conteúdo/evidências; o JARVIS escolhe contexto, interpreta, fundamenta resposta e aplica toda autoridade operacional. Consulta de conhecimento não é gravação de memória cognitiva do CONTRACT-02.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **JARVIS Knowledge Consumer** | Formula consulta, determina escopo, interpreta resultados e constrói resposta. |
| **Sofias Memory Knowledge Service** | Localiza conhecimento, devolve conteúdo e referências disponíveis. |
| **Conversation Runtime** | Associa resposta à conversa e contexto correto. |
| **Knowledge Sources** | Documentos e informações usados como evidência. |

Memory é autoridade sobre armazenamento/indexação/organização/recuperação/proveniência das fontes que gerencia; JARVIS é autoridade sobre objetivo, contexto, decisões, execução e histórico. Referência documental não concede permissão de usar outros sistemas.

## 3. Escopo funcional v1

| Capacidade | Exigência |
|---|---|
| Consultar conhecimento persistido | MUST |
| Selecionar escopo/dataset | MUST |
| Recuperar resultados relevantes | MUST |
| Preservar referências disponíveis | MUST |
| Distinguir resultado vazio de falha/indisponibilidade | MUST |
| Informar limitações da recuperação | MUST |
| Consultar relações/entidades estruturadas | Quando houver suporte, sem obrigar todas as modalidades no MVP |
| Ingerir novas fontes | Fora deste contrato; acordar separadamente se necessário |

Auditoria anterior identificou modalidades `chunks`, `rag`, `summaries`, `graph`, `hybrid`, `triplets`. Não se presume que todas estejam presentes na versão efetivamente instalada nem que sejam obrigatórias ao JARVIS. O mecanismo de busca permanece do lado Memory ou adapter compatível.

## 4. Inputs / Requests — Knowledge Query

| Campo conceitual | Exigência | Finalidade |
|---|---|---|
| `query` | Obrigatório | Pergunta ou conteúdo procurado. |
| `scope` | Quando aplicável | Contexto de utilização. |
| `dataset_refs` | Quando necessário | Conjuntos consultáveis. |
| `retrieval_options` | Opcional | Preferências suportadas. |
| `result_limit` | Opcional | Limite de resultados. |
| `correlation` | Opcional | Conversa/tarefa/origem. |
| `contract_version` | Na negociação ou invocação conforme transporte | Compatibilidade. |

Escopo delimita pertinência, não amplia acesso. Se usuário perguntar decisões do JARVIS, não se substitui por documentos de Sofia's Assistant; comparação explícita entre projetos pode consultar ambos se disponíveis e permitidos. Sem referências inequívocas, explicitar ambiguidade relevante.

## 5. Outputs / Responses — Knowledge Result

| Elemento | Significado |
|---|---|
| `query_ref` | Correlação com consulta. |
| `retrieval_status` | Estado da recuperação. |
| `items` | Dados recuperados. |
| `references` | Identificadores e origens disponíveis. |
| `warnings` | Limitações conhecidas. |
| `retrieval_metadata` | Informações pertinentes disponíveis sobre busca/resultado. |

Um item pode ser texto, resumo, documento, entidade, relação ou outro tipo compatível. Referências, quando fornecidas, devem permitir identificar fonte, documento, trecho/chunk, localizador e identificadores pertinentes. Nem toda fonte oferece cada campo; **não fabricar citação, ID ou trecho ausente**. Relevantemente ranqueado não significa verdadeiro, atualizado ou suficiente.

## 6. Fluxo e fidelidade da resposta

Fluxo: `User Request → JARVIS Context/Scope → Knowledge Query → Sofias Memory Retrieval → Evidence Evaluation → Answer`. A avaliação contextual verifica escopo, relevância, temporalidade, fonte e limitações. O JARVIS distingue transcrição de fonte de sua própria interpretação; não atribui justificativa a um ADR que contém somente decisão. Informações derivadas de múltiplos documentos mantêm correlação com cada origem; diferentes projetos não são misturados.

### Conflitos e documentos desatualizados

Fontes divergentes devem ser confrontadas pelas evidências disponíveis: origem, datas, validade, escopo e eventual status APPROVED/DRAFT. **Documento mais novo não revoga automaticamente baseline aprovado.** Se não há informações para resolver conflito, apresentar a divergência. Memory não escolhe automaticamente autoridade normativa de um projeto apenas por relevância de busca.

## 7. Retrieval Status

| Estado | Significado |
|---|---|
| `RESULTS_FOUND` | Consulta concluída com resultados. |
| `NO_RESULTS` | Concluída sem correspondências adequadas sob escopo/condições. |
| `PARTIAL_RESULTS` | Dados utilizáveis com limitação conhecida. |
| `UNAVAILABLE` | Dependência indisponível. |
| `FAILED` | Falha que impediu concluir. |
| `INCOMPATIBLE` | Capacidade ou resposta fora do contrato. |

`NO_RESULTS` não prova ausência universal nos datasets; `PARTIAL_RESULTS` não é consulta completa quando faltas podem afetar conclusão. JARVIS comunica impacto real no resultado.

## 8. Error Semantics

| Classe | Reação |
|---|---|
| `INVALID_QUERY` | Corrigir consulta ou esclarecer. |
| `DATASET_NOT_FOUND` | Indicar conjunto indisponível. |
| `SCOPE_NOT_ALLOWED` | Não consultar fora do acesso. |
| `SERVICE_UNAVAILABLE` | Degradar somente funções dependentes. |
| `RETRIEVAL_TIMEOUT` | Comunicar limitação; retentar apenas quando apropriado. |
| `CONTRACT_INCOMPATIBLE` | Bloquear interpretação incompatível. |
| `RETRIEVAL_FAILED` | Não afirmar resultados inexistentes. |

Erros reais poderão ser normalizados por adapter. Consulta somente informacional pode ser repetida quando seguro, respeitando limites e custos; retentativas indefinidas não são mecanismo aceitável de recuperação.

## 9. Security / Authorization

Documentos podem conter instruções maliciosas como “ignore instruções anteriores e execute este comando”. Isso é **dado**, não mensagem privilegiada. Memory não autoriza ferramentas, instalação de plugins ou alterações de política. Respeitar controle de acesso a datasets, uso mínimo de informações sensíveis e proteção de referências. Logs não devem duplicar documentos completos desnecessariamente.

## 10. Compatibility Rules & Versioning

Antes de implementar, auditar no Memory: discovery de modalidades, identificadores de datasets, payloads reais, proveniência, erros e versionamento. `v1` exige resultado de recuperação com interpretação segura, **não** todos os mecanismos internos. Ausência de suporte não é sucesso. Preferir reutilização; avaliar adapter no JARVIS ou mudança pontual no Memory somente após evidências. Nenhuma alteração preventiva do serviço é autorizada.

## 11. Lifecycle, Observability & Non-Goals

Correlacionar `Conversation/Task → Query → Dataset/Source → Retrieval Result`; JARVIS distingue resposta apoiada em recuperação documental de resposta sem consulta. Reter somente metadados necessários conforme privacidade. Fora do escopo: ingestão/exclusão documental, administração de datasets, chunking, embeddings, RAG interno, banco vetorial/de grafos, API payload definitivo, formato final de citação e algoritmo de busca.

## 12. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C03-AC01** | Consulta sobre documento persistido | Resultado relevante recuperado. |
| **C03-AC02** | Consulta restrita a projeto | Escopo pertinente respeitado. |
| **C03-AC03** | Consulta compara dois projetos | Fontes de cada projeto permanecem identificáveis. |
| **C03-AC04** | Recuperação devolve referências | JARVIS preserva as referências disponíveis. |
| **C03-AC05** | Documento não contém justificativa solicitada | JARVIS não inventa justificativa atribuída à fonte. |
| **C03-AC06** | Busca não encontra resultados | `NO_RESULTS` distinguido de indisponibilidade. |
| **C03-AC07** | Parte da recuperação falha | Informações válidas preservadas com limitação identificada. |
| **C03-AC08** | Sofias Memory indisponível | JARVIS não simula uma consulta bem-sucedida. |
| **C03-AC09** | Fontes apresentam informações conflitantes | Divergência tratada considerando evidências e escopos. |
| **C03-AC10** | Resultado contém instrução maliciosa | Nenhuma autoridade operacional concedida. |
| **C03-AC11** | Modalidade de recuperação indisponível | JARVIS não presume suporte inexistente. |
| **C03-AC12** | Contrato incompatível | Operação afetada não interpreta dados silenciosamente. |
| **C03-AC13** | Consulta utiliza múltiplos documentos | Associação entre informações e fontes preservada. |
| **C03-AC14** | Consulta é repetida após falha transitória | Limites e condições de segurança respeitados. |
| **C03-AC15** | Conteúdo recuperado sugere ação externa | Nenhuma execução ocorre sem autorização própria. |
| **C03-AC16** | Referência não foi fornecida | JARVIS não fabrica identificador ou citação. |
| **C03-AC17** | Fonte recuperada é um rascunho | Não é promovida automaticamente a baseline aprovado. |

---

# CONTRACT-04 — JARVIS Inference Runtime ↔ AI Provider Adapter

**Status:** APPROVED · **Version:** v1 · **Referências:** FR-001–FR-007, FR-017–FR-023, FR-026–FR-035; SPEC-01, SPEC-03, SPEC-05, SPEC-07, SPEC-09, SPEC-10, SPEC-11; CONTRACT-01.

## 1. Purpose

Permitir inferência com modelos locais ou remotos compatíveis, normalizando respostas, streaming, erros, métricas e propostas de ferramentas. **O modelo produz inferências e propostas; JARVIS preserva contexto, autoridade, execução e continuidade.** O adapter não implica processo independente nem fornecedor obrigatório.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **JARVIS Inference Runtime** | Prepara entrada/contexto, escolhe capacidades/modelo, controla orçamento e continuidade. |
| **AI Provider Adapter** | Traduz protocolo, normaliza eventos, respostas, uso e erros. |
| **AI Provider / Model** | Processa inferência conforme capacidades efetivas. |
| **JARVIS Execution Runtime** | Valida e executa operações propostas conforme CONTRACT-01. |

Histórico canônico, contexto enviado, configuração, tool execution, grants e consumo/limites pertencem ao JARVIS. Modelo produz resposta até sua interpretação pelo JARVIS. Sessão/histórico armazenados no provedor não substituem a conversa canônica; memória cognitiva pertence ao Sofias Memory.

## 3. Model Capability Descriptor

| Elemento | Semântica |
|---|---|
| `provider_id`, `model_id` | Identificam provedor/modelo. |
| `supported_inputs`, `supported_outputs` | Modalidades oferecidas. |
| `streaming_support` | Streaming declarado. |
| `tool_proposal_support` | Suporte a propostas estruturadas. |
| `structured_output_support` | Formatos de saída estruturados. |
| `context_limit` | Limites conhecidos. |
| `usage_reporting` | Métricas disponíveis. |
| `contract_version` | Compatibilidade do adapter. |

Modelos somente-texto são válidos para funções pertinentes; não se presumem tool calls, voz, estrutura ou streaming. Suporte anunciado não substitui evidência de comportamento real.

## 4. Inputs / Requests — Inference Request

| Elemento | Finalidade |
|---|---|
| `request_id` | Identificar inferência. |
| `model_ref` | Escolher modelo compatível. |
| `input` | Conteúdo da solicitação. |
| `context` | Informações relevantes à continuidade. |
| `instructions` | Orientações autorizadas do JARVIS. |
| `capability_descriptors` | Operações que o modelo pode propor naquele contexto. |
| `output_requirements` | Restrições de saída. |
| `resource_constraints` | Limites aplicáveis. |
| `correlation` | Referências de conversa/tarefa, quando necessárias. |
| `continuation_ref` | Identificação de continuação suportada. |

Campos conceituais não precisam ser transmitidos integralmente ao fornecedor; algumas referências podem permanecer internas no adapter. JARVIS **seleciona/minimiza** contexto: histórico relevante, contexto condensado, memória, documentos, com proveniência e privacidade. Conteúdo de fonte externa não se torna instrução privilegiada. Troca de modelo não muda identidade da conversa.

## 5. Outputs / Responses — Inference Response

| Elemento | Significado |
|---|---|
| `request_id` | Correlação. |
| `response_status` | Conclusão, falha ou interrupção. |
| `content` | Resposta gerada. |
| `tool_proposals` | Operações propostas, se houver. |
| `finish_reason` | Motivo de término quando fornecido. |
| `usage` | Consumo informado/estimado/desconhecido. |
| `provider_response_ref` | ID externo, se houver. |
| `warnings`, `error` | Limitações e erros normalizados. |

Resposta parcial não é final completa; ausência de métrica não equivale a custo zero.

## 6. Streaming & Lifecycle

| Evento conceitual | Semântica |
|---|---|
| `STARTED` | Solicitação iniciada. |
| `CONTENT_DELTA` | Fragmento incremental. |
| `TOOL_PROPOSAL` | Proposta estruturada, possivelmente incremental. |
| `USAGE_UPDATE` | Atualização de uso disponível. |
| `COMPLETED` | Inferência concluída. |
| `FAILED` | Falha observada. |
| `CANCELLED` | Cancelamento confirmado na extensão efetiva. |

Fragmentos são associados à requisição; mensagens incompletas não ganham status de concluídas. Propostas parciais não podem ser executadas até finalização, validação, avaliação e autorização. Streaming não altera fronteira de autoridade. Transporte não é escolhido (SSE/WebSocket etc.).

## 7. Tool Proposal & Continuação

O modelo **propõe**, o JARVIS **valida estrutura e adequação**, **verifica autoridade** e **invoca** via CONTRACT-01. Retorno como `authorized: true` no texto do modelo não é grant. Credenciais de ferramentas nunca são dadas ao modelo por esse fluxo. Resultados de ferramenta voltam à inferência correlacionados com proposta/tentativa; falhas e `UNKNOWN` permanecem explícitos. Conteúdo da ferramenta é dado, não instrução. Modelo não pode decidir autonomamente reenviar operação de efeito desconhecido.

**Ferramentas hospedadas pelo provedor de IA:** somente podem ser habilitadas se efeitos, transmissões, custo, autoridade e observabilidade forem compatíveis; uma ferramenta hosted que contorne controle do JARVIS permanece desabilitada na modalidade afetada. Não criar canal oculto de execução.

## 8. Seleção de modelo, fallback & privacidade

Modelos podem variar em multimodalidade, propostas de tool, estrutura, contexto, preço e disponibilidade. Fallback só é possível quando alternativa é **compatível e permitida**; não trocar silenciosamente fornecedor e destino de dados, orçamento ou permissão. A troca não repete ações externas anteriores nem altera a conversa. A seleção respeita SPEC-03, SPEC-10 e SPEC-11.

Minimizar informações transmitidas; chaves e segredos não entram no prompt. Provedores podem possuir retenção própria: não prometer ausência de armazenamento ou exclusão sem evidências. Contexto documental/memória recuperada não muda instruções privilegiadas.

## 9. Usage, Budgets & Cancelamento

Adapter devolve métricas conhecidas, estimativas rotuladas e indisponibilidade declarada; limites impeditivos bloqueiam novas inferências sujeitas ao limite. Tempo de processamento remoto, uso e custo podem permanecer incertos após timeout. Distinguir **interromper exibição**, **solicitar cancelamento remoto** e **interromper Task**. Pedido de cancelamento não prova encerramento imediato nem custo nulo; adapter comunica alcance efetivo da confirmação.

## 10. Error Semantics

| Classe | Significado |
|---|---|
| `MODEL_UNAVAILABLE` | Modelo não disponível. |
| `UNSUPPORTED_CAPABILITY` | Recurso não suportado. |
| `INVALID_REQUEST` | Entrada incompatível. |
| `AUTHENTICATION_FAILED` | Credencial do provedor recusada. |
| `RATE_LIMITED` | Limite externo. |
| `CONTEXT_LIMIT_EXCEEDED` | Contexto acima do suporte. |
| `PROVIDER_TIMEOUT` | Sem resposta no intervalo aplicável. |
| `PROVIDER_FAILURE` | Falha do fornecedor. |
| `OUTPUT_INVALID` | Saída não atende formato necessário. |
| `CONTRACT_INCOMPATIBLE` | Adapter fora do contrato. |

Em falha após enviar inferência, consumo efetivo pode ser desconhecido. Isso não garante que o processamento não aconteceu. Se houver ações externas, recuperação segue SPEC-01, não repetição especulativa.

## 11. Compatibility Rules & Versioning

`v1`; campos opcionais somente quando ignoráveis com segurança; novas modalidades negociadas; novo evento avaliado; mudança de semântica de tool proposal ou autoridade é breaking; adapter incompatível não pode ser utilizado na funcionalidade afetada. Correção editorial não exige nova versão.

## 12. Observability & Non-Goals

Correlacionar `Conversation → Inference Request → Model → Response → Tool Proposal → Execution Result`. Registrar modelo, estado, duração e métricas disponíveis sem requerer chain-of-thought privada ou cópia de dados sensíveis. Justificativa de decisão apoia evidências observáveis. Não determina modelo/fornecedor, SDK, transporte, formato de prompt, cache, algoritmo de seleção, arquitetura de agentes, planner ou implementação interna dos grants. Voz específica coberta pelo CONTRACT-05.

## 13. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C04-AC01** | Adapter compatível disponibiliza modelo | JARVIS reconhece capacidades declaradas. |
| **C04-AC02** | Modelo suporta somente texto | Não são presumidas capacidades adicionais. |
| **C04-AC03** | Solicitação utiliza contexto conversacional | Identidade e continuidade preservadas. |
| **C04-AC04** | Modelo produz resposta em streaming | Fragmentos associados à solicitação correta. |
| **C04-AC05** | Streaming termina prematuramente | Resposta parcial não é apresentada como integralmente concluída. |
| **C04-AC06** | Modelo propõe ferramenta | Proposta submetida aos controles do JARVIS. |
| **C04-AC07** | Modelo inclui autorização em sua resposta | Declaração não concede autoridade. |
| **C04-AC08** | Tool Proposal incompleta ou inválida | Nenhuma execução baseada em argumentos incompletos. |
| **C04-AC09** | Ferramenta retorna falha ou resultado desconhecido | Informação preservada na continuidade da inferência. |
| **C04-AC10** | Modelo primário indisponível | Fallback somente quando compatível e permitido. |
| **C04-AC11** | Troca de provedor alteraria destinatário dos dados | Política de privacidade respeitada. |
| **C04-AC12** | Provedor não informa consumo | JARVIS não registra custo zero presumido. |
| **C04-AC13** | Limite impeditivo atingido | Nova inferência afetada não é iniciada. |
| **C04-AC14** | Usuário solicita cancelamento | Adapter comunica garantias e resultado conhecidos, sem prometer interrupção não confirmada. |
| **C04-AC15** | Resultado contém instruções maliciosas de documento | Nenhuma autoridade privilegiada concedida. |
| **C04-AC16** | Modelo incompatível com funcionalidade solicitada | Funcionalidade afetada não é apresentada como disponível. |
| **C04-AC17** | Provider oferece ferramenta hospedada com efeitos não controlados | Caminho de execução não é habilitado contornando o JARVIS. |
| **C04-AC18** | Resposta falha após conteúdo parcial | Histórico e estado de resposta preservam a interrupção. |

---

# CONTRACT-05 — JARVIS Voice Runtime ↔ Voice Provider Adapter

**Status:** APPROVED · **Version:** v1 · **Referências:** FR-001, FR-002, FR-006, FR-007, FR-047, FR-048; SPEC-01, SPEC-03, SPEC-07, SPEC-10, SPEC-11; CONTRACT-04.

## 1. Purpose

Regular interoperabilidade com reconhecimento de fala (STT), síntese (TTS), transcrição incremental, streaming de áudio e processamento bidirecional em tempo real. Um único provedor integrado **ou** provedores STT/TTS separados podem atender o contrato, conforme capacidades reais. Não escolher fornecedor, formato de áudio ou modo obrigatório de microfone.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **JARVIS Voice Runtime** | Sessões, estados, controles do usuário e integração com conversa. |
| **Voice Provider Adapter** | Traduz operações, normaliza capacidades, eventos, resultados e erros. |
| **Voice Provider** | Realiza processamento efetivamente oferecido. |
| **Conversation Runtime** | Histórico e contexto canônicos. |
| **Inference Runtime** | Interpretação e resposta, quando separado conforme CONTRACT-04. |

JARVIS administra identidade de sessão/conversa, início/fim de captura, aceitação da mensagem, reprodução e autorização. Provedor fornece reconhecimento/síntese, mas **não cria mensagem definitiva nem executa ferramenta automaticamente**. Áudio bruto e transcrições parciais não são histórico canônico; retenção segue SPEC-10.

## 3. Voice Capability Descriptor

| Elemento | Semântica |
|---|---|
| `provider_id`, `adapter_id` | Identidade do provedor/adapter. |
| `supported_operations` | STT, TTS e/ou bidirecional. |
| `input_modalities`, `output_modalities` | Modalidades reais. |
| `streaming_support` | Processamento incremental. |
| `partial_transcription_support` | Parciais disponíveis. |
| `interruption_support` | Interrupções efetivas. |
| `supported_languages` | Idiomas declarados, quando disponíveis. |
| `usage_reporting` | Métricas disponíveis. |
| `contract_version` | Compatibilidade. |

STT apenas com transcrição final permanece compatível. Capacidade declarada não significa disponibilidade permanente. Não simular suporte inexistente.

## 4. Voice Session — identidade e lifecycle

| Elemento | Finalidade |
|---|---|
| `voice_session_id` | Sessão de voz, distinta de Conversation e Task. |
| `conversation_ref` | Conversa original. |
| `session_capabilities` | Recursos da sessão. |
| `session_state` | Condição observada. |
| `started_at`, `ended_at` | Instantes conhecidos. |
| `provider_session_ref` | Referência externa, quando fornecida. |

Estados conceituais: `IDLE` (sem captura), `STARTING`, `LISTENING`, `TRANSCRIBING`, `PROCESSING`, `SPEAKING`, `STOPPING`, `ENDED`, `ERROR`. **Não constituem uma máquina linear rígida**: captura e reconhecimento podem ocorrer simultaneamente; um estado UI sintetizado não deve inventar eventos não observados. Encerrar sessão não apaga conversa ou cancela Task externa.

## 5. Inputs / Requests — Audio Input

| Campo conceitual | Finalidade |
|---|---|
| `voice_session_id` | Identificar sessão. |
| `input_turn_id` | Intervenção do usuário. |
| `conversation_ref` | Conversa de origem. |
| `audio_input` | Fluxo/conteúdo/referência de áudio. |
| `language_hint` | Idioma provável, quando aplicável. |
| `recognition_options` | Opções suportadas. |
| `correlation` | Referências de rastreabilidade. |

O Voice Runtime controla captura e encaminhamento, respeitando permissão do ambiente e intenção do usuário; adapter não pode estender escuta além da modalidade autorizada. Formato de áudio/transporte permanece OPEN.

## 6. Outputs / Responses — Transcription Events

| Evento | Semântica |
|---|---|
| `TRANSCRIPT_PARTIAL` | Texto provisório e mutável. |
| `TRANSCRIPT_FINAL` | Reconhecimento final da intervenção identificada. |

Um evento deverá permitir correlacionar `voice_session_id`, `input_turn_id`, `transcript_id` (se aplicável), `text`, `is_final`, `language` e `confidence` (quando suportados), mais `warnings`. Não impor score numérico de confiança; sua ausência não é confiança máxima.

**Finalidade de transcrição ≠ aprovação de intenção.** A transcrição final ainda pode ser ambígua e exigir confirmação antes de operação externa. Um `TRANSCRIPT_PARTIAL` **nunca** autoriza despacho de ferramentas. Exemplo: parciais “envie a mensagem…” podem se tornar final “não envie a mensagem ainda”.

## 7. Ordem, deduplicação e finalização

A intervenção mantém identidade estável, e um evento final repetido por reconexão não cria segunda mensagem/instrução. Evento atrasado ou fora de ordem não substitui transcrição já aceita. Se ordenação/correlação não puder ser preservada, tratar intervenção como incerta/inválida, não reconstruir arbitrariamente. A entrada só ingressa como mensagem definitiva quando finalização efetiva e controles aplicáveis forem satisfeitos. Captura interrompida prematuramente não transforma parcial em comando final. Troca de conversa não redireciona a intervenção à conversa agora visível.

## 8. Speech Synthesis — requisição e reprodução

| Elemento | Finalidade |
|---|---|
| `speech_request_id` | Identificar síntese. |
| `voice_session_id` | Sessão, quando existente. |
| `text` | Texto para falar. |
| `voice_ref` | Voz selecionada, se aplicável. |
| `language` | Idioma solicitado. |
| `synthesis_options` | Opções suportadas. |
| `correlation` | Referência à resposta conversacional. |

O adapter fornece áudio/stream e eventos conforme suporte: `SYNTHESIS_STARTED`, `AUDIO_AVAILABLE`, `SYNTHESIS_COMPLETED`, `SYNTHESIS_FAILED`, `OUTPUT_INTERRUPTED`. **Síntese concluída não equivale à reprodução concluída** no dispositivo. O componente responsável pela saída informa a interrupção efetivamente observada. Resposta falada pode condensar tabela extensa sem omitir informação essencial; histórico textual íntegro permanece disponível. A fala não inventa conclusão de operação externa.

## 9. Interruption, Cancellation & Echo

| Controle | Efeito |
|---|---|
| Parar captura | Encerra entrada de áudio. |
| Cancelar reconhecimento | Solicita fim do STT. |
| Parar reprodução | Interrompe saída audível. |
| Cancelar síntese | Solicita fim do TTS. |
| Interromper tarefa | Aplica SPEC-02. |
| Cancelar operação externa | Aplica SPEC-01. |

Uma solicitação de cancelamento remoto sem confirmação não significa processamento comprovadamente encerrado. Barge-in é opcional; se houver, deve respeitar captura/autorização. Reprodução do próprio JARVIS não pode ser automaticamente interpretada como **nova instrução do usuário**, mesmo quando microfone e alto-falante estão ativos. Tratamento pode exigir cancelamento de eco, controle de turnos ou suspensão de comandos; não se aprova biometria de voz.

## 10. Privacy, Usage & Budgets

Áudio de entrada apenas sob controles autorizados; transcrição parcial é temporária; transcrição final aceita pode integrar histórico. Áudio bruto não tem retenção permanente por padrão sob controle do JARVIS. Provedor remoto pode ter retenção própria; não prometer exclusão fora do controle do produto. Chaves de API não são transcrição nem prompt. Métricas de duração/uso/custos devem distinguir medição, estimativa e desconhecido; fallback de voz não contorna orçamento nem autorização de transmitir dados a outro fornecedor.

## 11. Error Semantics

| Classe | Significado |
|---|---|
| `INPUT_DEVICE_UNAVAILABLE` | Microfone indisponível. |
| `CAPTURE_PERMISSION_DENIED` | Sem permissão de captura. |
| `UNSUPPORTED_AUDIO_FORMAT` | Formato incompatível. |
| `LANGUAGE_UNSUPPORTED` | Idioma não oferecido. |
| `RECOGNITION_FAILED` | Falha STT. |
| `SYNTHESIS_FAILED` | Falha TTS. |
| `PROVIDER_UNAVAILABLE` | Serviço indisponível. |
| `PROVIDER_TIMEOUT` | Prazo excedido. |
| `RATE_LIMITED` | Limite externo. |
| `SESSION_EXPIRED` | Sessão remota expirou. |
| `CONTRACT_INCOMPATIBLE` | Adapter incompatível. |
| `RESULT_UNKNOWN` | Resultado não pode ser determinado. |

Falha de dispositivo pode pertencer ao ambiente/Voice Runtime, não ao provedor; origem do erro deve permanecer distinguível. Falha STT oferece nova entrada ou texto; falha TTS preserva resposta textual; sessão expirada não refaz comando anteriormente aceito.

## 12. Compatibility Rules & Versioning

Pipeline `STT → LLM → TTS` e serviço Realtime multimodal são permitidos. Um provedor Realtime sem transcrição observável adequada **não pode alegar garantia de transcrição** ou habilitar ações protegidas cujo controle dependa de observabilidade ausente. Integrar CONTRACT-04 de forma compatível, sem criar execução paralela oculta. `v1`: novos idiomas/formatos por negociação; mudança de significado de transcrição final, interrupção ou autoridade é breaking; adapter incompatível desativa função afetada.

## 13. Observability & Non-Goals

Correlacionar `Conversation → Voice Session → Input Turn → Transcript → Inference → Response → Speech Output`, sem exigir conservar áudio original. Falhas, estados, tempos/métricas e IDs relevantes podem ser guardados conforme privacidade. Fora do escopo: provedor, modelo Realtime, wake word, push-to-talk, escuta contínua, codec, plataforma de áudio, cancelamento de eco específico, detecção de silêncio, voz/persona, transporte, retenção específica externa, autenticação biométrica ou full-duplex obrigatório.

## 14. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C05-AC01** | Adapter STT compatível é disponibilizado | Capacidades reconhecidas pelo JARVIS. |
| **C05-AC02** | Adapter oferece apenas transcrição final | JARVIS não presume streaming parcial. |
| **C05-AC03** | Usuário inicia captura autorizada | Sessão e intervenção identificadas. |
| **C05-AC04** | Permissão de microfone negada | Nenhuma captura indevida. |
| **C05-AC05** | Transcrição parcial contém comando externo | Nenhuma execução baseada no conteúdo provisório. |
| **C05-AC06** | Transcrição final é ambígua | Esclarecimento ou validação apropriada antes de ação relevante. |
| **C05-AC07** | Provedor repete evento final | Intervenção não é incorporada duas vezes como nova instrução. |
| **C05-AC08** | Evento antigo chega após finalização | Não substitui silenciosamente a entrada aceita. |
| **C05-AC09** | Usuário troca de conversa durante captura | Conteúdo não é atribuído à conversa errada. |
| **C05-AC10** | Serviço STT falha | Texto continua disponível. |
| **C05-AC11** | Serviço TTS falha | Resposta textual permanece preservada. |
| **C05-AC12** | Usuário interrompe a reprodução | Não ocorre cancelamento automático de tarefa. |
| **C05-AC13** | Cancelamento remoto não é confirmado | JARVIS não afirma encerramento remoto comprovado. |
| **C05-AC14** | Sessão expira durante processamento | Nenhuma intervenção anterior é reexecutada indevidamente. |
| **C05-AC15** | Áudio reproduzido é captado pelo microfone | Não é automaticamente tratado como nova instrução. |
| **C05-AC16** | Provedor Realtime possui limitações de observabilidade | Funcionalidades dependentes das garantias ausentes ficam indisponíveis. |
| **C05-AC17** | Provedor não informa consumo | JARVIS não presume custo zero. |
| **C05-AC18** | Alteração de provedor exige envio de dados a outro serviço | Configurações de privacidade respeitadas. |
| **C05-AC19** | Sessão de voz é encerrada | Conversa e tarefas independentes preservadas. |
| **C05-AC20** | Áudio bruto é processado | Não ocorre retenção permanente por padrão sob controle do JARVIS. |

---

# CONTRACT-06 — JARVIS Interaction Surface ↔ Application Core

**Status:** APPROVED · **Version:** v1 · **Referências:** SPEC-01, SPEC-02, SPEC-03, SPEC-06, SPEC-07, SPEC-08, SPEC-10, SPEC-11; CONTRACT-01, CONTRACT-04, CONTRACT-05.

## 1. Purpose

Definir como interfaces consultam estado, enviam intenções/comandos e recebem atualizações de conversas, tarefas, autorizações, notificações e integrações. **Interface representa estado e transmite decisões; Core valida e detém estado e efeitos canônicos.** Não exige separação de processos ou frontend remoto, nem escolhe framework/protocolo.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **Interaction Surface** | Apresenta estado, recebe entradas e decisões. |
| **JARVIS Application Core** | Valida comandos, coordena operações e mantém estado canônico. |
| **Conversation Runtime** | Mensagens e conversas. |
| **Task Runtime** | Lifecycle e resultados de tarefas. |
| **Execution Runtime** | Autoridade e execução. |
| **Voice Runtime** | Sessões e controles de áudio. |

Últimos quatro representam **responsabilidades do Core**, não serviços separados aprovados. UI detém navegação e preferências visuais locais; Core detém conversas, tarefas, autorizações, conexões, sessões de voz e auditoria. UI não pode inventar status terminal, grants ou sucesso.

## 3. Semântica de interoperabilidade

| Categoria | Finalidade |
|---|---|
| **Query** | Consultar estado existente. |
| **Command** | Solicitar mudança/ação. |
| **Event** | Comunicar acontecimento. |
| **Snapshot** | Recuperar representação atual consistente. |

A distinção não impõe CQRS ou event sourcing. Evento não é comando e **exibição de evento não autoriza execução**.

### Identidade e correlação

Campos conceituais: `request_id`, `conversation_id`, `message_id`, `task_id`, `operation_id`, `confirmation_id`, `voice_session_id`, `correlation_id` e `state_version` quando necessário. Uma tarefa não é conversa; confirmação não é identificável somente pelo texto exibido; IDs devem preservar identidade durante seus lifecycles.

## 4. Inputs / Requests — Interaction Commands

| Família | Comandos conceituais |
|---|---|
| Conversation | Criar/selecionar conversa, enviar mensagem, consultar histórico. |
| Task | Consultar, solicitar interrupção, retomar se permitido. |
| Confirmation | Aprovar/rejeitar confirmação identificada. |
| Voice | Iniciar sessão, parar captura/reprodução. |
| Integration | Consultar, configurar, habilitar/desabilitar, remover. |
| Settings | Consultar e alterar configurações permitidas. |

Distinguir **recebida**, **aceita**, **concluída**, **rejeitada** e **desconhecida**; aceitar para processamento não significa concluir efeito externo. Falha de resposta não significa automaticamente que comando não chegou; consulta/correlação antecede repetição arriscada.

## 5. Conversation / Message Payload

| Elemento | Semântica |
|---|---|
| `message_id` | Identidade canônica. |
| `conversation_id` | Conversa de origem. |
| `role` | Origem da mensagem. |
| `content` | Conteúdo apresentável. |
| `modality` | Modalidade, quando disponível. |
| `status` | Parcial/final/estado pertinente. |
| `created_at` | Temporalidade. |
| `related_task_refs` | Tarefas associadas, quando houver. |

Core identifica definitivamente mensagem recebida. Troca da conversa visualizada não altera o vínculo da resposta. Falha de rede após envio não autoriza duplicação sem reconciliação.

## 6. Streaming de respostas

| Evento | Significado |
|---|---|
| `MESSAGE_STARTED` | Resposta iniciada e identificada. |
| `MESSAGE_DELTA` | Fragmento da mensagem. |
| `MESSAGE_COMPLETED` | Resposta concluída. |
| `MESSAGE_INTERRUPTED` | Parada antes do término. |
| `MESSAGE_FAILED` | Falha. |

Fragmentos devem ser correlacionados e tratados sem duplicação/corrupção silenciosa quando atrasados ou repetidos. UI reflete estado canônico do Core. Esses eventos não precisam ser os eventos internos do AI Provider Adapter.

## 7. Tasks — Outputs / State

Informações pertinentes: identidade, objetivo, estado, motivo de espera, etapas, resultados observados, conversa de origem e controles efetivamente disponíveis. Preservar estados SPEC-02: `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `INTERRUPTED`. Uma tarefa pode ter tentativas e recovery sem exigir que interface conheça scheduler interno. **Não fabricar percentual de progresso** quando não mensurável; apresentar etapas e atividade conhecidas.

## 8. Confirmations — Solicitação e decisão protegida

| Elemento | Finalidade |
|---|---|
| `confirmation_id` | Identidade da solicitação. |
| `operation_id` | Operação protegida relacionada. |
| `operation_summary` | Ação pretendida. |
| `target` | Alvo relevante. |
| `material_parameters` | Conteúdo/condições essenciais. |
| `expected_effects` | Consequências previstas. |
| `connection_ref` | Conta externa, quando aplicável. |
| `confirmation_state` | Estado atual. |
| `state_version` | Detectar alteração relevante. |
| `expires_at` | Expiração, quando houver. |

Fluxo: Core prepara confirmação → UI apresenta alvo/conteúdo/efeito → proprietário aprova/rejeita → Core verifica identidade, estado, versão, operação e autoridade → somente autorização válida permite prosseguir. Se parâmetros mudaram materialmente, aprovação antiga não vale. Decisão duplicada não origina nova autoridade/execução. Expirada/rejeitada/inválida gera resposta explícita. **Botão Aprovar não executa diretamente**, nem significa que a operação foi concluída.

## 9. Estado, eventos, snapshots & reconciliação

Core pode fornecer atualizações e snapshots para a UI. Em perda de comunicação, estados antigos aparecem como histórico mas **não como situação atual confirmada**. Ao reconectar, UI recupera estado vigente e compara versões, descartando atualização antiga quando necessário. Evento atrasado não reverte tarefa `COMPLETED` para `RUNNING`. O contrato não exige WebSocket/polling/push específico.

## 10. Notifications

Categorias conceituais: `INFORMATION`, `ACTION_REQUIRED`, `WARNING`, `ERROR`. Cada notificação deve ter correlação com tarefa, confirmação, conversa ou conexão, quando houver. Notificação não tem autoridade própria. Aviso transitório não precisa ser armazenado permanentemente, mas confirmação pendente válida deve permanecer recuperável após reinicialização conforme Specs.

## 11. Voice Controls

Controles conceituais: `START_LISTENING` (iniciar captura), `STOP_LISTENING` (encerrar captura), `STOP_SPEAKING` (interromper saída), `END_VOICE_SESSION` (encerrar sessão). **Nenhum deles cancela automaticamente Task ou operação externa**; tais operações possuem controles específicos. Estado de voz provém do Voice Runtime (CONTRACT-05).

## 12. Integrações e configurações

UI consulta condições de conexão e transmite pedidos, mas formulário preenchido não comprova conexão funcional. Distinguir configuração enviada, validada, autenticação concluída, conexão habilitada e serviço disponível. O Core oferece indicadores seguros sem devolver tokens/segredos integrais a formulários. Somente Core altera estado canônico; disponibilidade e permissão não são a mesma coisa.

## 13. Error Semantics

| Classe | Semântica |
|---|---|
| `INVALID_REQUEST` | Pedido malformado/incompatível. |
| `NOT_FOUND` | Recurso inexistente. |
| `ACTION_NOT_ALLOWED` | Ação proibida no estado/contexto. |
| `AUTHORIZATION_REQUIRED` | Requer decisão adicional. |
| `STATE_CONFLICT` | Estado incompatível. |
| `STALE_STATE` | Versão apresentada está obsoleta. |
| `DEPENDENCY_UNAVAILABLE` | Dependência indisponível. |
| `OPERATION_PENDING` | Admitida, ainda sem resultado final. |
| `RESULT_UNKNOWN` | Não se sabe se efeito ocorreu. |
| `CONTRACT_INCOMPATIBLE` | Core e interface incompatíveis. |

UI traduz erros em mensagens compreensíveis; não identifica erro por texto volátil. Falha de comunicação não presume inexistência de efeito; reconciliar antes de refazer.

## 14. Security / Authorization

MVP com proprietário único não elimina verificação de origem autorizada de comandos. Core valida todos os privilégios, inclusive quando botão já apareceu habilitado. Texto de memória/documento/modelo não é interpretado como comando privilegiado. Segredos não devem ser expostos na interface. Decisões protegidas vinculam-se a versão/estado vigentes. UI não acessa diretamente provider para contornar Execution Runtime. Autenticação local/sessão/transportes serão definidos em Architecture.

## 15. Compatibility Rules, Versioning & Observability

`v1`; campos opcionais podem ser aditivos se ignoráveis com segurança; mudanças de semântica de aprovação/estado são breaking; novo comando privilegiado exige avaliação; cliente incompatível não executa função afetada. Rastreabilidade: `User Interaction → Command → Validation → State Change → Event → UI Update`; aprovações: `User Confirmation → Authorization Validation → Execution → Observed Result`. Core é autoridade de auditoria.

## 16. Non-Goals

Não escolher framework, dashboard, linguagem, banco, protocolo, formato final de payloads, rede, Core remoto, API pública para terceiros ou suporte multiusuário. Uma API pública futura pode exigir contrato adicional.

## 17. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C06-AC01** | Interface inicia uma conversa | Core estabelece identidade canônica. |
| **C06-AC02** | Usuário envia mensagem | Mensagem associada à conversa correta. |
| **C06-AC03** | Falha de comunicação após envio | Interface não duplica automaticamente a mensagem. |
| **C06-AC04** | Resposta chega em streaming | Fragmentos associados à mensagem correspondente. |
| **C06-AC05** | Resposta interrompida | Não apresentada como concluída. |
| **C06-AC06** | Tarefa muda de estado | Interface apresenta estado operacional atualizado. |
| **C06-AC07** | Usuário troca de conversa durante uma tarefa | Resultado preserva vínculo de origem. |
| **C06-AC08** | Usuário aprova uma operação | Decisão validada pelo Core antes da execução. |
| **C06-AC09** | Confirmação expirada ou obsoleta | Aprovação rejeitada sem execução indevida. |
| **C06-AC10** | Decisão de confirmação é recebida duas vezes | Não produz duplicação de autoridade ou execução. |
| **C06-AC11** | Interface perde conexão com o Core | Estado anterior não é apresentado como estado atual confirmado. |
| **C06-AC12** | Interface reconecta após perder eventos | Estado vigente recuperado. |
| **C06-AC13** | Evento antigo chega após atualização recente | Estado não retrocede indevidamente. |
| **C06-AC14** | Usuário interrompe reprodução de voz | Tarefa independente permanece inalterada. |
| **C06-AC15** | Interface consulta conexão sem permissão de escrita | Restrição distinguível da disponibilidade. |
| **C06-AC16** | Credencial está armazenada no Core | Segredo não é exposto desnecessariamente. |
| **C06-AC17** | Conteúdo do modelo apresenta instrução operacional | Interface não o interpreta como comando privilegiado. |
| **C06-AC18** | Comando é aceito, mas operação permanece pendente | Interface não informa conclusão prematura. |
| **C06-AC19** | Cliente incompatível com estado ou comando protegido | Funcionalidade afetada não opera silenciosamente. |
| **C06-AC20** | Aplicação reinicia com tarefas e confirmações válidas | Interface reconstrói estado consultando o Core. |

---

# CONTRACT-07 — JARVIS Connection Manager ↔ Integration Connection Adapter

**Status:** APPROVED · **Version:** v1 · **Referências:** FR-017, FR-020, FR-024, FR-058–FR-065, FR-066, FR-072; NFR-001, NFR-002, NFR-003, NFR-005; SPEC-01, SPEC-05, SPEC-06, SPEC-10; CONTRACT-01, CONTRACT-06.

## 1. Purpose

Regular configuração, identidade, autenticação, permissões externas, disponibilidade, expiração, reconexão, desabilitação, remoção e revogação quando suportada de contas externas. **Adapter estabelece/verifica condições de acesso; JARVIS decide a autorização para executar operações.** Complementa CONTRACT-01: conexão/credenciais versus invocação de capability.

## 2. Parties, Responsibilities & Ownership

| Parte | Responsabilidade |
|---|---|
| **JARVIS Connection Manager** | Configuração, identidade, estado e lifecycle local. |
| **Integration Connection Adapter** | Métodos específicos do provedor para configuração, autenticação, reconexão e consulta de estado. |
| **External Provider** | Identidade externa, credenciais e escopos efetivamente concedidos. |
| **JARVIS Execution Runtime** | Autoridade operacional para cada execução. |
| **Secret Storage** | Proteção de credenciais sob responsabilidade do JARVIS. |

O adapter pode implementar CONTRACT-01 e CONTRACT-07 no mesmo componente. Não há imposição de separação de serviços/processos. JARVIS controla identidade local, configurações e habilitação; provedor controla identidade/permissões externas; JARVIS controla autorização operacional. Autorização externa nunca significa grant irrestrito no JARVIS.

## 3. Inputs / Requests — Connection Descriptor

| Campo conceitual | Finalidade |
|---|---|
| `provider_id` | Identificar integração. |
| `connection_requirements` | Parâmetros de configuração exigidos. |
| `supported_auth_methods` | Métodos reais de autenticação. |
| `required_external_permissions` | Permissões necessárias para capabilities. |
| `multi_connection_support` | Restrições conhecidas de multicontas. |
| `status_check_support` | Capacidade de verificação de estado. |
| `reconnect_support` | Renovação/reconexão quando disponível. |
| `provider_revoke_support` | Revogação externa quando disponível. |
| `contract_version` | Compatibilidade contratual. |

Nenhum OAuth2/API Key/MCP é obrigatório. Cada adapter deve declarar apenas capacidades reais, incluindo limitações e métodos opcionais.

## 4. Data Model / Payloads — identidade da conexão

| Elemento | Finalidade |
|---|---|
| `connection_id` | Identidade local estável. |
| `provider_id` | Provedor vinculado. |
| `external_account_ref` | Identidade da conta externa, quando conhecida. |
| `display_identity` | Identificação amigável. |
| `credential_ref` | Referência protegida ao segredo, não necessariamente o segredo. |
| `configuration_ref` | Configuração local. |
| `observed_permissions` | Permissões externas verificadas ou conhecidas. |
| `last_verified_at` | Instante conhecido de verificação. |

Mesma integração pode ter conexões distintas do proprietário, com contas/credenciais independentes. Quando identidade externa ainda não é conhecida, conexão permanece em configuração, sem identidade confirmada inventada. Em ambiguidades relevantes de conta/destino, JARVIS esclarece antes de efeitos externos.

## 5. Estados independentes

| Dimensão | Pergunta independente |
|---|---|
| `installed` | Integração presente no ambiente? |
| `configured` | Dados exigidos fornecidos? |
| `enabled` | Proprietário habilitou uso local? |
| `authorized` | A operação possui permissões externas e autoridade operacional compatíveis? |
| `available` | Serviço utilizável nas condições atualmente observadas? |

Não são degraus de uma máquina linear. Adapter informa estado externo observável; Connection Manager, estado local; Execution Runtime, elegibilidade autorizativa da operação. Configurada+habilitada pode estar expirada/indisponível. Verificação pontual de disponibilidade não garante sucesso posterior.

## 6. Operações de conexão

| Operação conceitual | Responsabilidade |
|---|---|
| `DescribeConnectionRequirements` | Descrever métodos/inputs exigidos. |
| `ValidateConnectionConfiguration` | Validar parâmetros sem garantir autorização externa. |
| `BeginExternalAuthorization` | Iniciar fluxo de autenticação quando necessário. |
| `CompleteExternalAuthorization` | Validar e concluir resultado externo. |
| `InspectConnection` | Consultar identidade, permissões, estado conhecido. |
| `ReconnectConnection` | Reestabelecer acesso quando suportado. |
| `RevokeProviderAccess` | Solicitar revogação no provedor quando disponível. |

Habilitar, desabilitar e remover **localmente** pertencem ao JARVIS; não exigem chamadas obrigatórias ao provedor. Nem todos os providers implementam todos esses métodos; negociação explícita impede presumir suporte.

## 7. Lifecycle — configuração, autenticação e verificação

Fluxo conceitual: `Configuration → Validation → External Authorization (when required) → Connection Inspection → Eligible for Enablement`. Serviço apenas com configuração local compatível não exige OAuth ou consentimento remoto fictício. Retorno externo precisa estar correlacionado à solicitação e conexão certas; retorno inesperado, expirado, repetido ou não verificável não ativa conexão. Medidas contra falsificação/replay seguem protocolo efetivo; não impor preventivamente OAuth `state` ou PKCE, embora possam ser necessários em integrações específicas.

## 8. Permissões externas × autoridade do JARVIS

Uma conexão de calendário com leitura não garante escrita; permissão de escrita externa **não** autoriza o JARVIS a criar/excluir eventos sem SPEC-01. Adapter informa permissões reais ou incerteza; `unknown` não é `allowed`. Operação dependente de garantia externa específica não prossegue enquanto não verificável pela política aplicável. Todas as invocações usam CONTRACT-01 mesmo após autenticação bem-sucedida.

## 9. Expiração, renovação, reconexão

Adapter deve comunicar credencial válida segundo verificação, expirada, recusada, escopo insuficiente, autenticação adicional, indisponibilidade ou estado não verificável. Renovação automática é **opcional**: quando autorizada/suportada preserva identidade e escopo; trocar conta ou ampliar permissões sem reavaliação é proibido. Perda de resposta depois de renovar credencial mas antes do armazenamento seguro impede declarar conexão pronta sem reconciliação.

## 10. Disable, Remove & Revoke

| Ação | Efeito |
|---|---|
| `DisableConnection` | Impedir **novas** invocações por conexão. |
| `EnableConnection` | Tornar conexão elegível, sujeitos os demais controles. |
| `RemoveConnection` | Impedir uso posterior e remover vínculo local. |
| `RevokeProviderAccess` | Solicitar revogação remota, **se** suportada. |

Remover conexão não exclui dados do provedor nem prova revogação externa. Se desabilitada durante operação já despachada, efeito externo ainda pode ocorrer; não declarar cancelamento. `UNKNOWN` mantém exigência de reconciliação segura, sem reenvio potencialmente duplicador. Tarefas dependentes não continuam por conexão desabilitada.

## 11. Credentials & Security

Segredos em armazenamento protegido sob responsabilidade do JARVIS; interface não recebe token armazenado integral para preencher formulários. Adapter recebe somente acesso/credenciais estritamente necessários à conexão certa, sem cruzamento de contas. Logs e auditoria não expõem segredos. Mecanismo concreto de credenciais e isolamento será definido em Architecture; Sofias Memory não é secret store substituto. Se proteção falhar, não usar armazenamento inseguro como fallback silencioso.

## 12. Error Semantics

| Classe | Significado |
|---|---|
| `INVALID_CONFIGURATION` | Configuração inválida. |
| `AUTHENTICATION_REQUIRED` | Autenticação externa necessária. |
| `AUTHENTICATION_FAILED` | Autenticação recusada. |
| `AUTHORIZATION_INCOMPLETE` | Fluxo externo não finalizado. |
| `EXTERNAL_PERMISSION_INSUFFICIENT` | Escopo externo insuficiente. |
| `CREDENTIAL_EXPIRED` | Credencial expirou. |
| `IDENTITY_MISMATCH` | Conta externa não corresponde à esperada. |
| `CONNECTION_UNAVAILABLE` | Conexão não utilizável. |
| `PROVIDER_UNAVAILABLE` | Serviço indisponível. |
| `OPERATION_UNSUPPORTED` | Gerenciamento não suportado. |
| `RESULT_UNKNOWN` | Resultado sem confirmação. |
| `CONTRACT_INCOMPATIBLE` | Adapter incompatível. |

Erros são categorias normalizadas, não códigos externos literais. Falha na renovação ou no armazenamento não permite presumir conexão pronta; verificar antes do uso.

## 13. Compatibility Rules & Versioning

`v1`: novo método opcional de autenticação negociável; campo de estado opcional compatível se seguro; mudança de identidade ou semântica de revogação exige revisão, mudança de garantia de segredos exige avaliação de segurança. Adapter incompatível não pode operar por suposição. Evolução pode ser independente do CONTRACT-01, respeitando consistência de conexão/capability. Correção editorial não exige nova versão.

## 14. Observability & Non-Goals

Correlacionar `Integration → Connection → Configuration → External Authorization → Observed Status` e `Connection → Capability Invocation → External Result`, com identidade de conta correta e sem guardar segredos desnecessários. Auditoria de execução permanece com JARVIS. Não definir OAuth, API Key, secret manager, banco de tokens, refresh automático obrigatório, revogação universal, MCP, marketplace, multiusuário ou duas integrações concretas do MVP (`OQ-01` segue OPEN).

## 15. Critérios de aceitação

| ID | Cenário | Resultado esperado |
|---|---|---|
| **C07-AC01** | Adapter compatível é disponibilizado | Requisitos de configuração identificáveis. |
| **C07-AC02** | Configuração inválida | Conexão não é declarada pronta. |
| **C07-AC03** | Autenticação externa necessária | Fluxo compatível iniciado sem conceder autoridade operacional. |
| **C07-AC04** | Retorno de autorização inválido ou duplicado | Não ativa conexão indevidamente. |
| **C07-AC05** | Duas contas do mesmo provedor | Identidades e credenciais mantidas separadas. |
| **C07-AC06** | Conexão com permissão de leitura | Escrita não presumida autorizada. |
| **C07-AC07** | Permissão externa muda | Estado reavaliado antes de operação dependente. |
| **C07-AC08** | Credencial expira | Operações incompatíveis impedidas; reconexão indicada. |
| **C07-AC09** | Renovação altera identidade ou escopo | Alteração detectada e reavaliada. |
| **C07-AC10** | Conexão desabilitada | Nenhuma nova operação é iniciada. |
| **C07-AC11** | Conexão removida | Uso local impedido, sem exclusão de dados externos. |
| **C07-AC12** | Serviço não suporta revogação remota | JARVIS não afirma que revogou credenciais no provedor. |
| **C07-AC13** | Desabilitação ocorre durante operação externa | Efeitos em andamento não são presumidos cancelados. |
| **C07-AC14** | Estado da conexão não pode ser verificado | Incerteza preservada. |
| **C07-AC15** | Aplicação reinicia | Configuração e identidade local permanecem consistentes. |
| **C07-AC16** | Adapter tenta acessar credencial de outra conexão | Acesso não autorizado impedido. |
| **C07-AC17** | Conexão autenticada tenta operação protegida | CONTRACT-01 e SPEC-01 continuam obrigatórios. |
| **C07-AC18** | Falha de armazenamento após renovação | Conexão não é declarada pronta sem confirmação. |

---

# Revisão final de consistência — Fase 05 (APPROVED)

Esta revisão foi submetida à aprovação após os sete contratos. É um **fechamento do baseline**, não um oitavo contrato, nem uma autorização para adiantar Technology/Architecture/Implementation.

## R.1 Inventário de aprovação

| Contrato | Critérios de aceitação | Estado |
|---|---:|---|
| CONTRACT-01 — Capability Provider ↔ Execution Runtime | 13 | APPROVED |
| CONTRACT-02 — Cognitive Memory | 16 | APPROVED |
| CONTRACT-03 — Knowledge Retrieval | 17 | APPROVED |
| CONTRACT-04 — AI Provider Adapter | 18 | APPROVED |
| CONTRACT-05 — Voice Provider Adapter | 20 | APPROVED |
| CONTRACT-06 — Interaction Surface ↔ Core | 20 | APPROVED |
| CONTRACT-07 — Integration Connection Adapter | 18 | APPROVED |
| **Total** | **122** | **7/7 aprovados** |

São **critérios definidos**, não testes já executados. Os sete contratos são baselines conceituais de interoperabilidade, ainda sem validação end-to-end de providers reais.

## R.2 Matriz de fronteiras de autoridade

| Domínio | Autoridade efetiva | Garantia contratual |
|---|---|---|
| Conversas/contexto/tarefas/autorizações/confirmações/auditoria | JARVIS Core | CONTRACT-06 coordena apresentação; não desloca ownership. |
| Execução real de ferramentas | JARVIS Execution Runtime | CONTRACT-01; seleção e proposta não são grants. |
| Capacidades e validações próprias de integração | Capability Provider | CONTRACT-01; declarações não autorizam por si. |
| Configuração local, conexões e credenciais protegidas | JARVIS | CONTRACT-07; autenticação externa é complementar. |
| Identidade e permissões emitidas pelo provedor | Serviço externo | CONTRACT-07; escopo externo não amplia autoridade JARVIS. |
| Memória cognitiva e lifecycle | Sofias Memory | CONTRACT-02; nenhuma execução pelo Memory. |
| Documentos, indexação, fontes/proveniência | Sofias Memory | CONTRACT-03; documento não concede autoridade. |
| Inferência | AI Provider, coordenado pelo JARVIS | CONTRACT-04; propostas passam pelo Execution Runtime. |
| Reconhecimento/síntese | Voice Provider, coordenado pelo JARVIS | CONTRACT-05; voz/áudio não são comandos automaticamente autorizados. |
| UI, navegação e decisões do proprietário | Interaction Surface transmite; Core valida | CONTRACT-06; botão não é execução. |

**Conclusão aprovada:** nenhuma transferência contraditória de autoridade foi identificada entre os contratos revisados. Isso não equivale a auditoria de arquitetura ou implementação.

## R.3 Fluxos transversais verificados conceitualmente

| Jornada | Fronteiras | Avaliação |
|---|---|---|
| Voz → resposta | CONTRACT-05 → CONTRACT-04 → CONTRACT-06 | Coerente. |
| Usuário solicita ação externa | CONTRACT-06 → CONTRACT-04 → CONTRACT-01 / CONTRACT-07 | Coerente. |
| Aprovação de envio | CONTRACT-06 → controle interno JARVIS → CONTRACT-01 | Coerente. |
| Solicitação de memória | CONTRACT-06 → CONTRACT-02 | Coerente. |
| Consulta documental para resposta | CONTRACT-03 → CONTRACT-04 → CONTRACT-06 | Coerente. |
| Conexão expira durante Task | CONTRACT-07 → CONTRACT-01 → Task Runtime → CONTRACT-06 | Coerente. |
| Resultado externo desconhecido | CONTRACT-01 → Task Runtime → CONTRACT-06 | Coerente. |
| Transcrição final duplicada | CONTRACT-05 → CONTRACT-06 | Coerente. |

Fluxos são relações semânticas, **não** definições de chamadas diretas, protocolos de comunicação ou serviços fisicamente isolados.

## R.4 OQ-06 — representação de ferramentas, autorizações e tarefas

**Decisão de fechamento:** `RESOLVED AT CONTRACT BOUNDARY LEVEL — implementação interna pendente de Architecture`.

- Tools possuem fronteira externa formalizada no CONTRACT-01.
- Confirmações e autorizações possuem comportamento nas SPEC-01/08; interação com UI no CONTRACT-06.
- Tasks possuem lifecycle na SPEC-02 e exposição na interface pelo CONTRACT-06.
- **Não** criar contratos artificiais Task ↔ Authorization ↔ Audit sem fronteira independente real. Isso **não** significa que schemas, modelos persistentes ou APIs técnicas internas estejam definidos.

## R.5 Pendências técnicas rastreadas

| ID | Ponto pendente | Encaminhamento aprovado |
|---|---|---|
| **CTR-R01** | Tipos, obrigatoriedade e validação definitiva dos payloads | Formalizar tecnicamente antes da implementação de cada fronteira. |
| **CTR-R02** | IDs, correlação, idempotência e concorrência | Architecture e desenho técnico, preservando garantias. |
| **CTR-R03** | Negociação de versão/capacidades e tradução de erros | Verificar providers e adapters reais selecionados. |
| **CTR-R04** | Compatibilidade efetiva do Sofias Memory | Auditar contrato público/API e capacidades da versão utilizada. |
| **CTR-R05** | Segurança e isolamento de providers executáveis | Architecture com validação das garantias exigidas. |

Os itens são dependências concretas da implementação afetada e **não** autorização para completar lacunas silenciosamente. Garantia incompatível exige revisão explícita.

## R.6 Integridade do MVP e decisões abertas

- **MVP:** proprietário único por instalação, múltiplas contas externas permitidas; **dois domínios externos reais**, incluindo pelo menos uma alteração real supervisionada; demonstrações têm de verificar os resultados, não apenas simulá-los.
- **Sofias Memory:** serviço de informação/declarações, nunca executor operacional; contratos reais ainda a auditar (`CTR-R04`, RISK-01).
- **Conversation/Voice:** texto e voz compartilham história; transcrição provisória não executa comando; falhas de áudio preservam texto.
- **Autorização/Tasks:** grants não surgem de memória, modelo, tool ou UI; `UNKNOWN` não vira sucesso e não motiva repetição insegura; recuperação não ignora estado nem autorizações.
- **Privacidade:** persistência cognitiva automática desabilitada por padrão no MVP; retenção detalhada/backup, voz crítica e custos não mensuráveis mantêm condições da Fase 04.
- **Tecnologia ainda OPEN:** linguagem/core, OS, frontend, modelo de IA e voz, topologia, protocolos (inclusive MCP), persistência operacional, Secret Storage e isolamento. **OQ-01** (quais duas integrações) permanece aberta.
- **FUTURE/DEFERRED:** Agent Builder, Skill Evolution, Plugin Discovery avançado, automação desktop avançada, grants progressivos, proatividade recorrente, Multi-Agent, Knowledge Galaxy, Multi-Channel, Multi-User e demais capacidades futuras não entram no MVP por consequência deste documento.
- Reaproveitamento de `sofias_assistant` só após avaliação; não constitui dependência arquitetural do JARVIS.

## R.7 Resultado e autorização de fechamento

| Indicador | Resultado aprovado |
|---|---|
| Contratos normativos | 7/7 APPROVED |
| Critérios de aceitação | 122 IDs únicos |
| Contradições funcionais bloqueadoras identificadas | Nenhuma na revisão conceitual |
| Pendências técnicas rastreadas | 5 (CTR-R01–CTR-R05) |
| OQ-06 | Resolvida no nível de fronteiras; desenho interno segue para Architecture |
| Novo CONTRACT-08 | Não necessário no momento, salvo nova fronteira real comprovada |
| Próximo passo legítimo | **Fase 06 — Architecture**, mediante processo próprio de revisão e aprovação humana |

**Regra de controle de alterações:** qualquer mudança de semântica, lifecycle, autoridade, finalidade, compatibilidade, resultado ou critério de aceitação dos contratos requer aprovação explícita. Não substituir baselines aprovados por decisões silenciosas. Materialização do documento não equivale a autorização de implementação.

## R.8 Project State após a Fase 05

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | Fase 05 — Contracts concluída; próxima: Architecture |
| **Current role** | Software Architect |
| **Approved** | Discovery, Product Definition, PRD, Specs, CONTRACT-01–07 e revisão de consistência |
| **Current artifact** | `docs/product-manager/05-JARVIS-Contracts.md` |
| **Open / Deferred** | OQ-01, demais decisões tecnológicas e condições operacionais ainda abertas; CTR-R01–R05 |
| **Current Slice** | Nenhum slice de implementação aprovado |
| **Next legitimate step** | Iniciar Architecture por decisões revisáveis, baseadas no escopo e garantias aprovadas |

---

*Fim de JARVIS — Contracts de Interoperabilidade (Fase 05).*

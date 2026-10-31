# JARVIS — Architecture

| Campo | Valor |
|---|---|
| **Projeto** | JARVIS — assistente pessoal universal |
| **Fase** | 06 — Architecture |
| **Status** | **APPROVED** — ARCH-01 a ARCH-06 e revisão final aprovadas pelo proprietário |
| **Data da consolidação** | 2026-10-30 |
| **Papel predominante** | Software Architect |
| **Destino no repositório** | `docs/product-manager/06-JARVIS-Architecture.md` |
| **Baselines anteriores** | Discovery (01); Product Definition (02); PRD (03); Specs (04); Contracts (05), todos APPROVED |
| **Natureza** | Arquitetura lógica, responsabilidades, ownership, trust boundaries, fluxos, persistência, implantação, escolhas tecnológicas e questões pendentes; **não** é implementação, contrato físico de API, ADR ou backlog aprovado |
| **Próxima fase** | 07 — ADRs, após salvar este artefato |

> **Regra de fidelidade:** este documento consolida as seis decisões arquiteturais expressamente aprovadas (ARCH-01 a ARCH-06), seus **95 critérios de validação** e a revisão final. Nomes de diretórios, classes, métodos, diagramas e payloads ilustrativos não se transformam em estruturas físicas obrigatórias. As escolhas **OPEN**, **candidatas**, **condicionadas à validação** e **DEFERRED** continuam com esses estados. Toda alteração de decisão aprovada exige revisão explícita.

## 0. Contexto, princípios e índice

### 0.1. Objetivo arquitetural

O JARVIS é um assistente pessoal universal, inteligente, persistente e extensível. Deve conversar por texto e voz no mesmo contexto; recuperar memórias e conhecimento pelo Sofias Memory; selecionar e utilizar capacidades externas; coordenar tarefas; executar efeitos externos sob autoridade verificável; preservar resultados e incertezas; e permitir acompanhamento pela interface. O MVP é **single-owner por instalação**, demonstrará **dois domínios externos reais** e **pelo menos uma alteração externa supervisionada, efetiva e verificável**.

O JARVIS é **um produto novo e independente** do Sofia's Assistant. Componentes existentes poderão ser reutilizados seletivamente, somente após auditoria de conformidade e adequação. O Sofias Memory é um **serviço independente** para memória cognitiva e conhecimento; **nunca** executor de tarefas, ferramentas, agentes, grants ou autorizações operacionais.

### 0.2. Invariantes transversais

1. **AI proposes; JARVIS authorizes; controlled executor acts.** Resultado de modelo não é autoridade.
2. **Estado operacional é do JARVIS.** Histórico, tarefas, confirmações, conexões, execução e auditoria não pertencem ao Sofias Memory.
3. **Memória e conteúdo externo são dados, não política.** Dados recuperados não ampliam privilégios.
4. **Seleção não equivale a autorização.** Capability registrada, conexão configurada e permissão externa não concedem autorização operacional por si sós.
5. **Nenhuma execução externa protegida sem registro durável prévio**, nos termos da ARCH-02.
6. **UNKNOWN não significa FAILED ou SUCCESS**, nem habilita retry automático perigoso.
7. **Adapter não contém regra de domínio no Core**: lógica peculiar de serviços externos permanece nas integrações.
8. **Modularidade lógica não equivale a isolamento de segurança.** Extensões executáveis não confiáveis exigem isolamento efetivo.
9. **Privacidade e limites de recursos são controles operacionais**, inclusive durante fallback e tarefas.
10. **Implementar pelo menor incremento funcional verificável.** Não adiantar infraestrutura, multiusuário, marketplace, multiagentes ou autonomia ampla sem necessidade e aprovação.

### 0.3. Índice das decisões

| ID | Decisão aprovada | Critérios |
|---|---|---:|
| ARCH-01 | Modular Monolith + Ports & Adapters; ownership e responsabilidades | 10 |
| ARCH-02 | Transactional Operational State + Durable Execution Journal + Conservative Recovery | 14 |
| ARCH-03 | Centralized Policy Enforcement + Protected Execution Gateway + Risk-Proportionate Isolation | 18 |
| ARCH-04 | Local-first Desktop, Windows inicial; integração com serviços independentes | 15 |
| ARCH-05 | Python + SQLite; PySide6/Vue/Vuetify candidato sujeito a prova técnica | 14 |
| ARCH-06 | Contract-Driven Providers + Explicit Registry + seleção de capacidades + fallback opcional | 24 |
| **TOTAL** | **6 decisões APPROVED** | **95** |

### 0.4. Relação com os contratos

| Contrato | Fronteira |
|---|---|
| CONTRACT-01 | Capability Provider ↔ JARVIS Execution Runtime |
| CONTRACT-02 | JARVIS ↔ Sofias Memory: Cognitive Memory |
| CONTRACT-03 | JARVIS ↔ Sofias Memory: Knowledge Retrieval |
| CONTRACT-04 | JARVIS Inference Runtime ↔ AI Provider Adapter |
| CONTRACT-05 | JARVIS Voice Runtime ↔ Voice Provider Adapter |
| CONTRACT-06 | JARVIS Interaction Surface ↔ Application Core |
| CONTRACT-07 | JARVIS Connection Manager ↔ Integration Connection Adapter |

Contracts descrevem acordos entre partes interoperáveis. Architecture descreve organização e garantias técnicas. Os schemas concretos e escolhas duráveis necessárias serão completados nas etapas apropriadas, sem alterar silenciosamente os contratos.

---

# ARCH-01 — Topologia e Organização Arquitetural do JARVIS

**Status:** APPROVED. **Referências:** PRD-01–PRD-11, SPEC-01–SPEC-11, CONTRACT-01–CONTRACT-07.

## 1. Purpose / Problem

O JARVIS coordena conversação, inferência, memória, voz, ferramentas, autorização, tarefas e persistência. Deve evitar simultaneamente o **acoplamento excessivo** de um monólito indiferenciado e a **complexidade prematura** de múltiplos serviços, sincronizações e operações distribuídas. O MVP não tem justificativa para distribuirmos internamente o Core apenas por categoria funcional.

## 2. Alternativas consideradas

| Alternativa | Benefício | Limitação / decisão |
|---|---|---|
| A — Monólito convencional | Inicialização e deployment simples | Acoplamento de domínios e interfaces excessivo; não preferido |
| **B — Monólito modular com Ports & Adapters** | Ownership claro, deployment simples e substituição de integrações | **APROVADO**; requer disciplina real nas fronteiras |
| C — Microsserviços distribuídos | Isolamento de implantação e escala independente | Sem justificativa para o MVP |

**Decisão normativa:** **Modular Monolith** no Core, com **Ports & Adapters nas fronteiras contratuais que efetivamente os exigirem**. Isso **não** impõe Clean/Hexagonal Architecture formal em todas as classes, nem número fixo de pacotes ou camadas abstratas.

## 3. Componentes lógicos mínimos

```text
Interaction Surface  [CONTRACT-06]
        │ comandos / eventos / consultas / snapshots
        ▼
JARVIS Core — Modular Monolith
  ├─ Conversation & Context
  ├─ Orchestration & Tasks
  ├─ Policy & Execution
  ├─ Connections & Capabilities
  ├─ Audit & Resource Control
  ├─ Provider Coordination
  └─ Operational Persistence (autoridade do JARVIS)
        │ ports / adapters
        ├── AI Providers                  [CONTRACT-04]
        ├── Voice Providers               [CONTRACT-05]
        ├── Sofias Memory                 [CONTRACT-02/03]
        └── External Integrations         [CONTRACT-01/07]
```

Os itens representam **responsabilidades**, não processos independentes, microsserviços, tabelas obrigatórias ou hierarquia imutável de diretórios.

## 4. Ownership

| Responsabilidade | Owner |
|---|---|
| Conversas, mensagens, contexto conversacional e histórico | JARVIS |
| Coordenação, planejamento, tarefas e recuperação operacional | JARVIS |
| Autorizações, confirmações, concessões válidas e execução | JARVIS |
| Conexões locais, preferências, consumo e auditoria | JARVIS |
| Estado de UI, navegação e apresentação | Interaction Surface; Core mantém estado canônico |
| Memória cognitiva, fontes, documentos e proveniência | Sofias Memory |
| Credenciais emitidas e permissões externas concedidas | Provedor externo; uso local é controlado pelo JARVIS |
| Operações específicas de domínio | Adapters e serviços externos, submetidos ao Core |

O Core **não** incorporará regras nativas de CRM, e-commerce, assistência técnica, calendário, e-mail ou outro domínio particular.

## 5. Data flow — operação externa

```text
Pedido (texto/voz)
    ↓
Conversation/Context
    ↓
Inferência/avaliação/planejamento proporcional
    ↓
Capability + conexão pertinentes
    ↓
Policy + autorização + limites + confirmação aplicável
    ↓
PERSISTÊNCIA DURÁVEL DA TENTATIVA
    ↓
Protected Dispatch via Provider Adapter
    ↓
Registro de resultado observável / parcial / UNKNOWN
    ↓
Task / Conversation / Interaction Surface
```

Não se deve confundir envio de solicitação ao serviço externo com confirmação de efeito no destino. A etapa de durabilidade deve anteceder o despacho de operações protegidas e observar as garantias detalhadas na ARCH-02.

## 6. Trust boundaries e extensões

Interface, modelo de IA, memória, documentos e ferramentas não são fontes independentes de autoridade. Código de plugin não confiável não ganha confiança por ser instalado localmente. Adapters internos confiáveis podem compartilhar processo; extensões executáveis não confiáveis precisam de **isolamento efetivo ou não podem ser executadas com privilégios irrestritos**. Divisão em módulos não é sandbox.

## 7. Persistência e processamento

O JARVIS mantém persistência operacional própria, independente da persistência cognitiva do Sofias Memory. Trabalho demorado não deverá bloquear desnecessariamente a UI. O requisito de assincronia não exige previamente RabbitMQ, Redis, scheduler avançado, workers distribuídos ou microsserviços. Mecanismos físicos serão escolhidos com base nos requisitos reais.

## 8. Deployment e portability

ARCH-01 **não** decidiu sistemas operacionais, linguagem, UI, banco, modelo de IA, protocolos ou topologia física entre UI/Core. Essas decisões foram tratadas progressivamente em ARCH-04/05 ou continuam abertas. A organização deverá permitir substituição de interface sem transferir política ou estado operacional para ela.

## 9. Consequências / trade-offs

| Benefício | Custo / limitação |
|---|---|
| Implantação e integração internas simples | Disciplina de responsabilidade e acoplamento |
| Testes por comportamentos e contratos | Exige manter fronteiras verificáveis |
| Evolução de adapters sem contaminar Core | Não fornece isolamento físico automático |
| Menor complexidade que microsserviços | Não oferece escalabilidade distribuída automática, desnecessária inicialmente |

## 10. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH01-AC01 | Uma integração nova não exige lógica específica do domínio no Core |
| ARCH01-AC02 | Sofias Memory não executa operações nem administra tarefas |
| ARCH01-AC03 | Propostas de modelos de IA não contornam autorização |
| ARCH01-AC04 | Interface não possui autoridade operacional própria |
| ARCH01-AC05 | O estado operacional persiste independentemente do Sofias Memory |
| ARCH01-AC06 | Uma falha externa não inutiliza funções independentes |
| ARCH01-AC07 | Tarefas demoradas não bloqueiam desnecessariamente a interface |
| ARCH01-AC08 | Execuções desconhecidas não são repetidas automaticamente após reinicialização |
| ARCH01-AC09 | Extensões não confiáveis não recebem acesso irrestrito por padrão |
| ARCH01-AC10 | O MVP não exige uma infraestrutura distribuída própria sem justificativa |

**Non-Goals:** obrigação de microsserviços, frameworks abstratos por classe, generic repositories indiscriminados, broker por antecipação, escolha de linguagens e UI nesta decisão, execução irrestrita de plugins de terceiros.

---
# ARCH-02 — Operational Persistence & Recovery Architecture

**Status:** APPROVED. **Referências:** FR-003, FR-026–FR-046, FR-064, NFR-001–NFR-004, NFR-007; SPEC-01/02/03/08/10/11; CONTRACT-01/06; ARCH-01.

## 1. Problema e garantia central

Uma alteração externa pode ser efetivada antes que o JARVIS receba ou persista a resposta. Se o serviço receber um envio de e-mail e a aplicação encerrar antes de salvar o sucesso, o resultado registrado será insuficiente para afirmar sucesso ou falha. Reiniciar a tarefa ou repetir automaticamente pode produzir efeitos duplicados.

Devem ser diferenciados: **(a) estado que o JARVIS efetivamente persistiu**, **(b) efeito que realmente ocorreu fora dele**, e **(c) evidência que permite conhecer esse efeito**.

## 2. Alternativas e decisão

| Alternativa | Avaliação |
|---|---|
| A — State snapshots simples | Insuficientes para rastrear tentativas, autorizações e incerteza de operações externas |
| **B — Transactional State + Durable Execution Journal** | **APROVADA**: estado canônico consultável e evidências operacionais duráveis |
| C — Event Sourcing integral | Não necessário; aumenta complexidade para o MVP |

**Decisão:** **Transactional Operational State + Durable Execution Journal + Conservative Recovery**. O JARVIS manterá uma **autoridade lógica** de persistência operacional, sem comprometer previamente o modelo físico ou exigir um message broker.

## 3. Categorias de estado sob autoridade do JARVIS

| Categoria | Informação / função |
|---|---|
| Conversation State | Conversas, mensagens, contexto necessário à continuidade |
| Task State | Objetivos, etapas, progresso, espera e resultados parciais |
| Task Attempt | Tentativas de continuidade e respectivas evidências |
| Authorization State | Confirmações, parâmetros materiais, validade e decisões |
| Operation Attempt / Execution Journal | Preparação, autorização, admissão, tentativa de despacho, evidências e incerteza |
| Connections & Settings | Identidade local de conexões, habilitação, configuração e preferências |
| Resource Budget | Limites, consumo observado/estimado/desconhecido e decisões de bloqueio |
| Audit Evidence | Correlação de origem, política, operação, tentativa e resultado sem expor segredos |

A informação cognitiva/documental permanece sob autoridade do Sofias Memory; o Execution Journal não se confunde com memória de longo prazo.

## 4. State Records e Execution Journal

**State Records** expõem o estado atual e permitem consultas, inclusive após restart. **Execution Journal** preserva acontecimentos relevantes e a possibilidade de um efeito externo ter sido iniciado. Não se exige gravar indiscriminadamente prompts, documentos, áudio bruto ou credenciais.

| Registro do Journal | Finalidade |
|---|---|
| Operação preparada | Identidade, alvo e parâmetros materiais, efeitos previstos |
| Autoridade verificada | Política, autorização e confirmação pertinentes |
| Despacho admitido | Tentativa identificável que **pode** alcançar o provedor |
| Resultado observado | SUCCESS, FAILED, UNKNOWN ou efeitos parciais com evidências |
| Recuperação avaliada | Decisão de revalidar, aguardar intervenção, reconciliar ou encerrar |

## 5. Persist-before-dispatch — invariant

**Nenhuma operação externa protegida deverá ser despachada antes da persistência durável da tentativa e das informações necessárias à recuperação.**

```text
PREPARE operation
    ↓
AUTHORIZE / CONFIRM / CHECK CONNECTION & BUDGET
    ↓
PERSIST DISPATCH INTENT (commit confirmado)
    ↓
DISPATCH to provider
    ↓
PERSIST OBSERVED RESULT (ou UNKNOWN quando aplicável)
    ↓
UPDATE TASK / UI
```

A intenção persistida **não demonstra que o envio ocorreu**, apenas que ele **pode ter ocorrido**. A autorização e o estado da conexão deverão permanecer válidos no ponto de admissão; mudanças concorrentes (por exemplo, disable) necessitam de ordenação verificável.

## 6. Matriz de falhas e recuperação

| Janela de interrupção | Interpretação segura | Próxima ação |
|---|---|---|
| Antes de persistir uma operação | Não existe despacho admitido por esse fluxo | Reavaliar solicitação e condições antes de agir |
| Preparada, mas sem despacho admitido | Operação ainda não deveria ter alcançado provider | Revalidar antes de admitir |
| Intenção persistida, antes/durante o envio | Despacho pode ter ou não ocorrido | Tratar como **potencial efeito externo** |
| Envio efetivo sem resposta | Resultado externo desconhecido | Não repetir automaticamente |
| Resposta recebida, não persistida | Estado durável não comprova resultado | Consultar evidência externa ou solicitar revisão |
| Resultado persistido | Resultado conhecido no alcance da evidência | Recuperar estado sem reexecutar |

A recuperação deverá favorecer segurança a disponibilidade ilusória: **UNKNOWN permanece desconhecido até evidência suficiente**. Uma operação de escrita não deve ser automaticamente repetida por mera reinicialização ou timeout.

## 7. Limite da garantia de execução

Não se promete **exactly-once execution** de efeitos externos arbitrários. O banco do JARVIS e o serviço externo não compartilham uma transação atômica universal. Idempotência do provider só pode ser usada quando o contrato e o comportamento real oferecerem garantia verificável; uma string local de identificação não cria idempotência por si só.

O JARVIS deverá identificar tentativas, evitar dupla admissão intencional da mesma tentativa, revalidar operações antes de novas tentativas e reconciliar resultados quando um provider oferecer consulta confiável.

## 8. Autorizações, confirmações e concorrência

Uma confirmação persistida deve vincular identidade da confirmação, operação, conexão, **parâmetros materiais**, estado/validade, decisão humana e eventual tentativa de execução. Aprovar duas vezes a mesma confirmação não deve gerar duas operações. Alteração de alvo, destinatário, conteúdo ou efeito relevante exige nova avaliação.

Transições críticas devem ser **atômicas e concorrencialmente seguras**: dois executores não podem avançar a mesma tentativa como proprietários exclusivos; não pode haver dois despachos independentes por corrida de aprovação; desabilitar conexão impede **novas admissões** após efetivação, embora operações já enviadas possam concluir ou ter resultado incerto. Locks, versões e transações físicas serão escolhidos depois.

## 9. Lifecycle de Task, attempts e recuperação

Preservam-se os estados da SPEC-02: `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `INTERRUPTED`. **Task**, **Task Attempt** e **Operation Attempt** são identidades conceituais distintas: retomar uma tarefa não significa repetir efeitos realizados por attempts anteriores.

Após reinicialização, um estado persistido `RUNNING` não comprova atividade em execução. O JARVIS deve inspecionar tentativas e dependências; quando a segurança da continuidade for incerta, aplicar `WAITING` e motivo de revisão de recuperação (como `RECOVERY_REVIEW`, quando apropriado segundo SPEC-02). Resultados parciais e autorizações pendentes são preservados. Nenhuma task é integralmente reexecutada por regra geral de startup.

## 10. Eventos da UI e estado canônico

Eventos de interface não substituem registros duráveis. Uma notificação perdida não apaga o resultado da task. Após desconexão, o CONTRACT-06 exige reconciliação com snapshot/consulta de estado canônico, controle de versões quando necessário, e não apresentar estado obsoleto como atual confirmado.

## 11. Degradação quando a persistência estiver indisponível

| Função | Tratamento |
|---|---|
| Nova operação externa protegida | **Bloquear** se não puder persistir duravelmente pré-condições e tentativa |
| Aprovação | Não afirmar decisão persistida sem confirmação |
| Avanço de task rastreável | Não avançar etapa cuja segurança dependa da durabilidade indisponível |
| Consulta local já recuperada | Disponível quando possível, informando eventual desatualização |
| Conversação sem efeito externo | Pode existir modo **explicitamente não persistente**, se suportado e claramente informado |
| Retorno do armazenamento | Reconciliar antes de retomar operações protegidas |

Isso não exige encerrar completamente o aplicativo quando o armazenamento falha, mas **não permite** execução protegida sem rastreabilidade.

## 12. Sofias Memory, privacidade e retenção

Sofias Memory não participa do commit operacional do JARVIS nem mantém suas tasks. Chamadas de memória sujeitas a resposta perdida respeitam CONTRACT-02; não se exige transação distribuída com o serviço. O Journal usa referências e evidências mínimas. Credenciais e informações confidenciais devem ser protegidas; prazos de retenção e backup permanecem em aberto (`SPEC-R01`, `ARCH-R06`). A necessidade de auditoria não autoriza retenção ilimitada de dados pessoais.

## 13. Tecnologia requerida por semântica

A solução de persistência deve sustentar **atualizações atômicas**, **durabilidade pré-despacho**, **controle de concorrência**, **identidades estáveis**, **recuperação consistente** e **consultas de estado canônico**. ARCH-02 recomendou avaliar armazenamento relacional transacional prioritariamente, **sem ainda fixar produto**; ARCH-05 posteriormente aprovou SQLite para o MVP. Cache não substitui a autoridade operacional e Redis não é exigido como dependência operacional.

## 14. Consequências

A pré-persistência acrescenta custos de I/O e transações, mas reduz o risco de duplicação e permite auditoria. A arquitetura é mais complexa que salvar apenas snapshots, porém mais simples que Event Sourcing integral e sem promessa de atomicidade distribuída com terceiros.

## 15. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH02-AC01 | Conversas, tarefas e estados operacionais necessários sobrevivem à reinicialização |
| ARCH02-AC02 | Operações protegidas não são despachadas sem registro durável prévio |
| ARCH02-AC03 | Reinicialização entre registro e despacho não provoca repetição insegura |
| ARCH02-AC04 | Resposta externa perdida produz tratamento de resultado desconhecido |
| ARCH02-AC05 | Sucesso observado e persistido não gera nova execução após recuperação |
| ARCH02-AC06 | Confirmação duplicada não produz dois despachos independentes |
| ARCH02-AC07 | Duas continuações concorrentes não assumem indevidamente a mesma tentativa |
| ARCH02-AC08 | Tarefa com resultados parciais é recuperada sem perder informações anteriores |
| ARCH02-AC09 | Falha do Sofias Memory não compromete o estado operacional independente |
| ARCH02-AC10 | Falha de persistência bloqueia novas operações que dependem de durabilidade |
| ARCH02-AC11 | Interface reconectada recupera estado canônico consistente |
| ARCH02-AC12 | Auditoria preserva evidências sem expor indevidamente credenciais |
| ARCH02-AC13 | Desabilitação concorrente de conexão impede a admissão de novas operações após sua efetivação |
| ARCH02-AC14 | O sistema não promete execução exactly-once sem garantias efetivas do serviço externo |

**Non-Goals / Open:** banco físico específico na ARCH-02 (posteriormente SQLite na ARCH-05), entidades e índices físicos, ORM, locking, outbox, filas, workers, calendário de recuperação, mecanismo de backup, prazo de retenção, sandbox de plugins, transações distribuídas e Event Sourcing integral.

---

# ARCH-03 — Execution & Trust Boundaries

**Status:** APPROVED. **Referências:** SPEC-01/02/05/06/09/10/11, CONTRACT-01/04/06/07, ARCH-01/02.

## 1. Threat model e objetivo

Conteúdos de documentos, memórias e respostas de ferramentas podem conter **prompt injection**; extensões podem ser comprometidas; autorizações e condições de conexão podem ficar obsoletas entre apresentação e despacho. O problema comum é impedir efeitos operacionais por componentes que **não possuem a autoridade necessária**.

## 2. Alternativas e decisão

| Alternativa | Avaliação |
|---|---|
| A — Segurança delegada a cada provider | Rejeitada: políticas inconsistentes e bypass |
| **B — Policy Enforcement centralizado + isolamento proporcional** | **APROVADA** |
| C — Sandbox universal obrigatório para toda operação | Custoso e não é uma garantia universal; desnecessário para componentes internos confiáveis |

**Decisão:** **Centralized Policy Enforcement + Protected Execution Gateway + Risk-Proportionate Isolation**. O ponto lógico de admissão é único, não necessariamente uma única classe; seus controles não podem ser contornados por conversas, agents, skills, plugins ou providers.

## 3. Fronteiras de confiança

| Origem / componente | Pode | Não pode |
|---|---|---|
| Proprietário | Solicitar e aprovar operações específicas | Tornar tecnicamente possível uma operação não suportada |
| Interaction Surface | Transmitir comandos e decisões | Autorizar ou executar diretamente |
| Modelo de IA, planner, agents e skills | Interpretar, planejar e propor | Conceder grants, invocar operações protegidas fora do gateway |
| Sofias Memory | Fornecer memória e conhecimento com proveniência | Criar/usar grants ou administrar execução |
| Capability Descriptor | Descrever operações e efeitos declarados | Determinar sozinho política ou classificação definitiva |
| Adapter confiável | Executar operação admitida dentro de seu escopo | Ampliar permissão ou acessar segredos alheios |
| Extensão executável não confiável | Executar apenas sob controles verificáveis | Acessar livremente Core, credenciais, arquivos, rede ou processos |
| Provedor externo | Fornecer resultados e impor permissões externas | Conceder autoridade interna ao JARVIS |

## 4. Protected Execution Gateway

Toda invocação executável passa logicamente por: resolução de capability e conexão; validação de argumentos; avaliação dos **efeitos reais**; política de autorização; confirmação quando exigida; limites de custo e recursos; persistência de tentativa; admissão e despacho; registro de resultados/efeitos parciais e incerteza.

```text
Conversation / Planner / Agent / Skill
               ↓ propostas
        Capability Resolver
               ↓
    Policy + Effects + Identity + Connection
               ↓
    Confirmation (quando aplicável)
               ↓
    Revalidação das pré-condições vigentes
               ↓
    Durable Attempt / Execution Journal
               ↓
         Execution Gateway
               ↓
    Controlled adapter / provider
               ↓
    Evidence → Task / UI / Audit
```

O Core não precisa conhecer procedimentos particulares de e-mail, CRM ou calendário. O adapter não decide sozinho se a operação é autorizada.

## 5. Operation Envelope (conceitual)

| Elemento | Uso |
|---|---|
| `operation_id` | Identificar operação |
| `capability_id` / `provider_id` | Identificar habilidade e executor pretendido |
| `connection_ref` | Conta externa específica |
| `arguments` | Parâmetros validados |
| `operation_class` / `declared_effects` | Categoria candidata e consequências |
| `origin_ref` | Conversa, pedido ou tarefa de origem |
| `policy_context` | Dados necessários para autoridade |
| `resource_constraints` | Limites e custos |
| `operation_revision` | Identificar mudanças materiais |

Não é um schema definitivo. Alteração material de destinatário, alvo, conteúdo, conexão ou efeitos obriga reavaliar confirmação e autoridade. Igualdade de `operation_id` não prova igualdade da operação aprovada; não se escolheu mecanismo de hashing.

## 6. Classificação por efeitos

As categorias funcionais aprovadas continuam `READ`, `PREPARE`, `WRITE`, `CRITICAL`. Preparar rascunho em serviço externo pode ser WRITE; uma READ pode expor dados sensíveis. Descritores de plugins são **informações candidatas**, não fonte definitiva de risco. A ausência de condições verificáveis para uma operação protegida impede execução por presunção.

## 7. Policy Evaluation

| Resultado lógico | Significado |
|---|---|
| `PERMITTED` | Autoridade suficiente nas condições verificadas |
| `CONFIRMATION_REQUIRED` | Precisa de decisão do proprietário |
| `DENIED` | Não pode prosseguir |
| `UNVERIFIABLE` | Garantia obrigatória não pode ser verificada; fail-closed |

Esses resultados são conceituais e **não** substituem os estados normativos de execução da SPEC-01. Falha do avaliador nunca vira permissão implícita. O bloqueio da operação protegida não precisa inutilizar funções independentes.

## 8. Confirmação humana e operação autorizada

O Core prepara operação específica, determina risco e necessidade de aprovação, apresenta ao usuário parâmetros materiais, registra decisão vinculada e **revalida as condições pertinentes antes da admissão**. Uma confirmação não pode autorizar destinatário ou efeitos diferentes, nem ser consumida duas vezes. A desabilitação efetiva de conexão bloqueia novas admissões. Aprovações anteriores não viram grants persistentes amplos.

**Confirmação por voz:** a transcrição de uma frase, isoladamente, não comprova identidade nem consentimento inequívoco; as salvaguardas concretas permanecem em `SPEC-R02` / `ARCH-R07`. Até haver garantia suficiente, não considerar a simples transcrição autorização protegida.

## 9. Credenciais e conexão

Responsabilidade lógica de **Credential Access** permite disponibilizar apenas o acesso necessário à operação e à conta autorizada. Uma credencial de conexão não deve estar disponível a outra por conveniência. Não incluir segredos em prompts, logs ou resultados. O mecanismo pode usar armazenamento protegido, mediação ou fornecimento controlado ao adapter; não há obrigação de broker como processo separado.

## 10. Trusted adapters × untrusted extensions

| Tipo | Regra |
|---|---|
| Adapter interno confiável, desenvolvido e auditado | Pode executar no processo do Core, sob contratos e controles |
| Adapter declarativo com restrições verificadas | Pode ser interpretado sem conceder execução privilegiada |
| Plugin executável de terceiros | Precisa de isolamento efetivo e escopo limitado |
| Plugin sem isolamento demonstrado | Não pode obter execução irrestrita |
| Código gerado por IA | Não adquire confiança por origem interna |

Separação em Python packages e até processo separado **não** prova isolamento se credenciais, arquivos, rede e privilégios continuarem abertos. Não exigir sistema universal de plugins no MVP. Dois domínios externos reais podem ser validados por adapters confiáveis.

## 11. Data Plane × Control Plane

| Plano | Conteúdo |
|---|---|
| **Data Plane** | Texto, documentos, memórias, prompts, resultados de tools |
| **Control Plane** | Política, identidade, autorização, verificação e despacho |

Conteúdo do Data Plane **nunca** modifica diretamente o Control Plane. Instruções embutidas em documentos são tratadas como dados; não há promessa de segurança baseada apenas em prompts de sistema. O Enforcement deve ser independente da saída do modelo.

## 12. Concorrência e TOCTOU

A autorização validada no preparo pode tornar-se inválida antes do despacho. Admissões e mudanças de estado relevantes devem ter ordenação transacional verificável. Após `DisableConnection` efetivo, novas admissões são vedadas; operações admitidas antes podem produzir efeitos. Não escolher locks ou framework nesta fase.

## 13. Evidências, falhas e auditoria

A execução distingue `SUCCESS`, `FAILED`, `UNKNOWN` e efeitos parciais. Resultado declarado pelo adapter não deve ser descrito como verificação independente se não houver tal evidência. Timeout e perda de conexão não provam ausência de efeito. Auditabilidade: `Origin → Operation → Policy Decision → Confirmation → Dispatch Attempt → Provider Result`, sem segredos e com retenção definida posteriormente.

## 14. Non-Goals e trade-offs

Não exige service mesh, microsserviço de autorização, sandbox universal, RBAC multiusuário, grants progressivos, execução irrestrita de código gerado, sistema de plugins de terceiros, Credential Broker separado ou uma tecnologia de políticas específica. A política protegida adiciona validação e custo de execução, justificados pela capacidade de executar efeitos reais.

## 15. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH03-AC01 | Toda operação executável passa pelo ponto lógico de admissão protegido |
| ARCH03-AC02 | Modelo de IA não consegue conceder autoridade operacional |
| ARCH03-AC03 | Skills, agentes e plugins não contornam a avaliação de política |
| ARCH03-AC04 | Ausência ou falha de verificação obrigatória resulta em bloqueio |
| ARCH03-AC05 | Alteração material da operação invalida a aprovação anterior quando necessário |
| ARCH03-AC06 | Confirmação duplicada não gera autorizações independentes |
| ARCH03-AC07 | Conexões diferentes preservam isolamento de identidade e credenciais |
| ARCH03-AC08 | Uma conexão desabilitada impede novas admissões de operações |
| ARCH03-AC09 | Classificação de efeitos não depende exclusivamente da declaração do plugin |
| ARCH03-AC10 | Código executável não confiável não recebe privilégios irrestritos |
| ARCH03-AC11 | Conteúdo documental ou memória não modifica políticas operacionais |
| ARCH03-AC12 | Transcrição de voz, isoladamente, não é prova suficiente de autorização protegida |
| ARCH03-AC13 | Operação admitida respeita persistência anterior ao despacho |
| ARCH03-AC14 | Resultado externo desconhecido não provoca repetição automática insegura |
| ARCH03-AC15 | Operação e decisão de política possuem correlação auditável |
| ARCH03-AC16 | Credenciais não são expostas indevidamente em prompts, logs ou resultados |
| ARCH03-AC17 | Permissão externa não substitui autorização do JARVIS |
| ARCH03-AC18 | Execuções já iniciadas não são declaradas canceladas apenas pela desabilitação da conexão |

**Decisões OPEN relevantes:** isolamento de plugins não confiáveis; mecanismo físico de políticas; secret store Windows; autenticação da instalação/proprietário; confirmação segura por voz; testes de bypass do gateway. A arquitetura proíbe execução irrestrita antes de provar controles adequados.

---
# ARCH-04 — Runtime & Deployment Context

**Status:** APPROVED. **Referências:** PD-08, PRD-01/05/06/07/10, SPEC-02/03/07/08/10, CONTRACT-02–CONTRACT-07, ARCH-01–ARCH-03.

## 1. Problem / Deployment choices

O JARVIS precisa combinar recursos locais (janela, microfone, áudio, estado operacional), tarefas recuperáveis e providers independentes. Precisamos distinguir o encerramento da interface, o encerramento do Core e o ciclo de uma tarefa, além de não confundir offline parcial com autonomia total.

| Alternativa | Avaliação |
|---|---|
| A — Cloud-first | Facilidade multi-dispositivo, mas maior dependência de conexão e infraestrutura própria |
| **B — Local-first Desktop** | **APROVADA:** autoridade operacional na instalação do proprietário; serviços externos conforme necessidade |
| C — Hybrid Distributed com Core local/remoto e sincronização | Conflitos e complexidade prematuros no MVP |

**Decisão:** **Local-first Desktop**, **Windows** como primeira plataforma, **Windows 11** como alvo inicial de validação. Não define sistema operacional definitivo de todos os releases ou obrigação de Linux/macOS no MVP.

## 2. Topologia lógica

```text
WINDOWS DESKTOP — Instalação do proprietário
  ├── Interaction Surface (aplicação desktop; UI física a validar)
  ├── JARVIS Core — authority, tasks, policy, execution
  └── Operational Persistence local — state + journal
              │ contratos e conexões controladas
              ├── Sofias Memory (serviço INDEPENDENTE; local ou remoto)
              ├── AI Providers (locais ou remotos)
              ├── Voice Providers (locais ou remotos)
              └── External Integrations (APIs, serviços, ferramentas)
```

O Core e o armazenamento operacional devem poder funcionar na instalação Windows, sem uma infraestrutura cloud central obrigatória do próprio JARVIS. A interface e o Core **podem** compartilhar processo ou não; ARCH-04 não os obriga a usar IPC, HTTP, WebSocket ou outra comunicação específica.

## 3. Plataformas e escopo de suporte

| Plataforma | Situação |
|---|---|
| **Windows 11 Desktop** | **Primeiro alvo de implementação e validação do MVP** |
| Outras versões Windows | Suporte não assumido sem validação |
| Linux Desktop | Possível evolução, não compromisso do MVP |
| macOS | Possível evolução, não compromisso do MVP |
| Navegador remoto / múltiplos dispositivos | Não necessário no MVP |

O Core universal deve evitar acoplamento gratuito com APIs Windows; captura/reprodução de áudio, gerenciamento de janelas, credenciais nativas e notificações podem exigir adapters específicos de sistema operacional. Não construir abstrações multiplataforma para recursos ainda inexistentes.

## 4. Lifecycle: UI, Core, voz e tarefas

| Evento / condição | Garantia |
|---|---|
| Inicialização | Recuperar estado durável e dependências essenciais; verificar condições pertinentes |
| UI ativa | Conversa e acompanhamento sem bloquear desnecessariamente |
| Task em andamento | Continua apenas enquanto runtime efetivo e políticas permitirem |
| UI indisponível ou fechada | Não declarar tarefas automaticamente canceladas; preservar estado correto |
| Encerramento do Core | Preservar / registrar o que for possível; não prometer reverter efeitos externos |
| Restart | Recuperação conservadora da ARCH-02 |
| Falha abrupta | Reconciliar tentativas sem repetir ações de resultado incerto |
| Sessão de voz encerrada | Não equivale a cancelar uma task externa |

Minimizar ou fechar a janela não precisa encerrar a mesma entidade operacional, mas **execução contínua em background não é requisito obrigatório do MVP**. O comportamento físico do botão de fechamento, tray/residência e processo em segundo plano continua pendente.

## 5. Degradação de dependências

| Dependência indisponível | Tratamento |
|---|---|
| Sofias Memory | Recall, escrita e conhecimento afetados; demais funções independentes continuam |
| AI Provider | Inferência dependente daquele provider afetada; não inventar resposta |
| Voice Provider | Áudio/STT/TTS correspondente afetado; preservar texto |
| Integração externa | Capacidades daquela conexão não utilizáveis ou degradadas |
| Rede | Recursos remotos afetados; recursos locais independentes podem funcionar |
| Persistência operacional | Bloquear operações protegidas que exigem estado durável |
| UI | Estado canônico preservado conforme lifecycle real do Core |

**Local-first não equivale a offline completo:** disponibilidade depende das tecnologias e dos providers efetivamente utilizados.

## 6. Sofias Memory deployment boundary

O JARVIS deve consumir a **interface pública compatível** do Sofias Memory, sem acesso direto ao PostgreSQL, Neo4j ou filesystem interno do serviço. O Sofias Memory pode executar no próprio dispositivo, em outro dispositivo de rede privada ou em VPS controlada, sem que todas as topologias se tornem matrizes obrigatórias de teste do MVP. A distribuição do JARVIS **não** precisa instalar toda a stack interna do Sofias Memory.

Ao reconectar, verificar capacidades e condições pertinentes, não apenas a existência de uma resposta de rede. Proteger credenciais e dados sensíveis em trânsito conforme topologia real escolhida.

## 7. Exposição do Core e identidade local

Uma API em `localhost` não é confiável somente por usar loopback. Comandos privilegiados devem ser autenticados/autorizados conforme o ambiente e **não haverá exposição pública do Core por padrão**. A comunicação entre processos, se existir, exigirá controles de identidade, integridade e acesso adequados. A escolha de named pipes, sockets, HTTP, gRPC ou canal in-process permanece aberta.

## 8. Dados, secrets, temporários e upgrades

| Categoria lógica | Regra |
|---|---|
| Application Assets | Recursos distribuídos com a aplicação |
| Operational Data | Preservados entre restarts e atualizações |
| Secrets | Proteção adequada, sem reprodução indiscriminada |
| Temporary Data | Descartáveis, inclusive áudio transitório conforme política |
| Logs & Diagnostics | Protegidos, redigidos e limitados por retenção |
| User Configuration | Persistida e validada |

Essas categorias não exigem seis diretórios físicos. Uma atualização da aplicação **não** pode apagar silenciosamente dados operacionais nem ampliar permissões. Alterações de schema deverão ter estratégia de migração, proteção e eventual recuperação. Instalador, paths, updates e backups concretos dependem das decisões de tecnologia e retenção.

## 9. Controle de recursos e limites

CPU, RAM, GPU, armazenamento, uso de rede, concorrência, chamadas pagas e custos deverão ser tratados conforme capacidades reais e SPEC-11. Não inventar hardware mínimo, latência, SLA ou perfil de GPU sem medições. A execução de modelos locais não é requisito: providers locais e remotos podem coexistir conforme política.

## 10. Portabilidade, distribuição e segurança

O domínio de conversação, tarefas e autorização deve permanecer preferencialmente agnóstico do sistema operacional; adapters nativos podem depender de APIs Windows. Não aprovar automodificação silenciosa do Core por modelos de IA. Atualização de software não é aprendizagem cognitiva. Não impor Docker, WSL, serviço Windows, execução permanente no tray, sincronização entre instalações, execução offline integral ou `.exe` desde esta decisão.

## 11. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH04-AC01 | Core e persistência operacional podem executar na instalação principal do proprietário |
| ARCH04-AC02 | A plataforma inicial possui escopo de suporte explicitamente definido |
| ARCH04-AC03 | Sofias Memory continua sendo serviço independente |
| ARCH04-AC04 | Estado operacional não depende da disponibilidade de provedores externos |
| ARCH04-AC05 | Falha de conectividade degrada apenas funcionalidades dependentes |
| ARCH04-AC06 | Encerramento e reinicialização preservam as garantias da ARCH-02 |
| ARCH04-AC07 | Fechar a interface não implica declarar automaticamente tarefas canceladas |
| ARCH04-AC08 | Core não disponibiliza interface pública privilegiada sem proteção |
| ARCH04-AC09 | Comunicação local não presume confiança apenas por utilizar loopback |
| ARCH04-AC10 | Atualização da aplicação não elimina silenciosamente dados operacionais |
| ARCH04-AC11 | Segredos e dados transitórios possuem tratamento adequado às suas finalidades |
| ARCH04-AC12 | Recursos de áudio respeitam permissões e dispositivos disponíveis |
| ARCH04-AC13 | Aplicação não exige execução permanente em background para validar o MVP |
| ARCH04-AC14 | Dependências de sistema operacional não contaminam desnecessariamente as regras universais do Core |
| ARCH04-AC15 | A arquitetura não exige infraestrutura cloud própria do JARVIS para operar suas funções locais |

**OPEN / DEFERRED:** versões Windows adicionais, linguagem/UI/banco (decididos posteriormente na ARCH-05 ou condicionados), transporte, serviço do SO, tray, Docker/WSL, execução offline completa, acesso remoto, multi-instalação, Linux/macOS, atualização automática e medidas mínimas de hardware.

---

# ARCH-05 — Technology Evaluation & Runtime Baseline

**Status:** APPROVED. **Referências:** ARCH-01–ARCH-04, CONTRACT-01–CONTRACT-07, SPEC-01–SPEC-11; OQ-03/04/08; CTR-R01–CTR-R05.

## 1. Critérios de decisão e evidência existente

A tecnologia deve sustentar desktop Windows local-first, IA, voice, tasks, execution control, durabilidade, segurança, mantenabilidade e interfaces modernas. A decisão considera opções reais: Python, TypeScript/Node.js, PHP/Laravel, Rust; SQLite, PostgreSQL, Redis; PySide6 Widgets, PySide6 + Qt WebEngine + Vue, Tauri + Vue + Python sidecar, Electron + Vue + Python.

Os repositórios independentes do proprietário (`kallbuloso/sofias_assistant` e `kallbuloso/sofias_memory`) fornecem **evidência de experiência e candidatos à reutilização**, não autorização para copiar integralmente arquitetura, backlog ou dependências. A avaliação inicial do Sofia's Assistant identificou módulos de conversação, execução, memória, persistência, IA, interface e composição; **conformidade real com os Contracts do JARVIS não foi demonstrada**.

## 2. Linguagem do Core

| Opção | Vantagens | Desvantagens | Decisão |
|---|---|---|---|
| **Python** | Ecossistema IA/voz/automação, componentes existentes candidatos, integração desktop | Distribuição/runtime e concorrência precisam de validação | **APROVADO como linguagem principal do Core** |
| TypeScript / Node.js | Ecossistema web e programação assíncrona | Reaproveitamento Python requer novas fronteiras ou reimplementação | Não escolhido para Core |
| PHP / Laravel | Produtividade e experiência do proprietário | Mais natural para aplicação web que para áudio/desktop nativos nesta proposta | Não escolhido para Core |
| Rust | Performance e segurança de memória | Custo de desenvolvimento e integração maior para MVP | Possível uso especializado futuro |

**Versão:** Python **3.13 é candidato inicial de validação**, **não** fixado definitivamente. O Sofia's Assistant declara Python 3.13/3.14 e baseline de desenvolvimento em 3.14; o Sofias Memory declara runtime Python 3.12 em seu projeto. **Não** sincronizar esses runtimes artificialmente: JARVIS consumirá Memory como serviço independente.

## 3. Persistência operacional

| Candidato | Avaliação |
|---|---|
| **SQLite** | **APROVADO para MVP**: embedded, transacional, sem servidor obrigatório no Windows single-owner |
| PostgreSQL | Excelente servidor relacional, porém operação adicional injustificada inicialmente |
| Redis | Pode ter outros usos, mas não é autoridade principal do estado durável |

SQLite precisa de acesso local adequado, estratégias de transação, concorrência, migrações, retenção, backup e testes da ARCH-02; **WAL não equivale a writers simultâneos irrestritos** nem autoriza usar a base como filesystem de rede distribuído. A aprovação de SQLite **não comprova** por si só os critérios de recuperação.

**SQLAlchemy 2 e Alembic**: **candidatos preferenciais para avaliação**, não adoção obrigatória sem validação. Não incorporar PostgreSQL/Neo4j internos do Sofias Memory ao banco operacional do JARVIS.

## 4. Interface — comparação

| Opção | Benefícios | Custos / riscos | Situação |
|---|---|---|---|
| A — PySide6 Widgets | UI nativa, integração Python direta, existência de projeto anterior | Personalização visual avançada pode ser custosa | Alternativa de menor risco |
| **B — PySide6 + Qt WebEngine + Vue 3/Vuetify 3** | Host Windows em Python + liberdade visual Vue | WebEngine, assets/build, runtime e ponte exigem testes | **Candidata preferencial, condicionada a prova técnica** |
| C — Tauri + Vue + Python Sidecar | Shell web e separação explícita | Complexidade Rust/Tauri, supervisão e distribuição | Alternativa viável, não selecionada |
| D — Electron + Vue + Python | Tooling web maduro | Chromium/Node e coordenação adicional | Alternativa viável, não selecionada |

**Decisão aprovada:** priorizar **prova técnica curta** de PySide6 (desktop host) + **Vue 3/Vuetify 3** (interface embarcada). **Ainda não é frontend definitivo**. O **Qt WebChannel** é candidato de comunicação in-process/bridge, e não protocolo irrevogável; Qt WebEngine precisa validar recursos, lifecycle e superfície de segurança.

### 4.1. Referência de composição candidata

```text
frontend/ (Vue 3 + Vuetify 3)
      ↕ comandos/eventos com validação
Qt WebChannel (candidato)
      ↕
PySide6 Desktop Host — janela / áudio / recursos Windows
      ↕
Python JARVIS Core — autoridade, tasks, policy, execution
      ↕
SQLite — Operational State + Execution Journal
      ↕ via adapters
Sofias Memory / AI / Voice / External Services
```

A bridge não pode expor invocação genérica de métodos Python arbitrários, acesso direto a secrets, banco ou execução privilegiada. Deve respeitar CONTRACT-06; o Core jamais dependerá de classes Vue/PySide6 no domínio universal.

## 5. Comunicação interna

Com interface embarcada, avaliar `Qt WebChannel` **sem obrigatoriedade de servidor HTTP local**. Comandos de exemplo `sendMessage`, `getTasks`, `decideConfirmation`, `startVoiceSession`, `getConnections` são ilustrativos — não endpoints aprovados. Core valida entrada, mantém estado canônico e impede UI de executar ferramentas por conta própria.

Se no futuro for necessária fronteira entre processos, deverá ser escolhido transporte autenticado apropriado; não definir IPC/HTTP/WebSocket agora apenas por hábito.

## 6. Reutilização seletiva

| Área do Sofia's Assistant a auditar | Candidato / cautela |
|---|---|
| `conversation/` | Lifecycle, correlação de turnos, histórico |
| `ai/` | Provider adapters, streaming e roteamento |
| `execution/` | Policy, dispatcher, task journal, recuperação e bypass |
| `persistence/` | SQLite, transações, migrations |
| `memory/` | Portas e adapter para Sofias Memory conforme CONTRACT-02/03 |
| `client_app/` | Comportamentos visuais e voice já demonstrados |
| `client_boundary/` | **Não** importar automaticamente servidor HTTP legado |
| `host/` | Inicialização, encerramento, composição |

Regra: **reaproveitar componentes ou padrões compatíveis após avaliação funcional, de segurança, dependências e licenças; não incorporar o Sofia's Assistant como dependência operacional nem copiar o projeto inteiro por renomeação**. JARVIS permanece novo produto, com baseline independente.

O Sofias Memory será acessado por API de serviço conforme CONTRACT-02/03, não por modelos ORM internos ou seu runtime Python. Compatibilidade real: `CTR-R04` / `ARCH-R04`.

## 7. Stack candidata e estado da decisão

| Camada | Opção | Estado |
|---|---|---|
| Core | **Python** | **APPROVED** |
| Versão Core | Python **3.13** | **CANDIDATE / validação pendente** |
| Organização | Modular Monolith | **APPROVED** na ARCH-01 |
| Banco operacional | **SQLite** | **APPROVED** para MVP |
| ORM / migrations | SQLAlchemy 2 + Alembic | **CANDIDATE** |
| Desktop host | PySide6 | **PREFERRED CANDIDATE** |
| UI | Vue 3 + Vuetify 3 embarcados | **PREFERRED CANDIDATE, condicionado à prova técnica** |
| Ponte UI/host | Qt WebChannel | **CANDIDATE** |
| Sofias Memory | API pública do serviço separado | Boundary aprovado; compatibilidade pendente |
| AI | Provider Adapters | Contrato aprovado; provedores não escolhidos |
| Voice | Voice Adapters STT/TTS/Realtime | Contrato aprovado; provedores não escolhidos |
| Secrets | Mecanismo protegido apropriado para Windows | **OPEN** |
| Distribuição | Fonte para desenvolvimento inicial | **CANDIDATE**; distribuição final **OPEN** |
| Redis / RabbitMQ / backend Laravel / Node operacional | Não introduzir sem necessidade | Não exigidos no MVP |

Node.js poderá ser ferramenta de **build** do frontend Vue, caso aprovado; não é necessariamente runtime de servidor do JARVIS.

## 8. Prova técnica exigida para a interface

Antes da decisão definitiva de frontend, uma prova pequena e descartável deverá demonstrar:

1. Janela PySide6 renderizando Vue 3.
2. Comando Vue → Core Python.
3. Streaming Core → Vue sem duplicação e sem bloquear interface.
4. Confirmação apresentada no frontend e **validada no Core** (sem execução direta pelo JavaScript).
5. Captura e interrupção de áudio funcional.
6. Encerramento correto, sem processos ou recursos abandonados.
7. Persistência SQLite e recuperação de conversa após restart.

Observar complexidade, memória, eventos, comportamento em falhas e integridade da fronteira. Pode usar mocks como prova técnica, mas isso **não** substitui integrações reais do MVP. O ensaio ainda será planejado em Slice posterior aprovado; nenhuma implementação foi autorizada por esta decisão.

## 9. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH05-AC01 | Linguagem do Core suporta os requisitos de IA, tarefas, voz e ferramentas |
| ARCH05-AC02 | Persistência selecionada atende às garantias transacionais da ARCH-02 |
| ARCH05-AC03 | O JARVIS não depende do runtime Python interno do Sofias Memory |
| ARCH05-AC04 | Interface não recebe acesso direto a credenciais ou dados operacionais privilegiados |
| ARCH05-AC05 | Streaming de mensagens e atualização de tarefas podem ocorrer sem bloquear a interface |
| ARCH05-AC06 | A tecnologia visual selecionada preserva as garantias do CONTRACT-06 |
| ARCH05-AC07 | Captura e reprodução de áudio funcionam no Windows inicial |
| ARCH05-AC08 | O frontend não exige um backend HTTP separado sem necessidade comprovada |
| ARCH05-AC09 | Reutilização do Sofia's Assistant ocorre somente após auditoria de compatibilidade |
| ARCH05-AC10 | Nenhum componente interno do Sofia's Assistant vira dependência obrigatória do JARVIS |
| ARCH05-AC11 | Persistência operacional continua independente do Sofias Memory |
| ARCH05-AC12 | Escolhas de interface e comunicação são validadas antes de fixar a implementação definitiva |
| ARCH05-AC13 | A distribuição futura não é confundida com o fluxo inicial de desenvolvimento |
| ARCH05-AC14 | As escolhas não introduzem infraestrutura distribuída sem necessidade concreta |

**OPEN:** versão Python definitiva; tecnologias auxiliares; UI e bridge definitivas; instalador/distribuição; providers de IA/voz; segredo seguro; compatibilidade real com Memory. **Sem** implantação ou código de prova técnica autorizado nesta fase.

---
# ARCH-06 — Integration Architecture & Provider Lifecycle

**Status:** **APPROVED, com emenda de fallback opcional também aprovada.** **Referências:** ARCH-01–ARCH-05, CONTRACT-01–CONTRACT-07, SPEC-01/04/05/06/07/09/10/11.

## 1. Propósito

O JARVIS deverá descobrir, configurar, selecionar e utilizar providers independentes sem incorporar suas regras de negócio ao Core; manter distinção entre provider, conexão e capability; respeitar contratos e políticas; e observar falhas, resultados, custos e disponibilidade. Providers de IA e voz são mecanismos funcionais de inferência/áudio, não autoridades operacionais. Sofias Memory é uma dependência funcional com contratos específicos, não uma tool genérica.

**Decisão:** **Contract-Driven Provider Architecture + Explicit Provider Registry + Capability-Aware Selection + Centralized Execution Control**, com **Optional Capability-Aware Provider Fallback** previsto arquiteturalmente e implementação automática completa **DEFERRED**.

## 2. Visão lógica

```text
JARVIS Core (conversation / tasks / policy / execution)
           │
           ▼
Integration Coordination
  ├─ Provider Registry
  ├─ Capability Discovery / Selection
  └─ Connection Manager
           │ contract ports
           ├─ Capability Port            CONTRACT-01
           ├─ Cognitive / Knowledge      CONTRACT-02 / 03
           ├─ Inference Port             CONTRACT-04
           ├─ Voice Port                 CONTRACT-05
           └─ Connection Port            CONTRACT-07
                     │ adapters
                     ├─ Sofias Memory (service)
                     ├─ AI Providers
                     ├─ Voice Providers
                     └─ External APIs / Tools

Interaction Surface ↔ Application Core: CONTRACT-06
(não precisa atravessar o Provider Registry)
```

O desenho não exige processos separados, nem um protocolo único para todas as fronteiras.

## 3. Explicit Provider Registry

O Core mantém registro **explícito** de adapters confiáveis conhecidos na composição inicial do MVP. Isso não aprova marketplace, download de plugins, descoberta remota ou importação de executáveis arbitrários. O Registry pode descrever `provider_id`, `provider_type`, `contract_versions`, `capabilities`, `configuration_requirements`, `operational_constraints`, `availability` conhecida e `supported_features`. Tais nomes são campos conceituais, não schemas impostos.

**Register ≠ Configure ≠ Enable ≠ Authorize ≠ Execute.** O registro de um provider ou descoberta de sua capability nunca constitui grant. O Core verifica compatibilidade de contrato e não habilita silenciosamente funcionalidade incompatível.

## 4. Provider, Connection, Capability — identidades separadas

| Conceito | Definição |
|---|---|
| Provider | Implementação que oferece um conjunto de operações ou recursos |
| Connection | Configuração, credenciais, conta e identidade externa do proprietário |
| Capability | Operação específica declarada, sujeita à elegibilidade efetiva |

```text
Email Provider (exemplo; NÃO escolhido para o MVP)
  ├─ Connection A: conta pessoal
  │    ├─ ReadMessages
  │    └─ SendMessage
  └─ Connection B: conta profissional
       ├─ ReadMessages
       └─ SendMessage — sem permissão externa confirmada
```

A existência da capability no provider não significa elegibilidade em todas as contas. Múltiplas conexões preservam escopo e segredos isolados; ambiguidade material de conta/destino requer esclarecimento antes de efeito externo.

## 5. Lifecycle e observações de estado

Provider Lifecycle diz respeito à implementação/compatibilidade. Connection Lifecycle diz respeito às condições **independentes** `installed`, `configured`, `enabled`, `authorized` (permissões externas e autoridade operacional consideradas separadamente), `available`. Estado observado de disponibilidade não garante sucesso futuro. Um provider pode estar registrado sem configuração; conexão habilitada pode estar sem credenciais válidas; remover vínculo local não garante revogação remota. Todas as operações respeitam CONTRACT-07.

| Situação | Consequência |
|---|---|
| Registered, not configured | Capabilities conhecidas, sem utilização dependente de conexão ausente |
| Disabled connection | Impede novas admissões |
| Credential expired | Reautenticação/renovação compatível, sem supor permissão |
| Service unavailable | Limitação explicitada; nenhuma resposta externa inventada |
| Contract incompatible | Recurso dependente indisponível |
| Multiple accounts | Resolução por contexto ou esclarecimento |
| Removed connection | Uso local bloqueado; dados externos não são apagados por inferência |

## 6. Seleção de capacidades e admissão

```text
Pedido / Contexto
    ↓
Semantic Discovery (LLM pode sugerir)
    ↓
Capability Contract / Effect Validation
    ↓
Connection Selection (desambiguação quando necessária)
    ↓
Policy / Confirmation / Budget / Availability
    ↓
Durable Dispatch Attempt (ARCH-02)
    ↓
Protected Execution Gateway (ARCH-03)
    ↓
Provider Adapter / Result Evidence
```

O adapter não recebe invocação protegida apenas porque foi escolhido semanticamente. Seleção contextual pode ser feita com auxílio de IA, mas validação e política são determinísticas naquilo que exige autoridade. Se não houver capacidade pertinente, informar limitação, não simular execução.

## 7. AI Providers

O CONTRACT-04 define capabilities de inferência, streaming, saída estruturada, tool proposals, custo e contexto. O catálogo deve indicar suporte **real**. Seleção de modelo considera requisitos, capacidade, disponibilidade, privacidade e orçamento. O MVP não precisa de roteador sofisticado nem múltiplos provedores obrigatórios; modelo/provider configurado pode ser selecionado explicitamente.

**Ferramentas nativas de IA com efeitos externos protegidos não podem contornar o Execution Gateway.** Uma chamada hospedada pelo provider que dispense o JARVIS de verificar autorização não atende automaticamente aos Contracts.

Fallback entre modelos só pode ser elegível quando respeitar privacidade, funcionalidade, custos e limites, com semântica de cancelamento e streaming segura (ver §16).

## 8. Voice Providers

O Voice Runtime coordena STT, TTS e/ou Realtime conforme os recursos suportados (CONTRACT-05). Um provider pode suportar mais de uma função, mas não se presume equivalência entre elas. Voz e texto compartilham a mesma **conversa canônica**; sessão de áudio não é nova conversa, transcrição provisória não é comando executável, texto final de STT não é autorização humana verificada. Parar reprodução de áudio não cancela operação externa ou task.

Captura respeita microfone e permissões da plataforma. A falha de voz não impede interação por texto. No fallback Realtime, transferência de sessão e sua continuidade **não** podem ser presumidas.

## 9. Sofias Memory — adapter dedicado

```text
JARVIS
  ├─ Cognitive Memory Adapter → CONTRACT-02
  └─ Knowledge Retrieval Adapter → CONTRACT-03
                                  ↓
                        Sofias Memory API pública
```

O serviço não é ferramenta genérica e não recebe o controle de tasks, execução, grants, policy ou audit operacional. A integração deverá mapear as operações aprovadas à API **real**, auditar disponibilidade, escopo, proveniência, forget e idempotência, sem assumir que toda operação conceitual está implementada exatamente com o nome previsto. Se houver incompatibilidade, registrar finding e decidir correção explicitamente; **não modificar Sofias Memory preventivamente**. Indisponibilidade degrada funções de memória e conhecimento, sem invalidar funções independentes do Core.

## 10. Error semantics e resultados

| Categoria | Tratamento |
|---|---|
| Invalid configuration | Corrigir configuração, não habilitar acesso incorreto |
| Authentication required / expired | Reautenticação ou renovação suportada |
| External permission insufficient | Bloquear capability dependente |
| Provider unavailable | Degradar função dependente |
| Budget / resource limit | Aplicar limite da SPEC-11; sem presumir consumo zero desconhecido |
| Unsupported operation | Informar lacuna funcional |
| Partial result | Preservar partes comprovadas e limitações |
| UNKNOWN | Não presumir falha/sucesso e não repetir alteração insegura |
| Contract incompatible | Não executar recurso incompatível silenciosamente |

Erros brutos podem ser preservados sanitizados para diagnóstico, mas UI/estado canônico utilizam semântica normalizada aprovada. Timeout significa que o JARVIS deixou de esperar: **não** prova que o provider deixou de processar.

## 11. Retries, idempotência e timeouts

Consultas poderão ser repetidas **quando seguro** segundo operação, privacidade, custos e capacidades; uma READ também pode consumir orçamento e expor dados. Escritas ou operações críticas sujeitas a resultado desconhecido **não** são repetidas automaticamente sem evidência adequada de segurança. Idempotência declarada exige comprovação de comportamento real; usar `operation_id` local não torna provider idempotente.

## 12. Transportes e protocolos

A escolha de HTTP, WebSocket, SDK, IPC ou MCP depende da fronteira real. Não impor MCP universalmente nem hospedar servidor MCP no JARVIS apenas como atributo de marketing. Sofias Memory é acessado por interface pública suportada; AI/Voice usam adapters apropriados. Vue ↔ PySide6 pode utilizar Qt WebChannel após prova da ARCH-05; isso não é dependência universal de todo Core.

## 13. Startup e degradação

Sequência conceitual: iniciar Core e recuperar estado operacional; registrar adapters confiáveis; recuperar configurações/conexões; consultar disponibilidade/permissões externas quando necessário/possível; oferecer apenas capacidades elegíveis. **Não exigir disponibilidade simultânea** de todos os providers para iniciar o Core. Falha de persistência operacional sujeita-se à ARCH-02, e falhas externas degradam exclusivamente funcionalidades dependentes.

## 14. Observabilidade e segurança

Correlacionar `Task/Conversation → Capability → Provider → Connection → Operation Attempt → Result`. Registrar consumo de IA/voz observado, estimado ou desconhecido. Não expor tokens, áudio bruto ou conteúdo sensível desnecessário. Não permitir que adapters controlem o Execution Journal; auditabilidade operacional permanece no JARVIS. Plugins executáveis desconhecidos precisam respeitar isolamento aprovado na ARCH-03.

## 15. Extensibilidade de MVP e non-goals

O MVP deve demonstrar **dois domínios externos reais** e **uma escrita externa autorizada, efetiva e verificável** usando adapters confiáveis. Não exige marketplace, sistema de instalação dinâmica de código executável, pesquisa autônoma de plugins, skill evolution, criação automática de adapters, sandbox universal ou um motor genérico de workflows. `FR-025` (plugin discovery supervisionado) permanece SHOULD pós-MVP.

## 16. Emenda aprovada — Optional Capability-Aware Provider Fallback

**Status da emenda:** APPROVED. **Implementação automática completa:** **DEFERRED (pós-MVP)**. A arquitetura **permite** associar alternatives a uma capability; **não obriga** configurar mais de um provider ou modelo para utilizar o JARVIS.

### 16.1. Semântica

O usuário pode configurar provider/modelo primário e alternativas elegíveis. Quando o primário falhar de forma apropriada à tentativa, o JARVIS **poderá**, após implementação futura da política, avaliar alternativa antes de trocar. Fallback não é garantia universal de continuidade: pode não haver provider elegível, conexão válida, custo aceitável, consentimento/privacidade compatíveis, nem estado transferível.

```text
Provider principal
     ├── Resultado válido → usar normalmente
     └── Falha elegível
            ↓
     Fallback Eligibility Check
      capabilities / privacy / authority / costs / prior state
            ↓
     Provider alternativo configurado e elegível
            ↓
     Resultado com proveniência ou falha explícita
```

### 16.2. Matriz por categoria

| Categoria | Direção aprovada |
|---|---|
| AI / LLM | Fallback potencialmente útil se modelo suporta todas as capacidades exigidas |
| STT | Alternância possível com permissões e privacidade compatíveis |
| TTS | Alternância possível; mudança de voz/qualidade relevante deve ser informável |
| Realtime Voice | Pode não haver transferência de sessão, estado ou turno em andamento |
| Search / READ Tools | Condicional: fontes, custo, escopo e semântica podem diferir |
| WRITE / CRITICAL Tools | **Não realizar fallback automático inseguro**, especialmente após resultado UNKNOWN |
| Sofias Memory | **Não substituir automaticamente** a autoridade cognitiva definida do produto |

### 16.3. Restrições de elegibilidade

1. **Configuração opcional:** nenhuma dependência de múltiplos providers no MVP.
2. **Prioridade explícita:** respeitar escolhas/preferências do proprietário quando houver alternativas configuradas.
3. **Compatibilidade funcional real:** não trocar streaming/structured output/tool capability por serviço incapaz de cumprir requisitos.
4. **Privacidade/localidade:** restrição local não pode causar envio automático de dados para cloud.
5. **Custo:** considerar limites, gastos já incorridos e incerteza de medição (SPEC-11).
6. **Streaming e efeitos parciais:** fragmentos de resposta anterior não podem ser apresentados como resposta única contínua e coerente do novo provider quando houver troca; interrupção e reconstrução precisam ser explícitas.
7. **Authority:** provider alternativo não amplia grants nem contorna Execution Gateway.
8. **Transparência:** permitir identificar provider efetivamente utilizado e eventual troca.
9. **Escrita incerta:** não substituir um executor por outro para repetir possível efeito externo cujo resultado é UNKNOWN.

### 16.4. Horizonte de implementação

**MVP:** preservar arquitetura multi-provider e capacidade de seleção/registro; fallback automático não integra aceite obrigatório.

**Pós-MVP:** políticas completas de troca automática, prioridades, falhas elegíveis, mecanismos de proteção contra falhas recorrentes e validações de sessão/stream, quando justificadas por necessidades reais. Não instalar agora circuit breakers, health monitors sofisticados ou roteamento entre dezenas de providers por antecipação.

## 17. Critérios de validação

| ID | Critério aprovado |
|---|---|
| ARCH06-AC01 | Providers podem ser registrados sem incorporar regras particulares do serviço ao Core |
| ARCH06-AC02 | Registry distingue providers, conexões e capabilities |
| ARCH06-AC03 | Capacidade declarada não é tratada como autorização |
| ARCH06-AC04 | Provider incompatível não é utilizado silenciosamente |
| ARCH06-AC05 | Múltiplas conexões preservam identidades e escopos separados |
| ARCH06-AC06 | Seleção de ferramentas considera contexto, disponibilidade e autoridade |
| ARCH06-AC07 | Conta externa ambígua exige esclarecimento quando material |
| ARCH06-AC08 | Toda execução protegida respeita o Execution Gateway |
| ARCH06-AC09 | Ferramentas nativas de IA não contornam os controles do JARVIS |
| ARCH06-AC10 | Adapters de voz preservam o contexto conversacional canônico |
| ARCH06-AC11 | Sofias Memory é integrado por seus contratos próprios |
| ARCH06-AC12 | Indisponibilidade de um provider não inutiliza funcionalidades independentes |
| ARCH06-AC13 | Timeouts e resultados desconhecidos preservam sua semântica |
| ARCH06-AC14 | Retentativas de efeitos externos obedecem às garantias de recuperação |
| ARCH06-AC15 | Credenciais são acessadas exclusivamente pelos mecanismos autorizados |
| ARCH06-AC16 | Invocações e resultados possuem correlação observável |
| ARCH06-AC17 | Novas integrações compatíveis não exigem modificação das regras de negócio do Core |
| ARCH06-AC18 | Pelo menos dois domínios externos reais podem ser validados no MVP |
| ARCH06-AC19 | Uma operação externa supervisionada produz resultado efetivo e verificável |
| ARCH06-AC20 | Inicialização do Core não depende de disponibilidade simultânea de todos os providers |
| **ARCH06-AC21** | A arquitetura permite associar providers alternativos a capacidades compatíveis, sem torná-los obrigatórios |
| **ARCH06-AC22** | A elegibilidade de uma alternativa respeita capacidades, privacidade, autoridade e limites de recursos |
| **ARCH06-AC23** | A possibilidade de fallback não autoriza repetir operações externas de resultado desconhecido |
| **ARCH06-AC24** | O fallback automático completo permanece DEFERRED e não bloqueia a aprovação do MVP |

**OPEN / DEFERRED:** dois domínios externos concretos (`OQ-01`); AI/Voice providers e modelos; protocolos específicos; auditoria real Sofias Memory (`CTR-R04`); fallback automático completo, marketplace, descoberta autônoma e execução de plugins não confiáveis até comprovar isolamento.

---
# Revisão final de consistência — Fase 06 (APPROVED)

**Status da revisão:** APPROVED pelo proprietário. **Resultado:** encerramento autorizado da Fase 06, sem implementação nem mudança de baseline anterior.

## R.1. Inventário de decisões e critérios

| Decisão | Descrição | Critérios | Status |
|---|---|---:|---|
| ARCH-01 | Modular Monolith + Ports & Adapters | 10 | APPROVED |
| ARCH-02 | Transactional State + Durable Execution Journal + Conservative Recovery | 14 | APPROVED |
| ARCH-03 | Policy Enforcement + Protected Execution Gateway + isolamento proporcional | 18 | APPROVED |
| ARCH-04 | Local-first Windows Desktop + serviços externos independentes | 15 | APPROVED |
| ARCH-05 | Python + SQLite; PySide6/Vue candidato condicionado | 14 | APPROVED |
| ARCH-06 | Contract-Driven Providers + fallback opcional DEFERRED | 24 | APPROVED |
| **Total** | **Seis decisões** | **95** | **APPROVED** |

Os **95 critérios** são condições de verificação arquitetural, **não** 95 testes executados. Complementam os **122 critérios de aceitação contratuais** da Fase 05, também ainda sujeitos a validação concreta.

## R.2. Consistência do ownership e trust boundaries

| Invariante | Resultado da revisão |
|---|---|
| Core independente da UI | Consistente: a UI transmite comandos, não mantém autoridade operacional |
| Sofias Memory independente | Consistente: memória/knowledge não executam |
| Estado operacional separado da memória cognitiva | Consistente: SQLite do JARVIS versus serviço Sofias Memory |
| Persistência antes de despacho protegido | Consistente: ARCH-02 aplica-se a ARCH-03/06 |
| Autoridade do JARVIS sobre efeitos | Consistente: IA, adapters e plugins não ampliam privilégios |
| Registry, Connections e Capabilities distintos | Consistente: ARCH-06 observa CONTRACT-01/07 |
| Extensão desconhecida não recebe execução privilegiada | Consistente: isolamento efetivo exigido |
| Fallback sem bypass e sem retry inseguro | Consistente: ARCH-06 emenda respeita ARCH-02/03 |
| Windows inicial e suporte futuro não assumido | Consistente: ARCH-04/05 |
| Desenvolvimento por Slices verificáveis | Consistente com baselines anteriores |

**Conclusão:** nenhuma contradição estrutural bloqueadora foi identificada na revisão aprovada. Isso **não** é certificação de segurança ou prova de implementação.

## R.3. Fluxos transversais

### R.3.1. Conversa por texto ou voz

`Input → Interaction Surface → Voice Adapter (se áudio) → Conversation/Context → AI Adapter → resposta/stream → Conversation State → UI`.

Garantias: voz e texto na conversa canônica; transcrição provisória não executa; modelo não controla política; persistência e indicação de falha seguem Specs/Contracts. Recursos de voz podem estar indisponíveis sem bloquear texto.

### R.3.2. Ação externa protegida

`User → Conversation/Planner → Capability Registry → Connection → Policy → Confirmation (se exigida) → Durable Attempt → Execution Gateway → External Provider → Result Evidence → Task/Journal/UI`.

Garantias: interface não despacha; timeout não prova falha; UNKNOWN não habilita retry; privacidade/custo/credenciais são aplicados; conta e autorização permanecem vinculadas à operação material.

### R.3.3. Memória e conhecimento

`Conversation/Task Context → Memory/Knowledge Adapter → Sofias Memory API → Result + Provenance → Context/Response`.

Garantias: documento não concede grant; memória escrita automaticamente **desabilitada por padrão no MVP** e registro explícito requer confirmação aplicável; forget não é exclusão universal; indisponibilidade não destrói estado operacional.

### R.3.4. Recuperação após falha

`Startup → Recover Operational State → Inspect Attempts → Revalidate Dependencies/Authorization → Resume if safe OR WAITING/review → UI snapshot`.

Garantias: `RUNNING` persistido não prova trabalho ativo; decisões humanas e efeitos prévios não são repetidos; reconciliação de resultados só mediante evidência.

### R.3.5. Fallback opcional de IA/voz

`Primary Provider Failure → Eligibility (capability/privacy/cost/authority/prior state) → Configured Alternative, if eligible → Report provenance`.

Garantias: não obrigatório no MVP; fallback automático completo pós-MVP; não substitui Sofias Memory nem repete WRITE/CRITICAL de resultado UNKNOWN.

## R.4. Pendências arquiteturais rastreadas

| ID | Ponto aprovado como pendente | Severidade | Resolução necessária |
|---|---|---|---|
| **ARCH-R01** | Validação PySide6 + Vue/Vuetify + Qt WebChannel | IMPORTANT | Prova técnica antes de fixar UI definitiva |
| **ARCH-R02** | Versão exata do Python e dependências | IMPORTANT | Matriz de compatibilidade e ambiente reprodutível |
| **ARCH-R03** | Proteção de credenciais no Windows | IMPORTANT | Escolher e validar mecanismo antes de integrar contas reais |
| **ARCH-R04** | Compatibilidade efetiva com Sofias Memory | IMPORTANT | Auditar API pública contra CONTRACT-02/03 |
| **ARCH-R05** | Escolha de dois domínios externos reais do MVP | IMPORTANT | Definir antes dos Slices que dependem dessas integrações |
| **ARCH-R06** | Proteção de dados, backups e retenção | IMPORTANT | Resolver antes de implementações afetadas |
| **ARCH-R07** | Confirmações por voz de operações protegidas | IMPORTANT | Definir salvaguardas antes de habilitar aprovações por voz |
| **ARCH-R08** | Fallback automático de providers | DEFERRED | Evolução pós-MVP, não bloquear aceite |

**IMPORTANT** não implica que a Fase 06 esteja bloqueada; implica trabalho verificável antes do Slice dependente. Itens de segurança/autoridade podem se tornar BLOCKER para implementação/validação concreta se não resolvidos.

### R.4.1. Correlação com pendências anteriores

| Pendência anterior | Continuidade |
|---|---|
| CTR-R01 — payloads e schemas físicos | Technical design / implementation conforme fronteira |
| CTR-R02 — correlação, idempotência, concorrência | ARCH-02/03 exigem garantias; mecanismos físicos ainda pendentes |
| CTR-R03 — versionamento e erros reais | ARCH-06 + validação de adapters |
| CTR-R04 — Sofias Memory real | ARCH-R04; auditoria da API |
| CTR-R05 — segurança/isolation de providers | ARCH-03; concretização antes de código não confiável |
| SPEC-R01 — retenção e backup | ARCH-R06 |
| SPEC-R02 — confirmações por voz | ARCH-R07 |
| SPEC-R03 — custo de providers | SPEC-11; medir/estimar/desconhecido e verificar nas integrações |
| SPEC-R04 — API Sofias Memory | ARCH-R04 |
| PRD OQ-01 — duas integrações | ARCH-R05 |
| PRD OQ-03 — frontend | ARCH-R01, candidato preferido ainda não fixado |
| PRD OQ-04 — providers IA/voz | Seleção real pendente |
| PRD OQ-08 — reuse Sofia's Assistant | Auditoria seletiva pendente |

A questão `OQ-06` já foi classificada na Fase 05 como **RESOLVED AT CONTRACT BOUNDARY LEVEL**, permanecendo representação interna e schemas físicos para Architecture/technical design. Este documento confirma essa distinção; não inventa contratos internos adicionais.

## R.5. Segurança: três verificações de maior risco

1. **Bridge Vue/Python:** não expor execução Python genérica nem segredos no JavaScript; aplicar CONTRACT-06 e validações do Core.
2. **SQLite e efeitos externos:** commit local não equivale a commit remoto; preservar intenção anterior ao despacho, estados UNKNOWN e reconciliação conservadora.
3. **Adapters / plugins:** package Python e processo separado não bastam como sandbox. Sem isolamento efetivo, não executar código não confiável com privilégios irrestritos.

Nenhuma dessas garantias é considerada validada por ter sido descrita; elas exigem testes técnicos e humanos apropriados quando implementadas.

## R.6. Decisões para a etapa de ADRs

Temas identificados para **avaliação de registro**, sem obrigar um documento por item:

| Tema | Por que avaliar ADR |
|---|---|
| Modular Monolith e ownership | Justificar topologia e consequências duráveis |
| SQLite para Operational Persistence | Limitações de concorrência, durability, segurança e manutenção |
| Python Runtime | Razões e trade-offs da linguagem principal |
| Protected Execution Boundary | Isolamento, autoridade e garantias de segurança |
| Interface desktop e bridge | Registrar **após prova técnica**, não como escolha definitiva hoje |
| Provider Registry / Adapter model | Estabilidade de boundaries e alternativas |
| Fallback automático | **DEFERRED**; não obrigar ADR de implementação agora |

ADRs são registros decisórios; não devem duplicar os sete Contracts nem reescrever toda esta Architecture. Outros ADRs só serão propostos quando houver decisão durável real a registrar.

## R.7. Scope check — MVP versus futuro

| Item | Status consolidado |
|---|---|
| Um proprietário por instalação | MVP APPROVED |
| Texto + voz, uma conversa e histórico persistente | MVP obrigatório |
| Sofias Memory cognitivo/documental independente | MVP obrigatório |
| Dois domínios externos reais | MVP obrigatório; nomes **OPEN** |
| Uma escrita/alteração externa supervisionada e real | MVP obrigatório |
| Task lifecycle e recuperação segura | MVP obrigatório |
| Python Core | ARCH-05 APPROVED |
| SQLite como autoridade operacional | ARCH-05 APPROVED |
| Windows 11 como primeira plataforma de validação | ARCH-04 APPROVED |
| PySide6 + Vue/Vuetify + Qt WebChannel | **PREFERRED CANDIDATE**, depende de prova |
| Python 3.13 | **CANDIDATE**, versão definitiva aberta |
| SQLAlchemy 2 + Alembic | **CANDIDATE** |
| IA e voz: providers concretos | OPEN |
| Secrets no Windows | OPEN; validação de segurança obrigatória |
| Auto-write de memória cognitiva | **OFF por padrão no MVP** |
| Fallback automático completo | DEFERRED |
| Marketplace, agente-builder, skills evolution, multiagente avançado | FUTURE / DEFERRED |
| Execução permanente em background | Não obrigatória no MVP |
| Cloud Core próprio e sincronização multi-instalação | Não exigidos no MVP |
| Multiusuário e multiplataforma imediata | FUTURE / não obrigatórios |
| Acesso público remoto ao Core | Não aprovado por padrão |

Não fixar prematuramente licença do JARVIS, instalador final, formato físico do banco, protocolo universal MCP ou modelo específico por inferência. A PolyForm do Sofia's Assistant não define automaticamente a licença do JARVIS.

## R.8. Exit Criteria e resultado

| Condição de Architecture | Resultado |
|---|---|
| Componentes mínimos e responsabilidades | Atendidos conceitualmente |
| Ownership e trust boundaries | Aprovados |
| Data flow conversacional e operacional | Aprovado conceitualmente |
| Persistência e recuperação | Garantias arquiteturais aprovadas; implementação pendente |
| Integrações e contratos | Fronteiras aprovadas, compatibilidade efetiva a auditar |
| Runtime / deployment | Local-first Windows inicial aprovado |
| Tecnologia principal | Python/SQLite aprovados; interface candidata |
| Decisões duráveis para ADR | Identificadas |
| Pendências e decisões futuras | Rastreáveis em ARCH-R01–R08 |
| Revisão final pelo proprietário | **APPROVED** |

**Conclusão aprovada:** Fase 06 — Architecture encerrada, sem blocker estrutural identificado. Não significa que a interface candidata, a segurança dos plugins, os providers de IA/voz ou a compatibilidade com o Sofias Memory já tenham sido validados empiricamente.

## R.9. Project State após a Fase 06

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | Architecture encerrada — próxima fase **ADRs** |
| **Current role** | Software Architect |
| **Approved** | Discovery; Product Definition PD-01–09; PRD-01–11; Specs SPEC-01–12; Contracts CONTRACT-01–07; Architecture ARCH-01–06 e revisão final |
| **Current artifact** | `docs/product-manager/06-JARVIS-Architecture.md` |
| **Open** | ARCH-R01–ARCH-R07; versões e tecnologias condicionadas; provedores reais; mecanismos de credenciais; domínio externo escolhido; detalhes físicos de garantias |
| **Deferred** | ARCH-R08 fallback automático; demais funcionalidades futuras do PRD/PD-09 |
| **Current Slice** | Nenhum Slice de implementação autorizado |
| **Next legitimate step** | Salvar este documento no repositório; iniciar Fase 07 — ADRs com decisões duráveis existentes e deixar candidatos ainda não validados condicionados |

**Controle de mudanças:** baseline aprovado permanece normativo. Se uma avaliação técnica demonstrar incompatibilidade com os critérios aprovados, registrar o problema e obter decisão explícita antes de alterar comportamento, autoridade, contrato, escopo ou arquitetura durável. Alterações locais reversíveis de implementação podem ser decididas nos Slices correspondentes.

---

*Fim do JARVIS — Architecture (Fase 06, APPROVED).*

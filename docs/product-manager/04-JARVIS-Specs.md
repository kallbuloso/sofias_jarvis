# JARVIS — Especificações Funcionais (Specs)

| Campo | Valor |
|---|---|
| **Projeto** | JARVIS — assistente pessoal universal |
| **Fase** | 04 — Specs |
| **Status** | **APPROVED** — SPEC-01 a SPEC-11 e revisão final SPEC-12 aprovadas individualmente |
| **Data da consolidação** | 2026-10-29 |
| **Responsável pela aprovação** | Proprietário do produto |
| **Papel** | Product Engineer / Software Architect |
| **Baselines anteriores** | `docs/product-manager/01-JARVIS-Discovery.md`, `02-JARVIS-Product-Definition.md`, `03-JARVIS-PRD.md` |
| **Destino no repositório** | `docs/product-manager/04-JARVIS-Specs.md` |
| **Natureza** | Especificação normativa de **comportamento**; não define APIs, schemas, classes, frameworks ou arquitetura |

> **Integridade do baseline:** este documento consolida **11 Specs normativas aprovadas**, contendo **136 critérios de aceitação**, e a revisão de encerramento **SPEC-12**. Preserva condições, falhas, exceções, limites e questões adiadas, sem transformar alternativas ilustrativas em escolhas técnicas. Os requisitos do PRD continuam vigentes; uma Spec detalha o comportamento e **não** pode mudar silenciosamente um requisito anterior.

## 0. Orientações gerais de leitura

- **MUST / obrigatório:** comportamento que a implementação do MVP precisa atender no escopo aplicável.
- **APPROVED:** decisão funcional aprovada pelo proprietário; não implica implementação.
- **OPEN / DEFERRED:** decisão deliberadamente mantida para Specs complementares, Contracts ou Architecture, antes da implementação que dela dependa.
- **Exemplos:** serviços e nomes como GitHub, e-mail, calendário e assistência técnica apenas ilustram situações, sem escolher as duas integrações reais do MVP.
- **Nomes conceituais de estados:** `PREPARED`, `RUNNING`, `WAITING`, etc. ilustram comportamentos e **não** fixam enum, banco, API ou nomenclatura de código.
- **Critérios `Sxx-ACyy`:** verificações específicas de cada Spec; complementam e não substituem os critérios globais `AC-001–AC-008` do PRD.

### 0.1 Fronteiras invariantes do projeto

1. **JARVIS é um produto novo e independente de Sofia's Assistant**. A reutilização de componentes do outro repositório depende de auditoria e decisão posterior.
2. **Sofias Memory armazena/recupera memória cognitiva, conhecimento, proveniência e definições declarativas; não executa ferramentas, tarefas, scripts ou agentes.**
3. **JARVIS é a autoridade operacional** sobre conversas canônicas, contexto ativo, tarefas, integrações, grants, confirmações, execução, auditoria e recovery.
4. **Selecionar uma tool, considerar uma ação adequada ou recuperar uma memória nunca equivale a autorizar a execução**.
5. Estados e resultados precisam refletir **evidência observada**: `UNKNOWN` não é `SUCCESS`, e recuperar uma tarefa não equivale a repetir uma ação.
6. **MVP:** usuário único por instalação, múltiplas conexões desse proprietário, voz/texto unificados, Sofias Memory, pelo menos dois domínios externos reais, operação real supervisionada, tarefas persistentes e UI utilizável.
7. **FUTURE:** Agent Builder e Skill Evolution completos, Plugin Discovery amplo, autonomia progressiva, multiagente, desktop automation avançada, ambient context, Knowledge Galaxy 3D, multi-channel e multi-user; `FR-025` permanece SHOULD pós-MVP.

### 0.2 Índice de Specs

| Spec | Tema | Critérios |
|---|---|---:|
| SPEC-01 | Ciclo de vida da execução protegida | 8 |
| SPEC-02 | Ciclo de vida de tarefas e recuperação operacional | 11 |
| SPEC-03 | Gerenciamento de contexto e continuidade conversacional | 11 |
| SPEC-04 | Integração com Sofias Memory e semântica da memória | 11 |
| SPEC-05 | Descoberta e seleção contextual de capacidades | 13 |
| SPEC-06 | Ciclo de vida de integrações e conexões externas | 13 |
| SPEC-07 | Interação por voz e ciclo de vida de sessões de áudio | 13 |
| SPEC-08 | Interface de controle e visibilidade operacional | 15 |
| SPEC-09 | Planejamento, avaliação de decisões e adequação ao objetivo | 14 |
| SPEC-10 | Privacidade, retenção e política de persistência | 15 |
| SPEC-11 | Controle de consumo, orçamentos e limites operacionais | 12 |
| **TOTAL** | **11 Specs aprovadas** | **136** |

---

# SPEC-01 — Ciclo de Vida da Execução Protegida

**Status:** APPROVED  
**Requisitos relacionados:** FR-026–FR-035; FR-040; FR-046; NFR-001; NFR-004; NFR-007.

## 1. Purpose / Scope

Determinar o comportamento entre a preparação de uma operação de tool e a confirmação de seu resultado. Aplica-se a ações solicitadas pelo usuário diretamente e a operações originadas por tasks, agents, skills ou plugins. Nenhum desses atores possui rota paralela de execução ou concede a si mesmo autoridade.

**Fronteira:** escolher a ferramenta, avaliá-la como adequada e possuir credencial externa são condições distintas de **autorização efetiva para executar o efeito pretendido**.

## 2. Fluxo e condições conceituais

```text
PREPARED (operação, alvo, parâmetros e efeitos identificados)
  → AUTHORITY CHECK
     ├── PERMITTED ────────────────────────┐
     ├── WAITING (confirmação necessária) ──┤ após aprovação válida e revalidação
     └── DENIED → bloqueio; sem execução     │
                                            ↓
                                        EXECUTING
                                            ↓
                           SUCCESS | FAILED | UNKNOWN
```

Esse fluxo é conceitual: `PERMITTED`, `WAITING` e `DENIED` são decisões de autoridade; `SUCCESS`, `FAILED`, `UNKNOWN` são resultados operacionais. **Não** constituem necessariamente um único enum ou uma única máquina de estados técnica.

| Condição | Comportamento obrigatório |
|---|---|
| Operação preparada | Identificar tool, ação, destino/alvo, parâmetros relevantes, efeitos esperados. |
| Autoridade suficiente | Permitir execução **somente** dentro do escopo compatível. |
| Confirmação exigida | Aguardar decisão do proprietário **antes** de produzir efeitos externos. |
| Rejeição | Bloquear a tentativa; proposta/rascunho pode permanecer consultável. |
| Aprovação | Verificar que operação, alvo, conteúdo e condições continuam correspondentes à aprovação. |
| Mudança material pós-aprovação | Invalidar o uso da aprovação anterior para aquela tentativa; reavaliar autoridade. |
| Permissão/integração indisponível | Não executar se autorização não puder ser verificada ou houver desabilitação. |
| Execução | Registrar evidências operacionais proporcionais, sem expor segredos. |
| Resultado observado | Distinguir sucesso, falha e incerteza; não inferir sucesso por ausência de erro visível. |

## 3. Autoridade e confirmação

Distinguir **consulta**, **preparação**, **alteração externa** e **operação crítica** segundo efeitos reais. A leitura pode expor dados sensíveis; criar um rascunho **em um serviço externo** pode já ser alteração. Não pedir aprovação desnecessária para leitura já autorizada, mas nunca presumir permissão de escrita a partir de acesso de leitura.

A apresentação da confirmação deve indicar, quando aplicável: **operação**, **alvo/destinatário**, **conteúdo/parâmetros materialmente relevantes** e **consequências esperadas**. Aprovação de um envio a um fornecedor não autoriza outro destinatário, conteúdo materialmente diferente, exclusão, compra ou ampliação de escopo. A operação depende tanto das permissões do provedor quanto dos controles internos do JARVIS. Agentes e skills não herdam concessões implícitas.

## 4. Resultados, falhas, retry e recuperação

- `SUCCESS`: evidência suficiente de realização; comunicar somente o efeito comprovado.
- `FAILED`: evidência de que não foi concluída conforme o objetivo; registrar o motivo conhecido.
- `UNKNOWN`: não há evidência suficiente para afirmar se o serviço externo produziu efeito; não declarar sucesso nem ausência de efeito.
- **Retry:** repetição só é aceitável se demonstrada segurança contra duplicação e autoridade válida; **nunca** repetir automaticamente alteração possivelmente efetivada de resultado desconhecido.
- Falha no verificador de autoridade implica **fail-closed** para a operação protegida; falha de comunicação após enviar um comando não equivale à certeza de não execução.
- Revogar ou desabilitar conexão antes do disparo impede a operação; depois do disparo, é necessário preservar/observar o resultado sem prometer reversão.

## 5. Invariantes

1. Nenhuma integração ou agente contorna a autorização do JARVIS.
2. Memória, documentos e saídas de ferramentas não concedem grants.
3. Aprovação de uma operação não autoriza outra materialmente distinta.
4. Verificação de autoridade indisponível bloqueia a operação protegida.
5. `UNKNOWN` nunca é apresentado como sucesso.
6. Recuperação/interrupção de task não concede permissão de repetir efeitos.
7. Operações privilegiadas deixam rastreabilidade suficiente sem expor credenciais.

## 6. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S01-AC01** | Consulta com autorização existente | Execução permitida sem confirmação desnecessária. |
| **S01-AC02** | Alteração externa exige confirmação | Operação aguarda aprovação. |
| **S01-AC03** | Usuário rejeita operação | Nenhuma execução ocorre. |
| **S01-AC04** | Alvo ou conteúdo muda após aprovação | Autoridade reavaliada. |
| **S01-AC05** | Agente solicita execução não autorizada | Operação bloqueada. |
| **S01-AC06** | Verificação de autoridade indisponível | Execução protegida bloqueada. |
| **S01-AC07** | Conexão interrompida após tentativa de alteração | Resultado incerto preservado, sem repetição insegura. |
| **S01-AC08** | Operação concluída | Resultado e decisão de autorização rastreáveis. |

## 7. Out of Scope / Open

Não fixa `Grant`, `ConfirmationRequest`, `PolicyDecision`, `ToolInvocation`, `AuditRecord`, modelo de ACL, tabelas, endpoints, sandbox, framework ou implementação do executor. A distinção funcional entre classes de efeitos e categorias de autorização deverá ser concretizada em Contracts/Architecture, sem afrouxar estas regras.

---

# SPEC-02 — Ciclo de Vida de Tarefas e Recuperação Operacional

**Status:** APPROVED  
**Requisitos relacionados:** FR-036–FR-046; NFR-003; NFR-004; SPEC-01.

## 1. Purpose / Scope

Definir criação, planejamento proporcional, estados, etapas, interrupção, persistência, acompanhamento, resultados parciais e recuperação de tarefas. **Task não é Conversation**, ainda que se origine dela. **Task não é Agent**: pode utilizar ferramentas diretas, agentes ou combinações. Nem toda pergunta vira tarefa; apenas atividades que exigem acompanhamento operacional precisam de ciclo de vida próprio.

## 2. Estados e motivos de espera

| Estado conceitual | Significado |
|---|---|
| `PENDING` | Registrada, aguardando início. |
| `RUNNING` | Executando ou coordenando etapas. |
| `WAITING` | Suspensa até que condição necessária seja resolvida. |
| `COMPLETED` | Objetivo atendido e resultado final registrado. |
| `FAILED` | Encerrada por falha impeditiva. |
| `INTERRUPTED` | Encerrada antecipadamente após interrupção efetivada. |

`WAITING` deve manter **motivo** identificável: `USER_INPUT`, `AUTHORIZATION`, `DEPENDENCY_UNAVAILABLE` ou `RECOVERY_REVIEW`, quando aplicáveis. Os nomes são conceituais e não definem enums técnicos. Um pedido de interrupção enquanto operação está em andamento pode ser representado por **indicador de interrupção solicitada**, sem afirmar prematuramente que a task já foi interrompida.

## 3. Transições permitidas e restrições

| Origem | Destino | Precondição |
|---|---|---|
| `PENDING` | `RUNNING` | Início autorizado e condições atendidas. |
| `PENDING` | `INTERRUPTED` | Cancelamento antes do início. |
| `RUNNING` | `WAITING` | Falta informação, autorização, dependência ou revisão de recovery. |
| `WAITING` | `RUNNING` | Motivo resolvido **e** continuidade revalidada. |
| `RUNNING` | `COMPLETED` | Objetivo realmente concluído; resultado persistível/registrado. |
| `RUNNING` | `FAILED` | Falha impeditiva confirmada. |
| `RUNNING` | `INTERRUPTED` | Interrupção efetivada com tratamento seguro das operações iniciadas. |
| `WAITING` | `INTERRUPTED` | Usuário encerra a atividade pendente, sem mascarar efeitos desconhecidos. |

`COMPLETED`, `FAILED` e `INTERRUPTED` são **terminais para aquela execução**. Uma nova tentativa pode referenciar a anterior, mas não apagar nem reescrever silenciosamente seu resultado. A estrutura de etapas pode evoluir durante a execução se o objetivo autorizado não for ampliado.

## 4. Progresso e acompanhamento

- Pergunta simples: responder sem task formal desnecessária.
- Atividade composta (p.ex. identificar critérios → pesquisar fornecedores → comparar → recomendar): acompanhar etapas concluídas, em andamento, bloqueadas e futuras.
- Apresentar eventos reais, não percentuais inventados pelo modelo; preservar resultados parciais caso etapa posterior falhe.
- Tarefa aguardando aprovação não executa etapa protegida antes da SPEC-01. Cada etapa operacional passa por sua própria validação de autoridade.
- Consultar a task ou seu histórico operacional **não** dispara nova execução; acompanhamento não depende exclusivamente do feed da conversa.

## 5. Interrupção solicitada

1. Registrar imediatamente a solicitação de interrupção.
2. Não iniciar novas etapas enquanto a interrupção é processada.
3. Tentar cancelar operações em andamento **quando houver suporte seguro e aplicável**.
4. Tratar efeitos e resultados das operações já iniciadas, sem prometer reversão.
5. Encerrar como `INTERRUPTED` somente quando possível representar o estado sem encobrir pendência crítica. Alteração externa de resultado desconhecido pode exigir `WAITING`/`RECOVERY_REVIEW` até avaliação apropriada.

Interromper a tarefa **não** significa desfazer uma compra, apagar um e-mail enviado ou cancelar efeito já ocorrido.

## 6. Reinicialização, concorrência e consistência

| Estado observado antes da interrupção da aplicação | Recuperação obrigatória |
|---|---|
| Pendente, ainda não iniciada | Restaurar como pendente. |
| Aguardando intervenção | Restaurar motivo e contexto necessários. |
| Consulta de leitura interrompida | Avaliar segurança e autorização antes de novo pedido. |
| Alteração com sucesso confirmado | Preservar resultado; não executar novamente. |
| Alteração de resultado desconhecido | Aguardar verificação; nenhuma duplicação automática insegura. |
| Concluída/interrompida | Preservar histórico, resultados e condição final. |

**Concorrência:** uma única continuação ativa por task; operações internas paralelas podem existir apenas se coordenadas e seguras. Não iniciar duas continuações independentes da mesma tarefa.

**Persistência:** preservar estado e evidências necessárias antes de afirmar conclusão. Uma falha de persistência deve ser explicitada; não reclassificar task como concluída sem representação confiável. O estado operacional pertence ao JARVIS; conhecimento sobre atividades pode existir no Sofias Memory apenas sob sua política de memória.

**Limite de ambiente:** persistência não implica que tarefas rodem com a interface fechada. Background/headless depende de escolha arquitetural posterior.

## 7. Invariantes

1. Task e Conversation mantêm identidades distintas.
2. Task não requer Agent por definição.
3. Nenhuma tarefa executa efeitos sem a SPEC-01.
4. Interrupção solicitada não é sinônimo de cancelamento já efetivado.
5. Recovery não repete ação externa de resultado incerto.
6. Uma task não admite duas continuações simultâneas independentes.
7. Resultado final não apaga resultados parciais nem altera execução histórica anterior.
8. Histórico de tarefas e estado operacional pertencem ao JARVIS, não ao Sofias Memory.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S02-AC01** | Tarefa simples | Não exige plano complexo desnecessário. |
| **S02-AC02** | Tarefa de múltiplas etapas | Etapas e progresso consultáveis. |
| **S02-AC03** | Etapa exige confirmação | Tarefa aguarda autorização. |
| **S02-AC04** | Confirmação concedida | Continuidade ocorre após revalidar condições. |
| **S02-AC05** | Interrupção durante execução | Novas etapas impedidas; operações em curso tratadas com segurança. |
| **S02-AC06** | Reinicialização da aplicação | Estado operacional anterior recuperável. |
| **S02-AC07** | Resultado externo desconhecido | Nenhuma repetição automática insegura. |
| **S02-AC08** | Falha parcial | Resultados já obtidos disponíveis. |
| **S02-AC09** | Tarefa concluída | Consultar histórico não dispara execução. |
| **S02-AC10** | Tentativa simultânea de continuar mesma tarefa | Não surgem duas continuações independentes. |
| **S02-AC11** | Ferramenta exige autorização adicional | SPEC-01 continua aplicável. |

## 9. Out of Scope / Open

Não define banco, scheduler, workers, número máximo de tarefas paralelas, execução com app fechado, retries técnicos, leases/locks ou mecanismos de persistência. Scheduler recorrente e orquestração multiagente avançada seguem FUTURE; a continuidade segura de tasks do MVP é obrigatória.

---

# SPEC-03 — Gerenciamento de Contexto e Continuidade Conversacional

**Status:** APPROVED  
**Requisitos relacionados:** FR-001–FR-016; FR-057; FR-067–FR-073; NFR-003; NFR-005.

## 1. Purpose e responsabilidades

**O histórico registra o que aconteceu. A memória representa o que merece ser lembrado. O contexto ativo contém o que é relevante para atender à solicitação atual.** Eles se relacionam, mas não se confundem.

| Elemento | Autoridade | Descrição |
|---|---|---|
| `Conversation` | JARVIS | Histórico e identidade de interações relacionadas. |
| `Message` | JARVIS | Intervenção da pessoa, do assistente ou evento relevante da conversa. |
| `Active Context` | JARVIS | Seleção temporária de informações pertinentes à interação corrente. |
| `Cognitive/Knowledge Memory` | Sofias Memory | Fatos, preferências, documentos, decisões, referências e proveniência persistentes. |
| `Task Reference` | JARVIS | Associação entre conversa e tarefa acompanhável. |

Fontes possíveis para construir o contexto: pedido atual, mensagens anteriores relevantes, memória/knowledge recall, estado de tasks relacionado e observações reais de ferramentas autorizadas. Selecionar por **relevância, escopo, atualidade, origem** e limites de contexto; nenhuma fonte concede autorização operacional.

## 2. Operações sobre conversas

| Operação | Semântica |
|---|---|
| Nova conversa | Histórico distinto; não copia indiscriminadamente mensagens de outra conversa. |
| Continuar | Utiliza histórico da conversa selecionada e informação contextual pertinente. |
| Alternar | Preserva associação correta de mensagens e tarefas; não altera outra conversa. |
| Retomar conversa antiga | Recupera mensagens persistidas e reconstrói contexto relevante. |
| Encerrar aplicação | Preserva histórico necessário para futura continuidade. |
| Reiniciar | Permite reabrir conversas anteriores, distinguindo intervenções incompletas. |

**Nova conversa não implica amnésia:** uma preferência global registrada pode ser relevante em qualquer conversa; decisões específicas de outro projeto não devem contaminar o projeto atual. Informação contextual deve permanecer associada ao escopo e à proveniência corretos. Quando assunto anterior é ambíguo, pedir esclarecimento proporcional ao risco; para **efeito externo dependente de contexto**, esclarecer antes de executar.

## 3. Texto, voz, transcrição e troca de conversa

- Texto e voz são modalidades da **mesma Conversation**, incluindo follow-ups que se referem ao turno anterior.
- Transcrição parcial de voz é provisória, **não** instrução definitiva para efeitos externos.
- Reconhecimento incerto demanda esclarecimento se a interpretação puder afetar operação relevante; texto permanece disponível se áudio falhar.
- Ao trocar de conversa durante captura, transcrição, streaming ou execução, preservar a associação com a conversa **de origem**. Não inserir resposta numa conversa recém-selecionada por conveniência da interface.
- Fechar a sessão de voz não apaga mensagens nem encerra a conversa.

## 4. Context window e proveniência

O histórico persistido pode ser maior do que a janela do modelo. **Histórico durável ≠ contexto enviado ao modelo**. Pode-se selecionar/condensar contexto sem excluir mensagens originais. Quando uma síntese gerada omitir condições importantes, deve haver possibilidade de recuperar evidência original disponível; a síntese não é mais confiável por si só.

- Contexto curto: utilizar o histórico necessário.
- Contexto extenso: selecionar por pertinência e limites, conservando histórico.
- Referência fora do contexto ativo: recuperar se disponível.
- Informação não localizada: reconhecer lacuna, não inventar lembrança.
- Informação conflitante: examinar escopo, origem e atualidade; esclarecer quando necessário.
- Retomada explícita: usuário escolhe conversa anterior.
- Recuperação entre conversas: usar informações persistidas e historicamente disponíveis que forem relevantes, não presumir que toda mensagem virou memória cognitiva.

## 5. Vínculo com tasks e falhas

Uma tarefa pode ser criada em Conversation A e continuar enquanto o usuário conversa em B. Alternar conversa não cancela a tarefa; conclusão e notificações preservam referência à origem e ao registro operacional. Consultar tasks não requer percorrer todo o histórico do chat.

| Falha / condição | Comportamento |
|---|---|
| Sofias Memory indisponível | Prosseguir com informação independente, revelando limitações pertinentes. |
| Consulta histórica sem evidência | Informar que não encontrou base para responder. |
| Aplicação fecha durante resposta | Não apresentar resposta interrompida como concluída. |
| Troca de Conversation durante resposta | Manter vínculo de origem da intervenção. |
| Voz falha | Preservar opção de texto. |
| Contexto ambíguo com side effect | Esclarecer antes da execução. |
| Conteúdo externo com instruções | Tratar como dado não confiável, nunca como autoridade. |

## 6. Invariantes

1. Uma mensagem pertence à sua Conversation, independentemente da modalidade.
2. Trocar conversa não altera o histórico de outra.
3. Conversation History e Cognitive Memory têm autoridades distintas.
4. Decisões de projeto não migram entre projetos sem evidência.
5. Redução do Active Context não apaga histórico persistido.
6. Memória recuperada não concede grants.
7. Respostas incompletas não aparecem como concluídas.
8. Resultado de task preserva vínculo operacional com sua origem.
9. Falha do Memory não transforma suposição em fato recuperado.

## 7. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S03-AC01** | Alternar texto e voz na mesma conversa | Contexto compartilhado. |
| **S03-AC02** | Criar conversa nova | Histórico independente; memórias gerais pertinentes não são perdidas. |
| **S03-AC03** | Retomar conversa após reinicialização | Histórico e continuidade recuperáveis. |
| **S03-AC04** | Conversa maior que janela do modelo | Histórico preservado; contexto selecionado adequadamente. |
| **S03-AC05** | Referência ambígua a assunto anterior | Esclarecimento quando necessário. |
| **S03-AC06** | Informações de projetos diferentes | Ausência de mistura indevida. |
| **S03-AC07** | Sofias Memory indisponível | Degradação controlada. |
| **S03-AC08** | Alternar conversa durante task ativa | Task mantém vínculo com a origem. |
| **S03-AC09** | Aplicação encerra durante resposta | Resposta incompleta não é tratada como concluída. |
| **S03-AC10** | Transcrição provisória contém ordem externa | Nenhuma execução baseada só na entrada provisória. |
| **S03-AC11** | Memória contém instrução de execução | Conteúdo não concede permissão. |

## 8. Out of Scope / Open

Banco de histórico, modelos de recuperação/compactação, tamanho da janela, streaming e persistência incremental, vínculo técnico task/conversation, retenção detalhada e tecnologia de voz ficam para decisões posteriores. Não criar uma segunda conversa canônica dentro do Sofias Memory.

---
# SPEC-04 — Integração com Sofias Memory e Semântica da Memória

**Status:** APPROVED  
**Requisitos relacionados:** FR-008–FR-016; FR-067–FR-073; NFR-002; NFR-005; RISK-01; RISK-06; SPEC-03.

## 1. Purpose / Scope

Definir como o JARVIS registra, recupera, atualiza e esquece informações persistentes e utiliza conhecimento documental por meio do Sofias Memory. **Sofias Memory é autoridade das informações armazenadas; JARVIS é autoridade de interpretação operacional, decisão, permissão e execução.** A integração real existente no projeto Sofia's Assistant é referência técnica para auditoria posterior, **não** uma dependência obrigatória deste novo JARVIS.

| Responsabilidade do JARVIS | Responsabilidade do Sofias Memory |
|---|---|
| Entender intenção e decidir quando recuperar informação. | Persistir/recuperar Cognitive Memory. |
| Construir Active Context e atribuir escopo. | Disponibilizar Knowledge Memory, documentos e referências. |
| Aplicar policy, grants e confirmações. | Lifecycle, proveniência e relações de conhecimento. |
| Executar tools, coordenar tasks e agents. | Potencialmente armazenar definições **declarativas** de skills e agents. |
| Persistir Conversation History e estado operacional. | Não executar operações, tools, scripts nem agents. |

A compatibilidade de versões, contratos e recursos **não é presumida**; deve ser auditada antes de implementar, principalmente Knowledge Memory e definições declarativas.

## 2. Operações cognitivas e suas regras

| Operação | Comportamento aprovado |
|---|---|
| `Create` | Registrar informação relevante com escopo e origem, confirmando resultado real. |
| `Get` | Recuperar informação identificada. |
| `Recall` | Recuperar informação pertinente à intenção/contexto, preservando evidência e proveniência disponíveis. |
| `Supersede` | Substituir informação anterior que deixou de ser vigente naquele escopo. |
| `Forget` | Fazer com que a informação esquecida não seja mais recuperada como memória cognitiva **ativa**. |

### Registro explícito

Ex.: “Lembre que prefiro Vuetify 3”. Interpretar intenção de lembrar, validar informações relevantes, selecionar escopo (geral ou projeto), solicitar gravação e **só confirmar após observar sucesso**. Se o Memory falhar, não afirmar que lembrou. Credenciais ou segredos operacionais não são persistidos como memórias comuns só porque o usuário pediu “lembre”.

### Atualização / escopo

Ex.: “Para este projeto quero utilizar outra biblioteca”. A alteração específica do projeto **não** deve substituir silenciosamente preferência global. Se há memória anterior equivalente no mesmo escopo, a anterior poderá permanecer histórica, mas não como verdade atual. Conflitos são examinados quanto a escopo, origem, data e relações de substituição; sem evidência suficiente, esclarecer ou declarar divergência, não escolher arbitrariamente.

### Esquecimento

Identificar memória-alvo, esclarecer ambiguidades, executar a operação apropriada, verificar resultado e informar o alcance efetivo. **Forget Cognitive Memory ≠ apagar todas as conversas, documentos, backups ou registros operacionais** contendo a informação. Uma memória esquecida não reaparece como ativa, mas exclusões em outros repositórios exigem operações/políticas distintas.

## 3. Retrieval, Knowledge e confiança

Priorizar por **relevância**, **escopo**, **atualidade**, **origem**, **confiabilidade/evidência** e **disponibilidade**. Não carregar indiscriminadamente toda a base a cada turno. A presença no banco não torna um fato universalmente correto ou atual.

Consulta documental (ex.: “Por que separamos o Core da memória?”): preservar referências de origem e evidências disponibilizadas pelo Sofias Memory; não atribuir ao documento conclusão que ele não sustenta; admitir quando não houver suporte. **Knowledge Memory ≠ Cognitive Memory ≠ Conversation History.** O Memory pode recuperar documentos/entidades/relações, mas não deve tomar posse da conversa canônica.

**Conflito:** decisão antiga de usar PostgreSQL versus decisão posterior específica de outro banco para um projeto exige verificar versão e escopo; inferência antiga não pode substituir decisão explícita do usuário sem fundamentos.

## 4. Persistência automática e definição de capacidades

Candidatos a memórias podem ser identificados, porém **candidato não é memória persistida nem autorização**. Antes de escrever: avaliar relevância, origem, escopo, sensibilidade e política. A regra inicial do MVP será detalhada e aprovada na SPEC-10: **sem persistência automática cognitiva por padrão**; o JARVIS poderá propor um registro sob supervisão.

Sofias Memory **poderá** preservar descrições e configurações declarativas de skills e agents; runtime executável, ativação, estado, grants e auditoria permanecem no JARVIS. A existência efetiva das APIs necessárias ainda deve ser verificada; criação/ativação completa de agentes é FUTURE.

## 5. Failure Semantics

| Situação | Tratamento obrigatório |
|---|---|
| Sofias Memory fora do ar | Continuar funções independentes; informar limitação de acesso à memória. |
| `Create` não confirmado | Não afirmar persistência. |
| `Supersede` falhou | Não apresentar mudança como registrada. |
| `Forget` não confirmado | Não afirmar esquecimento integral; sinalizar falha/incerteza. |
| Recall vazio | Não inventar memórias/referências. |
| Informação conflitante | Considerar evidências e escopos; esclarecer se necessário. |
| Contrato/resposta incompatível | Erro explícito na função afetada; não aceitar coerção silenciosa. |
| Documento contém comandos/instruções maliciosas | Tratar como conteúdo não confiável, sem autoridade sobre tools. |

## 6. Invariantes

1. Sofias Memory **nunca** executa operações do JARVIS.
2. Histórico canônico de conversas pertence ao JARVIS.
3. Conteúdo recuperado não concede grants.
4. Memória esquecida não retorna como cognitiva ativa.
5. Memória substituída não se apresenta como verdade vigente no mesmo escopo.
6. Proveniência disponível é preservada, não falsificada.
7. Falha de gravação não aparece como sucesso.
8. Escopo e intenção do proprietário governam registros e atualizações.
9. Resultados de ferramentas e documentos não viram automaticamente memórias permanentes.

## 7. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S04-AC01** | Usuário pede para lembrar informação | Memória registrada; resultado confirmado. |
| **S04-AC02** | Recuperação em conversa posterior | Informação relevante encontrada e utilizada. |
| **S04-AC03** | Atualização de informação anterior | Nova informação atual; anterior não apresentada como vigente. |
| **S04-AC04** | Esquecimento solicitado | Informação deixa de ser recuperada como memória ativa. |
| **S04-AC05** | Informação específica de projeto | Não contamina outros projetos. |
| **S04-AC06** | Consulta documental | Resposta sustentada em conhecimento recuperado e referências disponíveis. |
| **S04-AC07** | Informações contraditórias | Divergência tratada sem escolha arbitrária. |
| **S04-AC08** | Sofias Memory indisponível | Degradação controlada. |
| **S04-AC09** | Falha de gravação | JARVIS não afirma persistência inexistente. |
| **S04-AC10** | Documento contém instrução de execução | Nenhuma autoridade operacional concedida. |
| **S04-AC11** | Contrato incompatível ou resposta inválida | Falha explícita, sem interpretação silenciosa. |

## 8. Out of Scope / Open

Não fixa endpoints/schemas, versão do contrato, estrutura de datasets, algoritmos de recall, IDs de scope/provenance, técnicas de classificação ou mudanças específicas no Sofias Memory. A política de persistência automática é objeto da SPEC-10; implementação deve esperar auditoria de compatibilidade.

---

# SPEC-05 — Descoberta e Seleção Contextual de Capacidades

**Status:** APPROVED  
**Requisitos relacionados:** FR-017–FR-025; FR-058–FR-065; SPEC-01; SPEC-03; SPEC-04.

## 1. Purpose / Scope

O JARVIS deve descobrir **o que uma ferramenta sabe fazer** sem incorporar ao Core regras de negócio particulares do serviço que a fornece. Seleção é contextual, dinâmica e proporcional, mas **nunca substitui autorização**.

| Conceito | Significado funcional |
|---|---|
| `Capability` | Habilidade declarada. |
| `Tool` | Operação concreta, com entrada e efeitos. |
| `Plugin` | Agrupamento de capacidades correlatas. |
| `Skill` | Procedimento para orientar combinações de capacidades. |
| `Agent` | Coordenação especializada subordinada à autoridade do JARVIS. |
| `Registry` | Catálogo consultável das capacidades conhecidas e condições de uso. |

O Registry não precisa ser um serviço separado. Conhecimentos sobre uso de tools podem estar no Sofias Memory, mas o catálogo **operacional** e a habilitação/autorização pertencem ao JARVIS.

## 2. Metadados de descoberta

Uma capacidade declarada deve disponibilizar, quando oferecidos pela integração, **identificador**, **descrição**, **operações**, **entradas necessárias**, **efeitos declarados**, **requisitos de autorização**, **disponibilidade** e **origem**. Isso permite escolher candidatos; descrições e manifestos de plugins **não** são instruções privilegiadas, nem declaração de permissionamento comprova permissão efetiva.

## 3. Seleção contextual

```text
Intenção em linguagem natural
  → interpretar objetivo e contexto
  → consultar catálogo de capabilities conhecidas
  → avaliar finalidade, compatibilidade, disponibilidade e limites
  → selecionar tool(s) necessárias
  → enviar cada operação ao controle da SPEC-01
  → produzir resultado real, falha parcial ou limitação transparente
```

A seleção pode mudar durante a tarefa conforme novas necessidades surjam, sem ampliar o objetivo nem a autoridade. Pedido simples (consultar agenda) não exige Agent nem planejamento extenso. Pedido composto (calendário + e-mail) pode coordenar consultas, preservando resultados parciais e origens reais.

## 4. Dimensões de elegibilidade

| Condição | Consequência |
|---|---|
| Integração instalada/registrada | É conhecida no catálogo. |
| Configurada | Possui dados de conexão necessários. |
| Habilitada | Pode ser considerada para novas seleções. |
| Autorizada | Possui permissões **para a operação específica**. |
| Disponível | Está operacional segundo informação verificável no momento. |

Essas condições coexistem e não constituem sequência linear rígida. Uma ferramenta pode estar habilitada, mas com token expirado ou somente permissão de leitura. **Selecionada ontem não significa autorizada hoje**: reavaliar antes da execução. Conexão desabilitada não inicia novas operações, ainda que a credencial externa continue válida.

## 5. Ambiguidades, alternativas e updates

- Múltiplas conexões: usar conta inequivocamente identificada pelo contexto; quando alvo de efeito externo é ambíguo, pedir esclarecimento.
- Consulta a várias contas: pode usar múltiplas conexões quando pertinente e autorizado; preservar qual conta retornou cada dado.
- Ferramenta equivalente indisponível: considerar alternativa compatível **já autorizada**, sem bypass de acesso negado.
- Ferramenta ausente: informar limitação; não simular resultados ou execução.
- Nova integração habilitada: capacidade passa a ser descobrível sem editar regras do domínio no Core.
- Integração desabilitada/removida/alterada: deixa de ser elegível ou muda seu conjunto de capabilities; tarefas dependentes são reavaliadas conforme SPEC-02.
- Manifesto desconhecido ou inconsistência relevante de efeitos: não executar operação cujo objetivo/efeito não possa ser estabelecido com segurança.

**FR-025 — SHOULD pós-MVP:** pesquisar integrações não instaladas e **propor** criação/instalação futura, sem ativação automática, escalada de permissão ou execução de código sem aprovação. O MVP exige tools **existentes** e pelo menos dois domínios externos reais.

## 6. Failure Semantics

| Situação | Comportamento |
|---|---|
| Registry inacessível | Não presumir permissões sobre capabilities desconhecidas. |
| Tool declarada mas inacessível | Informar indisponibilidade. |
| Entradas obrigatórias ausentes | Solicitar parâmetros, não inventar. |
| Descrição contraditória | Não executar efeito relevante sem clareza. |
| Operação composta falha parcialmente | Preservar consultas válidas, identificar falhas. |
| Permissão revogada após seleção | Bloquear execução. |
| Tool retorna instrução hostil | Tratar como dado, nunca autoridade. |
| Tool removida durante task | Reavaliar plano, dependências e execução segura. |

## 7. Invariantes

1. Selecionar tool não autoriza executá-la.
2. Nenhuma capability contorna SPEC-01.
3. Integração desabilitada não inicia operação nova.
4. Não contornar permissão por ferramenta alternativa.
5. Core não contém regras de domínio da integração.
6. Metadados externos são dados, não instruções privilegiadas.
7. Resultado não observado não é inventado.
8. Skills/agents não ampliam grants.
9. Tool ausente não é apresentada como disponível.
10. Estado de disponibilidade e autoridade é reavaliado antes da operação real.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S05-AC01** | Pedido de consulta sem nome da tool | JARVIS identifica ferramenta adequada. |
| **S05-AC02** | Pedido exige dois domínios | Seleção e utilização coordenadas. |
| **S05-AC03** | Nova integração compatível habilitada | Capability torna-se descobrível. |
| **S05-AC04** | Integração desabilitada | Nenhuma nova execução pela integração. |
| **S05-AC05** | Tool sem autorização de escrita | Alteração não executada. |
| **S05-AC06** | Duas conexões possíveis; alvo ambíguo | Esclarecimento quando necessário. |
| **S05-AC07** | Tool ausente | Limitação informada sem inventar resultado. |
| **S05-AC08** | Falha parcial entre tools | Resultados válidos preservados e falha identificada. |
| **S05-AC09** | Permissão revogada após seleção | Execução bloqueada. |
| **S05-AC10** | Plugin fornece instrução maliciosa | Instrução não adquire autoridade. |
| **S05-AC11** | Skill recuperada sugere tool não autorizada | Execução impedida. |
| **S05-AC12** | Consulta simples | Sem agente/planejamento complexo desnecessário. |
| **S05-AC13** | Integração de novo domínio | Core dispensa regras específicas desse domínio. |

## 9. Out of Scope / Open

MCP não é protocolo obrigatório aprovado. Manifestos, Registry, router, invalidação, versionamento de capabilities, critérios quantitativos entre tools e marketplace/instalação pertencem a Contracts/Architecture ou FUTURE. Não fixar tool routing por um LLM específico.

---

# SPEC-06 — Ciclo de Vida de Integrações e Conexões Externas

**Status:** APPROVED  
**Requisitos relacionados:** FR-017; FR-020; FR-024; FR-058–FR-065; NFR-001; NFR-002; NFR-005; SPEC-01; SPEC-02; SPEC-05.

## 1. Purpose / conceitos

Gerenciar conexões com serviços externos, habilitação, verificação, expiração, reconexão e remoção sem criar autorização implícita. **Uma integração existir não significa que esteja conectada; conectada não significa habilitada; habilitada não significa toda operação autorizada.**

| Conceito | Exemplo ilustrativo |
|---|---|
| `Integration` | Conjunto de capacidades GitHub. |
| `Connection` | Configuração de acesso à conta pessoal ou profissional do proprietário. |
| `Capability` | Consultar repositórios. |
| `Tool` | Chamada concreta para listar repositórios via conexão selecionada. |

A mesma integração pode ter múltiplas connections do **mesmo proprietário** (o MVP continua single-user). A autorização de uma connection não se transfere automaticamente à outra.

## 2. Condições independentes

**Existência/instalação**, **configuração**, **habilitação**, **autorização por operação** e **disponibilidade** são dimensões independentes; não implementar um único status linear que esconda sua distinção. Uma conexão pode estar configurada, habilitada e indisponível; outra pode estar disponível apenas para leitura. Um teste de conexão bem-sucedido não garante disponibilidade futura.

## 3. Operações de gerenciamento e semântica

| Operação | Comportamento |
|---|---|
| `Configure` | Obter dados necessários; persistir configuração protegida; não exibir segredos. |
| `Enable` | Tornar elegível para descoberta, **não** conceder grants irrestritos. |
| `Disable` | Impedir novas chamadas; manter configuração quando aplicável. |
| `Check` | Verificar o que puder sem produzir side effects não autorizados; indicar verificado/inválido/indisponível/incerto. |
| `Reconnect` | Reestabelecer acesso pelos mecanismos válidos do provedor; reavaliar novas permissões. |
| `Remove` | Impedir utilização futura pelo JARVIS; não excluir dados externos. |
| `Revoke at Provider` | Executar revogação externa **somente** quando houver suporte, autorização e confirmação real do provedor. |

**Remoção local ≠ revogação no provedor.** Nunca declarar revogação externa se ocorreu apenas remoção da configuração local. Desabilitar não invalida necessariamente token externo; remover conexão não apaga mensagens, repositórios, compromissos ou outros dados do serviço.

## 4. Desabilitação durante operação

| Momento | Semântica |
|---|---|
| Antes da operação externa | Não disparar chamada. |
| Preparada, aguardando aprovação | Não iniciar enquanto conexão desabilitada. |
| Operação externa já solicitada | Cancelar apenas se possível e seguro; verificar/preservar efeito real. |
| Resultado externo incerto | Aplicar SPEC-01/02; não repetir automaticamente. |

A alteração de estado da conexão invalida pressupostos de seleção e exige reavaliação de tasks dependentes. Uma task que precise de conexão removida poderá ficar bloqueada, sem apagar resultados anteriores. O usuário deve distinguir **desabilitar**, **remover** e **revogar**.

## 5. Credenciais, múltiplas contas e memória

- Tokens/chaves são armazenados por mecanismo protegido sob responsabilidade do JARVIS, **não** em Cognitive Memory; a configuração necessária persiste para reinicialização.
- Token expirado, revogado ou sem escopo compatível bloqueia operações afetadas até regularização; reconexão pode alterar permissões.
- Pedido “consulte minha conta profissional” pode selecionar conexão identificada inequivocamente; pedido de envio sem conta/destinatário inequívoco exige esclarecer alvo.
- Sofias Memory pode guardar **conhecimento sobre integrações** e procedimentos, mas **não** suas credenciais, estado operacional ou grants.
- OAuth2, API Keys, token refresh e MCP são variáveis conforme serviço e **não** decisões globais da Spec.

## 6. Failure Semantics

| Situação | Resultado |
|---|---|
| Credencial expirada | Bloqueio de operação dependente e reconexão pertinente. |
| Serviço indisponível | Degradação parcial; demais serviços seguem quando independentes. |
| Desabilitação com chamada ativa | Não prometer que chamada enviada foi revertida. |
| Remoção | Impedir novas chamadas; reavaliar tasks afetadas. |
| Revogação externa impossível/não confirmada | Informar diferença e resultado real. |
| Escopos de provider mudaram | Não inferir autoridade adicional; reavaliar. |
| Duas contas com destino ambíguo | Solicitar esclarecimento. |
| Teste sem resultado | Disponibilidade não verificada, sem alegação de sucesso. |
| Proteção de segredo falha | Não expor credencial nem usar armazenamento inseguro como fallback. |

## 7. Invariantes

1. Instalada não significa autorizada.
2. Configurada não concede permissão irrestrita.
3. Desabilitada não inicia operação nova.
4. Permissões do provedor não substituem SPEC-01.
5. Revogação externa só é afirmada com evidência.
6. Remover conexão não exclui dados do serviço.
7. Segredos não são exibidos indevidamente.
8. Grants não são transferidos entre conexões.
9. Disponibilidade e permissão são reavaliadas antes da execução.
10. Sofias Memory não gerencia conexões nem suas operações.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S06-AC01** | Configurar conexão | Configuração preservada; credenciais protegidas. |
| **S06-AC02** | Habilitar conexão válida | Capability elegível para seleção. |
| **S06-AC03** | Conexão sem permissão suficiente | Operação não autorizada bloqueada. |
| **S06-AC04** | Desabilitar conexão | Novas operações impedidas. |
| **S06-AC05** | Desabilitar durante execução externa | Efeitos prévios tratados sem presumir cancelamento. |
| **S06-AC06** | Remover conexão | JARVIS deixa de utilizá-la; dados externos preservados. |
| **S06-AC07** | Solicitar revogação no provedor | Resultado distinguido da remoção local. |
| **S06-AC08** | Credencial expirada | Reconexão necessária; nenhuma execução não autorizada. |
| **S06-AC09** | Duas contas do mesmo serviço | Conexões e autorizações independentes. |
| **S06-AC10** | Reiniciar aplicação | Configurações essenciais recuperadas. |
| **S06-AC11** | Serviço indisponível | Outras funções continuam utilizáveis. |
| **S06-AC12** | Reconectar com permissões diferentes | Autoridade reavaliada. |
| **S06-AC13** | Task depende de conexão removida | Continuidade reavaliada pela SPEC-02. |

## 9. Out of Scope / Open

Formas de armazenamento de credenciais, formato de connection, refresh, testes de saúde, protocolos (inclusive MCP), revogação por provedor, distribuição/remoção de plugins e isolamento técnico pertencem a Contracts e Architecture. Não transformar plugin marketplace em obrigação do MVP.

---
# SPEC-07 — Interação por Voz e Ciclo de Vida das Sessões de Áudio

**Status:** APPROVED  
**Requisitos relacionados:** FR-001; FR-002; FR-006; FR-007; FR-047; FR-048; NFR-002; NFR-005; NFR-006; NFR-009; SPEC-01; SPEC-03.

## 1. Purpose / Scope

Definir captura, transcrição, entrada definitiva, processamento, reprodução e interrupção de voz. **Voz e texto são modalidades da mesma Conversation, nunca históricos separados**. A `Voice Session` é temporária e não substitui a Conversation, que preserva mensagens e continuidade. A falha de recursos de áudio **não** bloqueia texto.

| Elemento | Papel |
|---|---|
| `Voice Session` | Gerenciar interação temporária e suas condições. |
| `Audio Input` | Capturar fala e obter conteúdo reconhecido. |
| `Audio Output` | Reproduzir resposta audível. |
| `Conversation` | Conservar histórico unificado, independentemente da modalidade. |

## 2. Fases conceituais de interação

`IDLE` (sem captura) → `LISTENING` (captura autorizada) → `TRANSCRIBING` (reconhecimento) → `PROCESSING` (interpretação contextual) → `SPEAKING` (reprodução). **Não** são estágios técnicos obrigatoriamente exclusivos ou lineares: Realtime pode captar/transcrever enquanto fala, e uma tecnologia pode sobrepor fases. A UI deve informar corretamente quando está ouvindo, processando e respondendo.

### Controle da escuta

O proprietário consegue iniciar, identificar e encerrar/suspender captura; encerrar sessão de voz sem encerrar Conversation; e continuar por texto. Permissões e controles do ambiente precisam ser efetivos. Microfone negado/inacessível → nenhuma captura e acesso textual preservado. A Spec não escolhe captura contínua, push-to-talk, botão alternável ou wake word.

## 3. Semântica de transcrições

| Categoria | Uso permitido |
|---|---|
| `Partial` | Provisória; pode mudar; **nunca** disparar side effects por si só. |
| `Final` | Conteúdo reconhecido como definitivo para a intervenção; **não** implica grant. |
| `Uncertain` | Insegura para interpretar consequência relevante; exige esclarecimento apropriado. |
| `Failed` | Não produz instrução utilizável; pedir nova entrada ou oferecer texto. |

**Exemplo de risco:** o usuário diz “**não envie** aquele e-mail ainda”, mas o reconhecedor entrega provisoriamente “envie aquele e-mail”. Executar a partial seria inversão da intenção. Mesmo com transcrição final, executar depende de interpretação contextual, avaliação (SPEC-09) e autorização (SPEC-01); destinatário, valor, exclusão ou confirmação crítica ambíguos exigem esclarecimento apropriado.

## 4. Conversa, reprodução e interrupções

- Modalidade não define identidade de Conversation. “Qual dos dois?” dito por voz utiliza contexto textual anterior quando disponível; também funciona no sentido inverso.
- Troca de conversa durante captura/transcrição **não** deve redirecionar silenciosamente entrada/resultado para a conversa recém-selecionada; preservar vínculo original ou cancelar de forma explícita e segura.
- Quando saída falada estiver habilitada, resposta audível deve ser semanticamente coerente com a visual. Uma tabela extensa pode ser falada como síntese, preservando advertências e incertezas relevantes na interface.
- Falar “estou executando” **não comprova** que uma operação externa terminou; status de voz é distinto do status operacional.
- “**Parar de falar**” interrompe playback; “**parar de ouvir**” interrompe captura; “**interromper tarefa**” usa SPEC-02; “**não execute**” afeta operação segundo SPEC-01. Um controle não deve operar silenciosamente como o outro.
- Reprodução interrompida não apaga mensagem registrada nem cancela task. Barge-in automático permanece diferido.
- Uma aprovação por voz, quando suportada, deve identificar operação/escopo e evidência de intenção suficiente; expressão incerta não autoriza ação crítica. Quais operações críticas podem ser confirmadas **exclusivamente** por voz permanece OPEN.

## 5. Áudio e privacidade

Áudio bruto capturado é potencialmente sensível. A `Final` pode integrar Conversation History; a `Partial` permanece transitória, sem se tornar mensagem definitiva. **Retenção permanente de áudio bruto não é obrigação do MVP e fica desabilitada por padrão** segundo SPEC-10. Serviços remotos podem processar/transmitir áudio sob políticas pertinentes, sem prometer eliminação externa não comprovada. Histórico textual continua acessível quando áudio original não existe.

## 6. Failure Semantics

| Falha ou condição | Comportamento obrigatório |
|---|---|
| Microfone indisponível / permissão negada | Sem captura indevida; texto segue funcional. |
| Partial interrompida ou reconhecimento falhou | Não executar; solicitar repetição ou texto. |
| TTS/saída indisponível | Resposta textual preservada. |
| Usuário interrompe fala | Parar playback sem cancelar Task. |
| Conversation mudou durante transcrição | Não atribuir mensagem ao feed errado. |
| Aplicação encerra durante captura | Não registrar entrada incompleta como comando definitivo. |
| Confirmação falada ambígua | Não executar operação protegida. |
| Provedor de voz indisponível | Degradação, mantendo componentes independentes. |

## 7. Invariantes

1. Voz e texto utilizam a mesma Conversation.
2. Sessão de áudio não substitui histórico.
3. Partial nunca autoriza efeitos externos.
4. Toda ação por voz passa pela SPEC-01.
5. Interromper áudio não cancela automaticamente task.
6. Falha de voz não impede texto.
7. Mensagem não migra silenciosamente entre Conversations.
8. Captura respeita permissões e controles.
9. Continuidade independe de retenção permanente do áudio bruto.
10. Pronunciar uma conclusão não comprova execução externa.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S07-AC01** | Iniciar por texto e continuar por voz | Contexto preservado. |
| **S07-AC02** | Iniciar por voz e continuar por texto | Mesmo histórico conversacional. |
| **S07-AC03** | Microfone indisponível | Texto continua funcional. |
| **S07-AC04** | Permissão de captura negada | Nenhuma captura não autorizada. |
| **S07-AC05** | Partial contém comando externo | Nenhuma execução baseada na transcrição provisória. |
| **S07-AC06** | Final ambígua para side effect | Esclarecimento ou confirmação apropriada. |
| **S07-AC07** | Reprodução interrompida | Playback para sem cancelamento indevido de task. |
| **S07-AC08** | TTS indisponível | Resposta textual preservada. |
| **S07-AC09** | Troca de conversa durante transcrição | Mensagem não é inserida na Conversation incorreta. |
| **S07-AC10** | Aplicação encerra durante captura | Entrada incompleta não vira instrução final. |
| **S07-AC11** | Operação crítica pedida por voz | SPEC-01 integralmente aplicada. |
| **S07-AC12** | Resposta extensa com tabela | Áudio inteligível e conteúdo essencial na interface. |
| **S07-AC13** | Encerrar sessão de áudio | Conversation e histórico seguem disponíveis. |

## 9. Out of Scope / Open

STT/TTS, providers Realtime, execução local/nuvem/híbrida, push-to-talk, escuta contínua, wake word, barge-in, full-duplex, personalidade/voz, limiares de latência, formato/transporte, retenção completa e confirmação crítica só por voz não foram escolhidos. A política de áudio bruto é complementada pela SPEC-10.

---

# SPEC-08 — Interface de Controle e Visibilidade Operacional

**Status:** APPROVED  
**Requisitos relacionados:** FR-047–FR-057; FR-024; FR-038–FR-045; FR-051–FR-065; NFR-006; NFR-007; NFR-009; SPEC-01; SPEC-02; SPEC-03; SPEC-06; SPEC-07.

## 1. Purpose / Scope

A interface apresenta conversas, tarefas, confirmações, notificações, resultados e integrações de maneira legível e controlável, sem transformar o produto num monitor técnico. **UI não é autoridade operacional**: transmite intenções e mostra estados produzidos pelo JARVIS; não concede grants ou altera execução por sua própria lógica visual.

**Áreas funcionais (não necessariamente telas):** `Conversation`, `Activities`, `Approvals`, `Notifications`, `Integrations & Settings`. Dashboard, painel lateral, janela modal ou navegação são alternativas de UX ainda abertas.

## 2. Interação e acompanhamento

- Pergunta simples recebe resposta no chat sem navegação ou criação desnecessária de tarefa.
- Usuário pode abrir tarefas, autorizações e integrações **sem perder a Conversation atual**.
- Task acompanhável disponibiliza três profundidades: **resumo** (objetivo/estado/atenção), **progresso** (etapas e obstáculos) e **detalhes** (resultados parciais/finais, falhas, autorizações e eventos relevantes).
- UI reflete estados conceituais da SPEC-02 `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `INTERRUPTED` e motivo de `WAITING` quando conhecido.
- Progresso é baseado em **etapas/eventos observados**, não em porcentagens fantasiosas. Terminar chamadas de ferramentas não basta para declarar objetivo concluído.
- Task que termina enquanto usuário está em outra Conversation preserva vínculo de origem; não inserir resultado no feed errado.

## 3. Approval UX

Uma confirmação compreensível mostra **operação**, **integração/conexão**, **alvo/destinatário**, **parâmetros/conteúdo relevantes**, **efeito previsto** e **situação**. O usuário pode aprovar ou rejeitar. Exemplo **ilustrativo, não integração escolhida**: enviar e-mail pela conta profissional para `fornecedor@exemplo.com` com assunto “Solicitação de orçamento”. A confirmação não deve ser um “Permitir?” sem detalhes pertinentes.

- A UI apresenta operação **atual**, não snapshot desatualizado; mudança material exige revalidação pela SPEC-01.
- Aprovação concluída, rejeitada ou invalidada não pode aparecer como pendente reutilizável.
- Recuperar confirmação pendente após restart exige verificar que continua aplicável antes de executar.
- Clicar na interface apenas encaminha decisão ao mecanismo apropriado; **não pula policy nem executor**.

## 4. Notifications e resultados

| Classe de notificação | Exemplo / comportamento |
|---|---|
| Informação | Tarefa concluída; evento relevante sem exigir intervenção. |
| Atenção necessária | Solicitação de autorização, esclarecimento ou espera. |
| Falha/limitação | Serviço indisponível, operação falhou ou exige revisão. |

Notificação deve identificar a atividade/conversa/conexão correlata e permitir inspecionar detalhes quando cabível. Evitar ruído para cada token ou chamada interna. Aprovação via notificação não substitui a apresentação da solicitação completa. Pendências e falhas relevantes continuam consultáveis após restart quando ainda aplicáveis; não exigir retenção eterna de todo aviso transitório.

| Situação mostrada | Comunicação honesta |
|---|---|
| `SUCCESS` | Efeito externo comprovadamente concluído. |
| `FAILED` | Objetivo da operação não foi atingido conforme evidência. |
| `UNKNOWN` | Não há confirmação de que o efeito externo ocorreu. |
| `DENIED` | Controle de autoridade impediu a operação. |
| `WAITING` | Task/operação depende de condição ou decisão. |

`WAITING` e `DENIED` são condições operacionais exibidas; não são necessariamente resultados finais do mesmo enum de `SUCCESS/FAILED/UNKNOWN`.

## 5. UI de integrações

Permitir consultar e administrar estados e configurações de conexões do MVP. Mostrar identidade da integração/conexão, habilitação, autenticidade/necessidade de reconexão, disponibilidade conhecida e **limites de permissão conhecidos**. Não reduzir tudo a “conectado”: habilitada pode estar fora do ar, disponível pode ser read-only. Nenhum segredo deve ser exibido indevidamente.

## 6. Atualização, falha e acessibilidade

- Perda de comunicação com runtime: **não** apresentar estado antigo como confirmação atual; informar limitação.
- Task muda durante visualização: atualizar quando houver informação observada correspondente.
- Autorização obsoleta: impedir sua utilização.
- Trocar Conversation não interrompe automaticamente task nem move mensagens.
- Voz fora do ar: interação textual continua; audio stop não é task cancel.
- Operação longa: fornecer feedback e não bloquear desnecessariamente navegação.
- Estados importantes têm **texto/indicador acessível**; não dependem somente de cor, animação ou áudio.

## 7. Invariantes

1. Interface não possui autoridade independente.
2. Botões não contornam SPEC-01.
3. Status mostrado corresponde ao estado operacional conhecido.
4. `UNKNOWN` não aparece como sucesso.
5. Trocar de conversa não altera identidade das tasks.
6. Integração desabilitada não executa por continuar visível.
7. Notificações não expõem segredos.
8. Notificações não substituem detalhes de ações.
9. Todas funções essenciais podem ser acessadas por texto/controle visual.
10. Nenhum controle de UI altera silenciosamente estado ou autorização persistidos.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S08-AC01** | Conversa simples | Resposta sem navegação operacional supérflua. |
| **S08-AC02** | Task multi-etapas | Resumo, estado e progresso consultáveis. |
| **S08-AC03** | Task aguarda aprovação | Motivo e operação identificáveis. |
| **S08-AC04** | Usuário aprova operação | Decisão enviada ao mecanismo de autoridade. |
| **S08-AC05** | Usuário rejeita operação | Nenhuma execução decorrente da solicitação rejeitada. |
| **S08-AC06** | Confirmação perde validade | Aprovação obsoleta não aplicável. |
| **S08-AC07** | Operação `UNKNOWN` | Incerteza claramente indicada. |
| **S08-AC08** | Task termina enquanto outra Conversation está ativa | Resultado associado às origens corretas. |
| **S08-AC09** | Integração indisponível | Estado e limitações legíveis. |
| **S08-AC10** | Conexão read-only | Permissão de escrita distinguida de disponibilidade. |
| **S08-AC11** | Restart com confirmação pendente | Solicitação válida consultável; autoridade revalidada. |
| **S08-AC12** | Microfone indisponível | UI textual utilizável. |
| **S08-AC13** | Comunicação operacional perdida | Não exibe status antigo como atual confirmado. |
| **S08-AC14** | Operação longa | Feedback e navegação preservados quando aplicável. |
| **S08-AC15** | Informação crítica usa cor | Indicação textual/acessível equivalente. |

## 9. Out of Scope / Open

Desktop/Web/híbrido, framework, layout, dashboard futurista, design system, animação, real-time update, notificações nativas/push, storage de eventos e protocolo UI-runtime permanecem decisões futuras. Interface futurista é possibilidade estética, não obrigação formal no MVP.

---

# SPEC-09 — Planejamento, Avaliação de Decisões e Adequação ao Objetivo

**Status:** APPROVED  
**Requisitos relacionados:** FR-018–FR-023; FR-026–FR-035; FR-036–FR-046; FR-067–FR-073; NFR-001; NFR-007; NFR-008; SPEC-01; SPEC-02; SPEC-03; SPEC-05.

## 1. Purpose e distinções

Um ato pode estar tecnicamente disponível e autorizado, mas ser **inadequado** ao objetivo humano. A Spec separa:

| Responsabilidade | Questão que resolve |
|---|---|
| Planejamento | Quais passos necessários e dependências conduzem ao objetivo? |
| Avaliação da decisão | A ação proposta é pertinente, sustentada, proporcional e dentro do escopo? |
| Policy/autoridade | A operação específica **pode** ser executada? (SPEC-01) |

Não há obrigação de criar `DecisionReviewRuntime` ou outra camada física. Não é preciso chamar outro modelo para cada ação. Análise é **proporcional** à complexidade/efeito.

## 2. Fluxo funcional e resultados

```text
Objetivo e contexto
  → ação / plano candidato
  → avaliar adequação ao objetivo, suporte factual, escopo,
    consequências e viabilidade
       ├── ELIGIBLE → SPEC-01 (autorização) → execução quando permitida
       ├── NEEDS_CLARIFICATION → esclarecer dado relevante
       ├── NEEDS_REVISION → corrigir candidato/replanejar
       └── UNSUPPORTED → não executar; informar limitação
```

São **resultados de avaliação**, não estados nem grants de SPEC-01. `ELIGIBLE` pode ser `DENIED` pelo Policy; autorização disponível pode coexistir com `UNSUPPORTED`/`NEEDS_REVISION`. Nem avaliação elegível nem orçamento disponível aprovam execução.

### Critérios de adequação

| Critério | Pergunta |
|---|---|
| `Goal Alignment` | Contribui para o objetivo solicitado? |
| `Factual Support` | Os fatos relevantes têm evidência suficiente? |
| `Scope Preservation` | Permanece dentro do escopo? |
| `Consequence Awareness` | Efeitos e consequências materiais foram reconhecidos? |
| `Operational Feasibility` | Ferramentas e condições permitem executá-la? |

**Primeiro excluir candidatos inadequados ou sem suporte; depois comparar alternativas válidas.** Não escolher alternativa com invenção de fatos apenas porque tem maior score secundário. A inexistência de evidência para escolher uma opção superior deve ser declarada, não disfarçada de certeza matemática.

## 3. Planejamento proporcional e revisão

- Pergunta explicativa simples → resposta sem Agent ou Task formal.
- Consulta pontual → tool adequada, sob seleção/controle.
- Objetivo composto (pesquisar fornecedores → comparar → recomendar) → plano proporcional; esclarecer critérios essenciais quando necessário.
- Contratar/comprar/enviar/excluir exige analisar efeitos e obter autorização concreta. Pedido geral não autoriza automaticamente preço, destino e condições não definidos.
- Planos podem ser ajustados quando surgirem evidências novas ou dependência deixar de existir, **sem ampliar silenciosamente o objetivo**; o mesmo vale se usuário mudar instruções durante a task.
- Reavaliar quando mudarem intenção, fonte factual, disponibilidade, consequência ou condição de autorização; preservar resultados anteriores e SPEC-02/01.

**Exemplo aprovado:** “Avise que vou chegar atrasado” **não** sustenta “chegarei duas horas atrasado e podemos remarcar para amanhã”. As expressões “duas horas” e “remarcar” são, respectivamente, fato não informado e compromisso não pedido. Corrigir texto ou perguntar antes de propor envio, mesmo que exista grant para mensagens.

**Outro exemplo:** usuário autorizou **pedir orçamento**, mas tool sugere **comprar**; recomendação externa não altera finalidade nem concede nova permissão.

## 4. Consumo e observabilidade

Avaliações devem respeitar limite de modelos, ferramentas e custos (`NFR-008`, detalhado na SPEC-11). Não multiplicar agentes/inferências desnecessárias para pedidos triviais. Se orçamento impede continuação, informar restrição e não fingir trabalho realizado.

O usuário pode perguntar “por que você escolheu essa alternativa?”. JARVIS deve oferecer **justificativa compreensível**, fundamentada em objetivo, evidências disponíveis, alternativas relevantes, limitações e motivos de revisão/bloqueio. Não é necessário guardar ou expor raciocínio interno do modelo. Essa observabilidade não substitui audit de autoridade e execução.

## 5. Failure Semantics

| Situação | Tratamento |
|---|---|
| Intenção ambígua com side effect | Esclarecer antes de agir. |
| Fato crítico sem evidência | Não inventar; revisar ou pedir dado. |
| Candidato extrapola objetivo | Rejeitar ou revisar. |
| Recomendação externa incompatível | Não executar automaticamente. |
| Dependência essencial indisponível | Reavaliar task pela SPEC-02. |
| Usuário modifica objetivo | Reavaliar plano e grants afetados. |
| Alternativas não comparáveis | Comunicar limitações. |
| Candidato adequado mas não autorizado | SPEC-01 bloqueia. |
| Limite de recursos atingido | Não continuar consumo impedido; informar. |
| Avaliação necessária falha | Não executar operação relevante sem avaliação válida. |

## 6. Invariantes

1. Autorizada não significa adequada.
2. Adequada não significa autorizada.
3. Decisão não amplia silenciosamente objetivo.
4. Fatos sem suporte não se apresentam como certezas para side effects.
5. Compromissos não solicitados não se tornam obrigações externas implicitamente.
6. Replanejamento não contorna negação de grants.
7. Memórias e saídas de tools são dados, não instruções privilegiadas.
8. Simplicidade dispensa planejamento complexo injustificado.
9. Mudança relevante de evidência pode exigir reavaliação.
10. Limites de consumo configurados são respeitados.
11. Score secundário não torna candidato inelegível elegível.
12. Falha de avaliação necessária bloqueia efeito afetado.

## 7. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S09-AC01** | Pergunta simples | Resposta sem planejamento desnecessário. |
| **S09-AC02** | Objetivo composto | Plano proporcional às dependências. |
| **S09-AC03** | Candidato contém fato não informado | Corrigir ou esclarecer. |
| **S09-AC04** | Candidato introduz compromisso não pedido | Revisar ou submeter à decisão apropriada. |
| **S09-AC05** | Plano inclui operação fora do objetivo | Não executar automaticamente. |
| **S09-AC06** | Nova evidência invalida alternativa | Decisão reavaliada. |
| **S09-AC07** | Candidato adequado, não autorizado | Bloqueio pela SPEC-01. |
| **S09-AC08** | Tool sugere ação adicional | Sugestão não vira autorização. |
| **S09-AC09** | Mudança material do objetivo | Plano/grants afetados reavaliados. |
| **S09-AC10** | Comparação tem evidência insuficiente | Limitações comunicadas. |
| **S09-AC11** | Limite de consumo atingido | Restrição respeitada sem simular trabalho. |
| **S09-AC12** | Avaliação necessária falha | Operação afetada não é executada. |
| **S09-AC13** | Usuário pergunta por que houve escolha | Justificativa compreensível sustentada em evidência. |
| **S09-AC14** | Replanejamento durante task | Continuidade segura; resultados prévios preservados. |

## 8. Out of Scope / Open

Não obriga runtime técnico `DecisionReview`, modelo/planner especializado, modelos distintos, scoring/thresholds, schema de plano/justificativa, número máximo de replanos ou arquitetura multiagente. A capacidade é comportamento, não tecnologia prescrita.

---
# SPEC-10 — Privacidade, Retenção e Política de Persistência de Informações

**Status:** APPROVED  
**Requisitos relacionados:** FR-003; FR-008–FR-016; FR-033; FR-042; FR-064; NFR-002; NFR-003; NFR-007; RISK-06; OQ-05; SPEC-01–SPEC-04; SPEC-06; SPEC-07.

## 1. Purpose / Scope

**Ter acesso a informação não autoriza armazená-la permanentemente, compartilhá-la com outros serviços ou convertê-la em Cognitive Memory.** Diferenciar persistência (sobrevive reinício) de retenção (por quanto tempo e sob quais condições). Preservar continuidade, recuperação e auditoria sem guardar indiscriminadamente tudo que passa pelo sistema.

### Categorias e owner

| Categoria | Exemplos | Responsabilidade |
|---|---|---|
| `Conversation Data` | Mensagens, transcrições finais, respostas | JARVIS |
| `Cognitive Memory` | Preferências, fatos e decisões duráveis | Sofias Memory |
| `Knowledge Data` | Documentos, fontes, conhecimento, referências | Sofias Memory |
| `Operational Data` | Tasks, etapas, confirmações e resultados | JARVIS |
| `Audit Data` | Evidência de execução, autoridade e resultado | JARVIS |
| `Credentials & Secrets` | Tokens, API keys, segredos de integrações | JARVIS, mecanismo protegido |
| `Transient Data` | Áudio temporário, partial transcripts, contexto intermediário | Componente que processa |

Categorias não são schemas, bancos ou infraestruturas aprovadas. Uma mensagem pode incluir uma preferência sem que isso gere `Cognitive Memory`; um resultado de tool pode trazer informação útil sem gravação automática.

## 2. Política funcional do MVP

| Categoria | Política aprovada |
|---|---|
| Histórico de conversas | Persistir para continuidade e consulta, respeitando política de retenção efetiva. |
| Memória solicitada explicitamente | Validar escopo/intenção, gravar no Sofias Memory e confirmar somente sucesso observado. |
| Memória candidata detectada automaticamente | **Não persistir automaticamente por padrão**; pode propor registro ao usuário. |
| Knowledge Data | Ingerir fontes/documentos mediante solicitação ou configuração autorizada. |
| Task e resultados operacionais | Persistir o necessário a acompanhamento, consistência e recovery. |
| Grants/confirmations/auditoria | Reter evidências necessárias à segurança e rastreabilidade, sem segredos desnecessários. |
| Credentials | Mecanismo protegido, enquanto necessárias e permitidas. |
| Áudio bruto | **Sem retenção permanente por padrão**; processamento temporário conforme política. |
| Transcrições parciais | Transitórias; não são mensagens definitivas. |

**OQ-05:** resolvida **funcionalmente para o MVP** quanto a escrita cognitiva explícita e à desabilitação de persistência automática por padrão. **Não** resolve prazos, backups, descarte, parâmetros técnicos ou uma futura política de gravação automática. Esta última dependerá de definição e aprovação específicas.

## 3. Escrever, sugerir, atualizar, esquecer e excluir

### Memória explícita

Identificar intenção e escopo; esclarecer ambiguidades; verificar sensibilidade; encaminhar ao Sofias Memory; confirmar resultado real. Preferência específica de projeto não vira global. Credencial observada em conversa **não** se converte em memória cognitiva normal mesmo sob pedido “lembre-se”; segredos legítimos vão para mecanismo apropriado.

### Memória candidata

```text
Candidato potencialmente útil
  → avaliar relevância + origem + escopo + sensibilidade
  → verificar autorização de persistência ou política previamente aprovada
  → persistir no Sofias Memory quando permitido e confirmar resultado
```

Candidato não é persistência nem grant. Não guardar indefinidamente candidatos descartados apenas porque foram avaliados. A persistência automática ampla continua desabilitada no MVP.

### Esquecimento não é exclusão universal

| Solicitação | Efeito e fronteira |
|---|---|
| `Forget Cognitive Memory` | Deixar de utilizar registro como memória cognitiva **ativa**. |
| `Supersede Memory` | Registrar mudança da verdade vigente no escopo relevante. |
| `Delete Conversation` | Excluir histórico correspondente **quando a funcionalidade e a política aplicável estiverem disponíveis**. |
| `Remove Knowledge Source` | Excluir/desativar fonte conforme lifecycle de Knowledge Memory. |
| `Remove Connection` | Impedir acesso futuro via conexão no JARVIS, sem apagar dados externos. |
| `Remove Operational Data` | Sujeito à integridade de task, auditoria e política de retenção aplicável. |

Uma informação esquecida pode existir também em mensagens, fontes originais, registros operacionais, backups ou provedores externos. Não prometer exclusão universal sem capacidade e evidências. Preservar o mínimo necessário para recuperação de operações pendentes **não** legitima reter conteúdo sensível arbitrariamente sob pretexto de auditoria.

## 4. Retenção e transmissão de dados

**Política por categoria**: histórico enquanto sob retenção vigente; memória até supersede/forget/regra aplicável; fontes conforme gestão do conhecimento; operacional enquanto necessário para consistência/recovery; auditoria conforme segurança; segredos enquanto necessários; dados transitórios não são persistidos permanentemente sem justificativa/autorização.

**Prazos específicos de retenção, descarte em backups e tratamento de caches ainda estão OPEN.** Não inventar 30/90/365 dias ou dizer que o produto já os aplica. **Antes de operar com dados reais cuja retenção dependa deles**, devem existir política efetiva e transparência; não habilitar funcionalidades adicionais dependentes de política indefinida.

Transmitir contexto a provider de IA ou ferramenta externa requer finalidade, configuração e acesso compatíveis. Limitar aos dados pertinentes; não enviar toda memória ou conversa só porque está disponível. Providers de voz/IA podem possuir retenção própria: não afirmar que descartaram conteúdo sem base. Processamento de voz remoto requer transparência sobre configurações pertinentes; não exigir confirmação repetitiva para cada uso já autorizado.

## 5. Áudio, segredos e auditoria

- Captura só com controles/permissões. Partial permanece transitória; final pode integrar Conversation History. Áudio bruto não é guardado permanentemente por padrão; processamento remoto pode ter política própria.
- Credenciais pertencem a mecanismo protegido do JARVIS e são usadas apenas na connection/operação pertinente. Nunca registrar como texto simples em log, modelo, memória cognitiva ou fallback inseguro de secret store.
- Audit precisa correlacionar **operação, ferramenta/conexão, decisão de autoridade/confirmation, alvo suficiente, resultado/evidência e task/etapa/tentativa**, sem copiar indiscriminadamente documentos completos, payloads sensíveis ou tokens. Proteger detalhes necessários à prova operacional.
- Revogação/removal de conexão impede uso futuro de seu segredo pelo JARVIS, sem inventar remoção no provedor.

## 6. Failure Semantics

| Evento | Tratamento |
|---|---|
| Falha de gravação de memória | Não declarar sucesso. |
| Forget cognitivo deixou referências históricas | Informar escopo real do esquecimento. |
| Provider fora do ar | Degradação de função afetada; preservar independentes. |
| Política de retenção exigida ainda indefinida | Não habilitar persistência adicional dependente da política. |
| Segredo encontrado em conversa | Não promover automaticamente a Cognitive Memory. |
| Dados sensíveis em saída de tool | Não propagar/expor desnecessariamente. |
| Exclusão sem confirmação | Informar falha ou incerteza, sem afirmar remoção total. |
| Informação envolvida em operação pendente | Resolver tensão de integridade/privacidade explicitamente. |
| Exclusão no provedor não confirmada | Não afirmar êxito fora do controle. |
| Secret protection indisponível | Não usar texto aberto como fallback. |

## 7. Invariantes

1. Histórico não é automaticamente Cognitive Memory.
2. Transient Data não é persistência permanente só por ter sido processado.
3. Candidato não é memória autorizada.
4. Segredos não entram na memória cognitiva comum.
5. Forget não apaga todos os registros onde o dado já apareceu.
6. Excluir/esquecer exige evidência para afirmar conclusão.
7. Transmissão a terceiros respeita finalidade/configuração/autoridade.
8. Áudio bruto não é retido permanentemente por padrão.
9. Auditoria não justifica coleção indiscriminada de segredos.
10. Proteção de credenciais não é contornada silenciosamente.
11. Sofias Memory não exerce autoridade operacional.
12. Informação recuperada não confere nova permissão.
13. Política efetiva de retenção deve estar conhecida antes do tratamento de dados reais que dela dependa.

## 8. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S10-AC01** | Proprietário pede lembrar | Persistência explícita e confirmada no Sofias Memory. |
| **S10-AC02** | Conversa contém preferência não solicitada como memória | Sem gravação automática sem política aplicável. |
| **S10-AC03** | JARVIS identifica candidato | Pode propor registro; não presume autorização. |
| **S10-AC04** | Informação sensível é credencial | Não grava como Cognitive Memory comum. |
| **S10-AC05** | Usuário solicita forget | Esquecimento confirmado no escopo próprio. |
| **S10-AC06** | Dado esquecido também está no histórico | JARVIS distingue repositórios/efeitos. |
| **S10-AC07** | Exclusão não verificável | Sem alegação de exclusão integral. |
| **S10-AC08** | Tool precisa de dados da conversa | Transmitir somente informações pertinentes. |
| **S10-AC09** | Interação por áudio | Sem retenção permanente de bruto por padrão. |
| **S10-AC10** | Provedor externo tem retenção própria | JARVIS não promete exclusão fora do controle. |
| **S10-AC11** | Audit de ação externa | Evidências suficientes sem segredos indevidos. |
| **S10-AC12** | Conexão removida | Uso posterior de credencial impedido. |
| **S10-AC13** | Proteção de credenciais falha | Sem fallback inseguro de armazenamento. |
| **S10-AC14** | Política de escrita automática indefinida | Persistência automática não habilitada. |
| **S10-AC15** | Task interrompida exige recuperação | Dados operacionais necessários preservados conforme política. |

## 9. Out of Scope / Open

Prazos de retenção, backups, descarte, tecnologia de criptografia/secret store, retenção efetiva de fornecedores, caches, UI de exclusão de conversas/fontes, classificadores de dados sensíveis, anonimização/pseudonimização e política futura de escrita automática continuam OPEN. Isso **não** autoriza retenção ilimitada silenciosa.

---

# SPEC-11 — Controle de Consumo, Orçamentos e Limites Operacionais

**Status:** APPROVED  
**Requisitos relacionados:** NFR-008; NFR-006; FR-026–FR-035; FR-036–FR-046; SPEC-01; SPEC-02; SPEC-06; SPEC-09.

## 1. Purpose / Scope

**Limites configurados são restrições reais, não meros avisos.** O JARVIS não pode consumir indefinidamente nem permitir que agent/task contorne orçamento. Também não deve confundir consumo medido, estimado ou não mensurável, nem alegar valor faturado quando conhece somente previsão.

| Categoria | Exemplos |
|---|---|
| Inferência IA | Tokens, chamadas, utilização de modelo. |
| Voz | Reconhecimento, síntese, sessões. |
| Tools externas | Chamadas, pesquisas, operações tarifadas. |
| Tasks | Operações e recursos ao longo das etapas. |
| Computação | Processamento/tempo quando mensurável. |

## 2. Configuração e condições

| Condição | Tratamento |
|---|---|
| Limite configurado | Aplicar restrição correspondente. |
| Ausência de limite | Mostrar que não há limite definido para aquele consumo; não fingir teto. |
| Limite atingido/impeditivo | Impedir **novas** operações afetadas até condição válida de continuação. |

Para recursos potencialmente cobrados, a configuração inicial deve informar a existência da cobrança e permitir estabelecer limites ou aceitar explicitamente ausência deles. Não solicitar confirmação financeira para cada chamada já autorizada. Limite por recurso/serviço deve respeitar seu escopo, mesmo em tasks diferentes.

## 3. Avaliação antes e depois da operação

```text
Operação planejada
  → identificar recurso e restrições aplicáveis
  → avaliar consumo medido/estimado/disponível
     ├── dentro de limite → passa aos demais controles de autoridade
     └── limite impeditivo → bloquear nova operação e informar
  → quando realizada, registrar consumo observado e incertezas
```

| Natureza da informação | Semântica |
|---|---|
| Medido | Utilizar valor observado do provedor/medidor. |
| Estimado | Identificar claramente como estimativa. |
| Desconhecido | Informar impossibilidade de determinar, não considerar custo zero. |
| Limite rígido não verificável | Não iniciar nova operação sujeita à restrição até condição segura. |
| Faturamento diferente da previsão | Preservar distinção e não prometer teto absoluto sem garantia. |

**Concorrência:** tasks que utilizam o mesmo orçamento compartilham a restrição e devem considerar **consumo combinado**. Escolha de locks, reservas ou contabilização atômica é técnica, mas o resultado não pode permitir duas tasks gastarem o mesmo saldo como se fossem únicas.

## 4. Orçamento durante task, autoridade e recovery

- Se task de pesquisa atingir limite, interromper **novas chamadas afetadas**, manter resultados parciais, informar bloqueio e permitir decisão do proprietário de alterar limite; a task pode permanecer `WAITING` (SPEC-02), não `COMPLETED` falsa.
- Consumo já realizado não desaparece ao interromper task, reiniciar app ou reduzir limite. Mudança de limite vale para operações posteriores.
- Uma operação externa **já iniciada** pode gerar custo mesmo que o JARVIS peça cancelamento; não prometer custo zero.
- Orçamento suficiente **não** autoriza tool; grant válido **não** substitui orçamento. Troca automática de provider para contornar restrição é proibida; alternativas legítimas precisam respeitar objetivo, orçamento e autoridade.
- Falha de medição não equivale a zero e o JARVIS não deve produzir retrys inseguros apenas para obter métricas.
- UI oferece acesso a limites configurados, consumo conhecido/estimado/desconhecido, bloqueios e tarefas afetadas, **sem exigir dashboard financeiro complexo** no MVP.

## 5. Failure Semantics

| Evento | Comportamento |
|---|---|
| Limite atingido | Novas operações afetadas bloqueadas. |
| Task interrompida | Consumo histórico preservado. |
| Restart | Limites e contabilização necessária recuperados. |
| Contabilização falhou | Não presumir zero. |
| Métrica não disponível | Indicar incerteza; respeitar restrição rígida. |
| Operação externa já iniciada | Não prometer cancelamento nem isenção de custo. |
| Limite aumentado | Reavaliar antes de continuar. |
| Limite reduzido | Aplicar a chamadas futuras e preservar valores já observados. |
| Resultado de tool desconhecido | Aplicar SPEC-01; sem repetição automática para buscar medição. |

## 6. Invariantes

1. Limite configurado aplicável impede novas operações além do seu escopo.
2. Tasks e agents não contornam orçamento via outra ferramenta/provider.
3. Consumo medido, estimado e desconhecido são distinguíveis.
4. Não presumir custo zero por falta de métricas.
5. Restrições compartilhadas consideram concorrência.
6. Tarefa bloqueada por orçamento não se torna concluída.
7. Orçamento não confere grants, grants não dispensam orçamento.
8. Consumo já observado não desaparece com cancelamento ou restart.
9. O JARVIS não promete teto absoluto que serviço externo não possibilita garantir.

## 7. Acceptance Criteria

| ID | Cenário | Resultado esperado |
|---|---|---|
| **S11-AC01** | Configurar limite | Restrição aplicada. |
| **S11-AC02** | Nova operação ultrapassaria limite impeditivo | Execução bloqueada. |
| **S11-AC03** | Task atinge limite durante execução | Resultados parciais preservados; continuidade suspensa. |
| **S11-AC04** | Duas tasks usam o mesmo orçamento | Consumo combinado considerado. |
| **S11-AC05** | Provedor informa consumo real | Registrar medição distinguindo estimativas. |
| **S11-AC06** | Custo não pode ser determinado | Não inventar valor. |
| **S11-AC07** | Limite rígido não é verificável | Não iniciar operação afetada. |
| **S11-AC08** | Agent tenta contornar limite via outra tool | Restrição continua válida. |
| **S11-AC09** | Usuário altera limite | Operações posteriores usam configuração nova. |
| **S11-AC10** | Restart | Recuperar limites e consumo necessário. |
| **S11-AC11** | Orçamento suficiente, sem autorização | SPEC-01 bloqueia. |
| **S11-AC12** | Provedor cobra após operação iniciada | Sem promessa de cancelamento ou custo zero. |

## 8. Out of Scope / Open

Valores monetários, limites numéricos padrões, moeda, janela de orçamento, modelo de billing, algoritmo de estimativa, contabilização concorrente e escolha dos fornecedores ficam para os passos técnicos. Provider nem sempre conhece o custo final antes de executar; não declarar garantia de teto que dependa de informação indisponível.

---

# SPEC-12 — Revisão Final de Consistência e Encerramento da Fase

**Status:** **APPROVED — revisão de fechamento**  
**Natureza:** verificação transversal, **não** uma 12ª Spec normativa com critérios de aceite adicionais.

## 1. Inventário e cobertura

| Bloco do PRD | Specs que detalham comportamento | Avaliação no fechamento |
|---|---|---|
| FR-001–FR-007 · Conversação | SPEC-03, SPEC-07, SPEC-08 | Coberto |
| FR-008–FR-016 · Memória | SPEC-04, SPEC-10 | Coberto |
| FR-017–FR-025 · Capabilities | SPEC-05, SPEC-06 | Coberto; FR-025 SHOULD pós-MVP |
| FR-026–FR-035 · Execução | SPEC-01, SPEC-09 | Coberto |
| FR-036–FR-046 · Tasks | SPEC-02, SPEC-09 | Coberto |
| FR-047–FR-057 · Interface | SPEC-07, SPEC-08 | Coberto |
| FR-058–FR-065 · Integrações | SPEC-05, SPEC-06, SPEC-08 | Coberto |
| FR-066–FR-073 · Contextos | SPEC-03, SPEC-04, SPEC-06 | Coberto |
| NFR-001–NFR-007 | SPEC-01–SPEC-10 | Cobertura transversal |
| NFR-008 · Controle de recursos | SPEC-09 e SPEC-11 | Lacuna detalhada pela SPEC-11 |
| NFR-009–NFR-010 | SPEC-05, SPEC-07, SPEC-08 | Coberto |

**Escopo da conclusão:** cobertura **documental/funcional** das Specs propostas e aprovadas. Não implica código, testes executados nem validação humana do MVP. Os `AC-001–AC-008` gerais do PRD permanecem vigentes.

## 2. Fronteiras preservadas

| Fronteira | Conclusão aprovada |
|---|---|
| JARVIS / Sofia's Assistant | Produto independente; reutilização seletiva. |
| JARVIS / Sofias Memory | Autoridades operacional e cognitiva separadas. |
| Conversation / Cognitive Memory | Histórico canônico não se converte automaticamente em memória. |
| Tool selection / Authorization | Relevância não concede grant. |
| Decision evaluation / Execution policy | Adequação não concede autorização. |
| Task recovery / Execution | Restore não permite retry inseguro. |
| Integration / Connection | Serviço e contas são identidades distintas. |
| Voice Session / Conversation | Entrada por voz não fragmenta histórico. |
| Memory Forget / Data Deletion | Esquecimento não equivale a exclusão universal. |
| Budget / Authorization | Saldo disponível não autoriza efeito externo. |

Não foram identificadas **contradições funcionais bloqueadoras** entre essas fronteiras nas onze Specs aprovadas. Isso não certifica ausência de problemas de implementação futuros.

## 3. Pontos de atenção, não bloqueadores deste fechamento

| ID | Risco/pendência | Resolver antes de |
|---|---|---|
| **SPEC-R01 — Retenção** | Prazos, backups e comprovação de exclusão ainda abertos. | Operar com dados reais cujo tratamento dependa dessa política. |
| **SPEC-R02 — Voz e confirmação** | Quais operações críticas admitem confirmação apenas falada e com quais garantias? | Habilitar tal confirmação. |
| **SPEC-R03 — Custos** | Provedores podem não permitir verificação antecipada precisa do custo. | Oferecer limites rígidos/garantias conforme provider concreto. |
| **SPEC-R04 — Memory compatibility** | Contratos efetivos de Cognitive, Knowledge e definições declarativas não auditados para JARVIS. | Implementar integração correspondente. |

**OQ-05:** comportamento inicial da escrita cognitiva automática ficou determinado pela SPEC-10 (**desabilitada por padrão**). Prazos de retenção/descarte e futura escrita automática permanecem pendentes; não registrar OQ-05 como “totalmente resolvida”.

## 4. Três jornadas de MVP

| Jornada do PRD | Cobertura detalhada |
|---|---|
| **A — Continuidade e memória** | SPEC-03, SPEC-04, SPEC-07, SPEC-10 |
| **B — Extensibilidade real** | SPEC-05, SPEC-06, SPEC-08 |
| **C — Execução supervisionada** | SPEC-01, SPEC-02, SPEC-08, SPEC-09 |
| **Controles transversais** | SPEC-10, SPEC-11 |

Nenhuma jornada dispensa os demais requisitos MUST e NFR. Duas integrações **de domínios externos distintos**, uma ação externa real autorizada, histórico compartilhado voz/texto, Memory, tasks e falhas de execução compõem o baseline do MVP.

## 5. Scope, DEFERRED e resultado

- **Sem blocker funcional identificado:** as onze Specs foram consideradas suficientemente precisas para prosseguir a Contracts.
- **FUTURE preservado:** Agent Builder completo, Skill Evolution automatizada, Plugin Discovery avançada, autonomia progressiva, colaboração multiagente, Knowledge Galaxy 3D, Ambient Context, automação avançada de desktop e multiusuário.
- **Tecnologias OPEN:** linguagem/runtime, UI, OS, providers de IA/voz, MCP, bancos, integração, isolamento, gravação, secrets, schemas, endpoints, budgets numéricos, latências.
- **Nenhuma tecnologia deliberadamente aberta foi convertida em decisão tomada**; as Specs definem comportamento observável.
- Mudanças materiais em política, autoridade, objetivo, requisito ou critério após aprovação precisam de mudança de baseline **explicitamente aprovada** pelo proprietário.

**Decisão SPEC-12:** revisão final e fechamento da Fase 04 **APPROVED**. Materializar `docs/product-manager/04-JARVIS-Specs.md` com as onze Specs integrais, 136 ACs e as conclusões acima; depois seguir para Contracts **apenas onde um acordo entre componentes seja necessário**.

---

# Anexo A — Rastreabilidade para o trabalho seguinte

## A.1 Contratos candidatos (não aprovados como arquitetura)

O estágio de Contracts deverá avaliar somente fronteiras com consumidores concretos, priorizando os comportamentos já definidos:

- **Execução/autoridade:** operação, alvo, escopo, confirmação, policy decision, resultado `SUCCESS/FAILED/UNKNOWN`, auditoria e recuperação (SPEC-01, SPEC-09).
- **Tasks:** estado, etapas, motivo de espera, correlação de tentativas e continuação segura (SPEC-02).
- **Conversation/UI/Voice:** identidade da conversa, mensagem final/provisória, proveniência da resposta, eventos e status de execução (SPEC-03, SPEC-07, SPEC-08).
- **Sofias Memory:** compatibilidade de operações Cognitive Memory, Knowledge Memory, escopos e referências; nenhum executor do lado Memory (SPEC-04, SPEC-10).
- **Capabilities/Connections:** metadados, entradas, efeitos, estados de elegibilidade, contas, revogação/remoção (SPEC-05, SPEC-06).
- **Budgets:** consumo conhecido/estimado/desconhecido, limites, bloqueios e concorrência (SPEC-11).

Essa lista indica **necessidades potenciais de interoperabilidade**, não exige um documento/serviço/contrato separado para cada linha.

## A.2 Verificações do baseline antes de implementar

1. Verificar compatibilidade efetiva com o Sofias Memory antes de escolher/adaptar contratos.
2. Escolher duas integrações reais apenas quando necessário à validação e definir suas permissões/efeitos.
3. Resolver política de retenção efetiva para dados reais e critérios de confirmação crítica via voz antes de habilitá-la.
4. Não estabelecer providers, stacks, SOs, UI ou protocolo MCP como obrigatórios sem decisão apropriada.
5. Planejar **vertical slices** que demonstrem valor concreto, testes de regressão pertinentes e validação humana de integrações reais.
6. Manter no PRD a autoridade sobre escopo e no presente documento a autoridade sobre **semântica funcional**; contratos não podem modificar esses baselines silenciosamente.

## A.3 Estado do projeto após a Fase 04

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | Fase 04 encerrada; próximo estágio: Contracts |
| **Current role** | Product Engineer / Software Architect |
| **Approved** | Discovery, Product Definition, PRD (PRD-01–PRD-11), SPEC-01–SPEC-11 e revisão SPEC-12 |
| **Open** | Questões técnicas e operacionais explicitamente adiadas, inclusive SPEC-R01–R04 |
| **Deferred** | Capacidades FUTURE e OQs cuja decisão depende de implementação concreta |
| **Rejected** | Executar via Memory, contornar Policy, duplicar side effects desconhecidos, confundir memória com histórico, transformar capacidades futuras em MVP obrigatório |
| **Current artifact** | `docs/product-manager/04-JARVIS-Specs.md` |
| **Current Slice** | Nenhum slice de implementação aprovado |
| **Next legitimate step** | Definir Contracts necessários, em decisões revisáveis e com aprovação humana explícita antes de baseline |

---

*Fim de JARVIS — Especificações Funcionais (Specs).*

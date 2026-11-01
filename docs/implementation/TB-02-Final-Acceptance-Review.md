# JARVIS — TB-02 Final Acceptance Review

**Revisão:** 2026-10-31 (horário local do proprietário)  
**Slice:** TB-02 — Memória e Conhecimento  
**Branch auditada:** `feat/tb-02-memory-knowledge`  
**HEAD auditado:** `d9ada3f030e50f3aeb383237b35fbf832bf993a1`  
**Baseline `main`:** `f75f2e1346de23db1507e016043bcf4a2f26ea3a` (inalterada)  
**Decisão:** **REVIEWED / IN PROGRESS — Product Done NÃO declarado**  
**Critério:** comparar código e evidências humanas à intenção do TB-02
no Technical Backlog e aos requisitos pertinentes do PRD-02, SPEC-04 e
CONTRACT-02/03. Nenhum requisito do MVP inteiro ou dos Slices TB-03+
é automaticamente declarado cumprido aqui.

## 1. Evidências aceitas

| Domínio | Evidência real | Resultado |
|---|---|---|
| Conectividade | Instância Sofias Memory v0.7.0, contrato de API 1 e capacidades cognitivas auditadas | PASS |
| Cognitive Create/Get/Recall | `--memory-create` com confirmação e Get/Recall da preferência pessoal `global/profile` | PASS no CLI |
| Supersede/Forget | Memórias **descartáveis A→B** com `CONFIRMED`, A/B em tombstone, sem conteúdo/escopo ativo; a memória pessoal permanece intacta | PASS **somente no laboratório controlado** |
| Knowledge dataset | `jarvis-knowledge`, ID `21100a21-d6e3-4dcc-a730-fe2f26111b5c`, active | PASS |
| Ingestão/indexação | ADR-0001, PipelineRun `21899eed-281f-4399-a6f4-8d73750da71b` `succeeded`; 1 fonte, 1 documento, 1 chunk ativos; hash verificado | PASS |
| Knowledge Retrieval | `RESULTS_FOUND`, query `a7a09ded-706f-4627-8772-39d27bcf7651`, referências com IDs coerentes | PASS no CLI |
| Chat CLI | Knowledge ON respondeu com ADR e referências; OFF não exibiu evidência documental | PASS |
| Desktop | OFF, Knowledge ON, Memory + Knowledge simultâneos demonstrados visualmente e no log | PASS no smoke |
| Testes | `172 passed in 4.90s` no Windows após correção Qt | PASS |
| Build | Vite `npm run build` passou (aviso não fatal de bundle maior que 500 kB) antes da instrumentação Python | PASS |
| Qt lifecycle | Três workers `completed`, todos `bridge_thread_finished` em GUI; `window_close_accepted`, `qt_about_to_quit`, `qt_event_loop_exit=0` | PASS do smoke |

**Limite importante:** o aborto nativo anterior
(`Fatal Python error: Aborted`/`QDxgiVSyncService not destroyed in time`)
não possui causa-raiz conclusiva. Um smoke limpo pós-correção autoriza
prosseguir à revisão, não prova ausência definitiva de regressões.

## 2. Confronto com os requisitos de produto

| Base | Estado de evidência | Observação |
|---|---|---|
| PRD-02 FR-008 / FR-009 | PASS no escopo testado | Persistir e recordar de outra conversa via Sofias Memory |
| PRD-02 FR-010 | **PARCIAL / BLOQUEIO DE ACEITE** | `Create` pessoal existe na CLI, mas `Supersede/Forget` do usuário são restritos aos UUIDs descartáveis; o desktop/chat não conduz pedido explícito de mutação à confirmação |
| PRD-02 FR-011 | PASS no escopo testado | Documento real recuperado; o desktop só oferece `jarvis-knowledge` |
| PRD-02 FR-012 | **PARCIAL / REVISAR CRITÉRIO** | Proveniência é apresentada no turno, mas não vinculada ao histórico de mensagens de maneira durável |
| PRD-02 FR-013 | PARCIAL | Escopo global/projeto e validação de dataset presentes; teste real restrito a um projeto/um documento |
| PRD-02 FR-014 | PASS da fronteira implementada | Conteúdo externo é tratado como dado; não há tools de execução neste Slice; não extrapolar para o futuro runtime |
| PRD-02 FR-015 | PARCIAL | Degradação prevista e coberta por testes com doubles; falta smoke humano específico da experiência de indisponibilidade no desktop |
| PRD-02 FR-016 | PARCIAL | Distingue ausência/indisponibilidade no fluxo, mas conflito, temporalidade e suficiência entre documentos reais não foram demonstrados |
| SPEC-04 S04-AC01..04 | PARCIAL | Create/Recall reais; Supersede/Forget reais somente em memória descartável e não expostos como operação pessoal conversacional |
| SPEC-04 S04-AC05..06 | PASS no piloto | Escopo verificado e ADR com fonte real |
| SPEC-04 S04-AC07..11 | MISTO | Falhas/contratos/injeção cobertos em testes; divergência real entre fontes não demonstrada |
| CONTRACT-02 / CONTRACT-03 | PARCIAL | APIs e referências compatíveis no caminho testado; multi-dataset, conflitos, resultado parcial e ciclo de fonte não têm cobertura end-to-end abrangente |

Esta matriz **não** é declaração de que todos os critérios do PRD
global ou dos contratos completos devam ser implementados agora:
registra a lacuna entre as demonstrações e a semântica aprovada do produto.

## 3. Findings para decisão antes de Product Done

### B-01 — P1: mutações cognitivas pessoais não estão integradas à experiência conversacional

**Constatação:** `main.py --memory-create` permite criar uma memória
pessoal confirmada. `--memory-test-supersede` e
`--memory-test-forget` usam `TestMemoryLab` e somente alvos na
allowlist `tb02_test_memories`. `ReplyWorker` e `ConversationRuntime`
oferecem recall e consulta documental, não tratamento de intenções
`lembrar/atualizar/esquecer` com preview, desambiguação e autorização
direta do usuário.

**Risco:** confundir evidência de viabilidade das APIs com a entrega
do requisito FR-010 / S04-AC01/03/04 para o usuário final.

**Critério de saída recomendado:** habilitar interface supervisionada
e restrita para comandos explícitos do proprietário, com confirmação
antes de qualquer mutação, identidade/escopo/alvo verificáveis,
journal/idempotência, ausência de repetição para `RESULT_UNKNOWN`,
sem escrita automática e sem acesso de mutações aos documentos.
A validação deve usar novo objeto de teste autorizado e não afetar a
memória pessoal previamente preservada.

### B-02 — P1: proveniência não sobrevive de forma independente à troca/reabertura da conversa

**Constatação:** o Qt WebChannel transmite referências por evento de
turno; `frontend/src/App.vue` mantém `knowledgeReferences` e
`knowledgeQueryId` apenas em refs reativas e limpa ao selecionar
outra conversa. `SQLiteConversationStore.messages` persiste papel,
conteúdo e status, sem `query_id`, dataset, `source_id`,
`document_id`, `chunk_id` ou relação auditável com a mensagem.
O texto gerado pelo LLM pode incluir uma citação, mas isso não
substitui a referência verificada pelo adapter.

**Risco:** uma resposta histórica atribuída a um ADR não pode ser
auditada novamente de forma estruturada ao reabrir o chat.

**Critério de saída recomendado:** definir persistência local mínima
dos **metadados de evidência**, associados ao `assistant_message_id`
(consulta, dataset e referências validadas, status e horário), sem
copiar chunks/documentos inteiros para SQLite. Recuperar e exibir essas
referências históricas com identidade e estado de mensagem corretos.
Não converter `url=null` em link inventado. Preservar o tratamento
de streaming interrompido/falho sem alegar resposta completa.

## 4. Limitações, riscos e decisões pendentes (não confundir com novos bloqueios automáticos)

1. **Escopo documental do piloto:** o chat aceita apenas o dataset
   `jarvis-knowledge`. Isso foi deliberado para a primeira prova
   controlada. Antes de generalizar, o proprietário deve aprovar
   descoberta/seleção de outros datasets e regras de acesso; não
   antecipar conectores ou outros domínios.
2. **Indisponibilidade/conflitos:** existem testes com doubles, mas
   ainda não há smoke visual específico de Knowledge/Memory
   indisponível nem prova multi-documento com conteúdo contraditório.
   Podem ser ensaios direcionados na finalização; não criar dados
   artificiais na instância real sem aprovação.
3. **Segurança e proteção de dados:** o journal elimina o payload
   após confirmação/rejeição; preserva payload de operações `unknown`
   para reconciliação. Esse armazenamento operacional merece política
   clara de retenção/proteção antes de ampliar as mutações pessoais.
   O detector atual de credenciais é uma salvaguarda inicial, não DLP.
4. **Qt/WebEngine:** crash nativo anterior documentado e smoke pós-fix
   aprovado. Manter diagnóstico opt-in e reabrir blocker em nova
   recorrência.
5. **UI e apresentação:** barras inferiores altas, scrollbar interno
   na fonte e suporte parcial a Markdown (ênfase/IDs podem aparecer
   literalmente). Classificar como refinamento visual; não resolver
   por interpolação HTML arbitrária ou por expandir o escopo do Slice.
6. **Documentação histórica:** vários runbooks descrevem estados
   antigos (`pendente`, 127/142/164 testes). Eles são evidências
   históricas, não devem substituir este estado consolidado.
   Recomenda-se um índice de status atual apontando para esta revisão.

## 5. Próximo incremento legítimo

**Proposta: TB-02 Finalization — sem novo Slice e sem TB-03**:

1. Resolver B-01 com desenho mínimo de fluxo supervisionado
   (pedido explícito → alvo/escopo → preview → confirmação → journal
   → confirmação real/reconciliação segura).
2. Resolver B-02 com evidência por mensagem, separando transcript,
   memória cognitiva e conhecimento documental.
3. Executar testes offline e smoke humano da integração, com um caso
   de degradação controlada; revalidar encerramento Qt se o worker mudar.
4. Atualizar documentação e emitir matriz final PASS/NOT PASS;
   somente então solicitar ao proprietário aceite formal de
   **TB-02 Product Done** e aprovação separada para merge.

**Nenhuma implementação, mutação em memória real ou merge é
autorizada automaticamente por esta auditoria.**

## 6. Post-finalization re-review (2026-11-01) — status by evidence

This section supersedes the earlier **implementation-status** claims
above without erasing the historical findings or falsely declaring
Product Done.

| Item | Observed evidence | Judgment |
|---|---|---|
| B-01a — supervised Cognitive Memory Create via CLI | Owner created disposable `project:jarvis/semantic` record; remote `active`, local `confirmed` | PASS for CLI |
| B-01b/c — desktop preview, cancel, Supersede, Forget | Owner confirmed preview/cancel, real replacement and Forget, remote state transitions and local journal `confirmed` | PASS |
| B-01d — durable typed consent | SQLite v4, fake desktop + CLI tests; owner reported `202 passed`, successful build, historical journal correctly `null` for retroactive consent | PASS for v4 contract |
| B-02a — durable Knowledge provenance | SQLite v5 linked to assistant-message ID, `214 passed`, Vite build, screenshot shows `RESULTS_FOUND` and verified source IDs inside the assistant message; owner confirmed conversation switch, restart and correct shutdown | **PASS** |
| Non-authoritative content boundary | Retrieved document IDs shown only as verified metadata; no automatic Cognitive Memory mutation in Knowledge flow | PASS for inspected pilot |
| UI **Create/lembrar** intent | `--memory-create` works from CLI, but no chat `/lembrar` or other desktop Create flow yet. `/atualizar` and `/esquecer` are supervised in desktop | **OPEN** if FR-010/S04-AC01 is interpreted as end-user conversational Create |
| Controlled service degradation | Offline tests and existing failure handling exist; a specific human desktop degraded-service scenario is not documented | **NOT VERIFIED in human smoke** |
| Contradictory evidence/knowledge | Single ADR documented and retrieved; no contradictory multi-source test | **NOT VERIFIED in pilot** |

This distinction matters: passing B-01 and B-02 *increments* does not
prove that all acceptance examples of FR-010/S04-AC01..09 have been
exercised end-to-end via the user-facing desktop. A minimal supervised
`/lembrar` UX may be needed to close that gap; a low-risk controlled
degradation test can be conducted without interfering with the real
Sofias Memory server. Any new behavior must be approved and verified
before claiming `TB-02 Product Done`.

The screenshot shows some raw Markdown emphasis tokens in assistant
prose. This is known deferred cosmetic work, not a provenance failure.
The Vite >500 kB chunk warning is non-blocking.

**Decision requested from owner:** confirm the remaining end-user
Create/degradation acceptance boundary before finalizing TB-02.
Neither Product Done nor merge to `main` is inferred from this report.

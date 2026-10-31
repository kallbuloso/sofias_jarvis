# JARVIS — Technical Backlog

| Campo | Valor |
|---|---|
| **Projeto** | JARVIS — assistente pessoal universal |
| **Fase** | 08 — Technical Backlog |
| **Estado deste documento** | **BASELINE DE PLANEJAMENTO APROVADA** — roadmap inicial TB-01 a TB-08 e plano do TB-01 aprovados pelo proprietário |
| **Estado de implementação** | **TB-01 PRODUCT DONE (2026-10-31)** — ver `docs/implementation/TB-01-Validation.md`; TB-02 a TB-08 continuam somente no roadmap |
| **Data** | 2026-10-30 |
| **Papel** | Product Engineer / Software Architect |
| **Destino** | `docs/product-manager/08-JARVIS-Technical-Backlog.md` |
| **Baseline** | Fases 01–07 aprovadas; ADR-0001 a ADR-0006 ACCEPTED |
| **Próxima atividade** | Validar o Create/Get/Recall explícito do TB-02 no Windows; depois avançar Context Integration e Knowledge Retrieval sem antecipar Slices posteriores |

> **Fidelidade:** este documento consolida somente o roadmap, o TB-01 e as decisões complementares expressamente aprovados. TB-02 está **aprovado e em execução** após confirmação do contrato da instância real; TB-03 a TB-08 continuam somente como roadmap, sem autorização de implementação. Tecnologias candidatas continuam condicionadas às validações da Architecture. O JARVIS é independente do Sofia's Assistant; Sofias Memory é serviço independente, não banco operacional nem executor.

## 1. Roadmap inicial do MVP

| Slice | Entrega utilizável esperada | Estado de planejamento |
|---|---|---|
| **TB-01 — Primeira conversa funcional** | Desktop inicia; chat real com IA em streaming; histórico reabre após restart | **APPROVED** (plano abaixo) |
| **TB-02 — Memória e conhecimento** | Integração com Sofias Memory, recall/knowledge e proveniência | **APPROVED / IN PROGRESS** — aprovação do proprietário após auditoria e diagnóstico da instância real; ver `docs/implementation/TB-02-Cognitive-Adapter.md` |
| **TB-03 — Conversação por voz** | Texto e voz compartilham conversa; controle de áudio e interrupção | **ROADMAP** |
| **TB-04 — Providers e conexões** | Configuração de contas, capabilities, disponibilidade e permissões | **ROADMAP** |
| **TB-05 — Ferramentas de consulta** | Capacidades READ verificadas em dois domínios externos reais | **ROADMAP** |
| **TB-06 — Execução supervisionada** | Confirmação, política, journal e um efeito externo real verificável | **ROADMAP** |
| **TB-07 — Tarefas persistentes** | Tarefa multietapa com progresso, interrupção e recuperação segura | **ROADMAP** |
| **TB-08 — Validação integrada do MVP** | Prova integrada de requisitos, segurança, consumo, falhas e recuperação | **ROADMAP** |

**Regra de sequenciamento:** a numeração representa uma ordem inicial proposta, não proibição de refinamento. Slices futuros devem ser detalhados e aprovados individualmente antes de sua implementação. Não criar Slices de infraestrutura sem capacidade verificável apenas para antecipar abstrações.

---

# TB-01 — Primeira conversa funcional

**Status:** **PRODUCT DONE** (validação humana em 2026-10-31; registro em `docs/implementation/TB-01-Validation.md`)

## Objective

Iniciar o JARVIS como projeto próprio no Windows 11, enviar uma mensagem de texto a um AI Provider real, receber resposta incremental e reabrir o histórico persistido após encerrar e reiniciar a aplicação.

## Product Value

Entregar o primeiro ciclo completo e observável do produto: **abrir → conversar → ver streaming → encerrar → reabrir → continuar**. Validar na prática a interação entre Core Python, persistência SQLite, provider e interface desktop antes de expandir para memória, voz ou ferramentas.

## Scope

1. **Aplicação independente:** bootstrap e configuração básica de um projeto JARVIS, sem dependência operacional do Sofia's Assistant.
2. **Conversation & Context:** criar, selecionar, listar, reabrir conversas e preservar mensagens/associações corretas; reconstruir contexto textual suficiente para continuidade, respeitando limites conhecidos do modelo.
3. **SQLite:** histórico operacional transacional e migrações necessárias; interrupção de streaming não pode produzir resposta falsamente marcada como concluída.
4. **AI Adapter real:** integração inicial com **OpenAI API — Responses API, streaming**; modelo configurável, sem ID fixo no Core; adapter compatível com CONTRACT-04 na parte efetivamente exercitada.
5. **Secrets:** API key no **Windows Credential Manager via `keyring`**, validando explicitamente o backend seguro antes de gravar/ler; sem fallback silencioso para arquivos inseguros; não expor a chave ao frontend, logs ou banco.
6. **Desktop UI mínima:** ensaio da composição **PySide6 + Vue 3/Vuetify 3 embarcado**, com ponte controlada (Qt WebChannel candidato); entrada de texto, resposta incremental, seleção e histórico de conversas, configuração mínima necessária e visibilidade de falhas.
7. **Lifecycle:** inicialização, encerramento de recursos, tratamento de falhas de API/rede e preservação do histórico na reinicialização.

**Limites de escopo:** o frontend e sua ponte são **candidatos sob prova técnica**, não escolha final consolidada; componentes de infraestrutura são implementados somente na medida necessária a esta entrega.

## Out of Scope

Sofias Memory; voz e STT/TTS/Realtime; agentes; ferramentas externas; operações protegidas e confirmações reais; provider registry genérico; fallback automático; automações; notificações avançadas; dashboard futurista completo; instalações executáveis e suporte a outros sistemas; execução em background obrigatória.

## Dependencies

| Item | Estado / condição |
|---|---|
| **TB01-D01 — Primeiro AI Provider** | **APPROVED:** OpenAI API, Responses API com streaming; modelo configurável |
| **TB01-D02 — Secrets Windows** | **APPROVED:** Windows Credential Manager por `keyring`, verificar backend seguro; fail closed |
| Ambiente Windows 11 e acesso à API | Necessários para validação humana com chamada real; chave não deve ser inserida em chat ou commit |
| Repositório próprio do JARVIS | Identificação e acesso necessários antes da execução; não presumir que já exista |
| Versão Python definitiva | **OPEN:** 3.13 é candidato; validar bibliotecas e fixar baseline reprodutível antes da implementação dependente |
| PySide6, Vue/Vuetify e ponte | **CONDITIONAL:** demonstrar integração suficiente neste Slice; áudio e confirmação da prova ARCH-05 serão completados nos Slices correspondentes |
| SQLAlchemy 2 / Alembic | Candidatos preferenciais, não obrigatórios sem validação |

## Relevant Decisions

- **ARCH-01 / ADR-0001:** modular monolith, Core independente da UI.
- **ARCH-02 / ADR-0002:** SQLite, integridade e recuperação conservadora.
- **ARCH-03 / ADR-0003:** não expor autoridade de execução ou segredos à interface, mesmo sem tools neste Slice.
- **ARCH-04 / ADR-0004:** local-first, Windows 11 como alvo inicial.
- **ARCH-05 / ADR-0005:** Python aprovado; PySide6/Vue/Vuetify e bridge ainda candidatos.
- **ARCH-06 / ADR-0006:** adapters de providers; não antecipar Registry universal.
- **SPEC-03:** identidade e continuidade de conversas; histórico ≠ contexto ativo ≠ memória cognitiva.
- **CONTRACT-04 e CONTRACT-06:** inferência/streaming e fronteira Interaction Surface ↔ Core.

## Implementation Plan

| Etapa | Resultado interno demonstrável |
|---|---|
| **01 — Bootstrap** | Inicialização do JARVIS a partir do próprio código-fonte, configuração e verificação de dependências |
| **02 — Persistence** | SQLite com estrutura mínima de Conversation/Message e migrações; reabertura após restart |
| **03 — AI Adapter** | Solicitação à Responses API, modelo configurável, normalização de eventos, erros e streaming |
| **04 — Secrets** | Escrita/leitura de credencial no Credential Manager, com verificação de backend e sem exposição na UI |
| **05 — Desktop Proof** | Janela PySide6 renderiza Vue/Vuetify e permite troca de comandos/eventos sem acesso direto à autoridade operacional |
| **06 — Conversation** | Enviar, acompanhar resposta incremental, selecionar e retomar conversas sem contaminação entre elas |
| **07 — Validation** | Testes, chamada real, tratamento de falhas e validação humana do ciclo completo |

Essas etapas são tarefas internas do **mesmo TB-01**, não sete novos Slices.

## Acceptance Criteria

| ID | Resultado observável |
|---|---|
| **TB01-AC01** | O JARVIS inicia no Windows 11 pelo seu próprio repositório, sem Sofia's Assistant |
| **TB01-AC02** | Uma mensagem do usuário recebe resposta real de IA pela OpenAI API |
| **TB01-AC03** | Streaming apresenta o texto progressivamente, na ordem correta e sem duplicações |
| **TB01-AC04** | Mensagens persistem com associação à Conversation correta |
| **TB01-AC05** | Após reinicialização, uma Conversation pode ser reaberta e continuada |
| **TB01-AC06** | Indisponibilidade/erro do provider são mostrados sem resposta inventada ou status falsamente concluído |
| **TB01-AC07** | Credenciais não são expostas ao frontend, banco operacional, logs ou arquivos comuns; backend seguro verificado |
| **TB01-AC08** | Encerramento correto, sem processos ou recursos abandonados |

Os oito critérios acima reproduzem os resultados aprovados para o Slice. Detalhes de testes abaixo orientam a evidência; não inserem novas funcionalidades no escopo.

## Required Tests

- **Unitários:** isolamento de conversas, transições de mensagem incompleta/concluída, construção de contexto, normalização de eventos e erros do adapter com mocks.
- **Persistência/integridade:** reabrir conversas após restart; nenhuma mensagem migra para outra conversa; falha/interrupção não marca resposta incompleta como concluída.
- **Bridge/UI:** comandos não acessam diretamente SQLite, credenciais ou execução arbitrária em Python; streaming incremental e troca de Conversation durante resposta preservam origem.
- **Secrets:** backend de armazenamento não seguro/ausente deve impedir armazenamento e acesso inseguro; verificar ausência de chaves em logs, banco e payloads de UI.
- **Integração real:** ao menos uma chamada de texto à OpenAI com streaming e modelo configurado, observando resultado/erro e consumo quando disponibilizado.
- **Lifecycle:** inicializar, encerrar e reiniciar; não deixar recursos/processos pendurados.

## Human Validation

1. Configurar a API key **localmente**, sem enviá-la a conversas, commits ou relatórios.
2. Iniciar JARVIS no Windows 11 e criar uma conversa.
3. Enviar mensagem; verificar streaming incremental e resposta efetiva.
4. Enviar follow-up na mesma conversa e verificar continuidade contextual.
5. Criar/selecionar outra conversa e confirmar isolamento visual e persistido.
6. Fechar, reiniciar e reabrir a conversa anterior; verificar histórico e continuidade.
7. Simular ausência/erro de credencial ou indisponibilidade de API e verificar falha explícita.
8. Encerrar e observar liberação de recursos e processos.

## Known Risks

| Risco | Tratamento nesta etapa |
|---|---|
| **ARCH-R01 — UI híbrida** | Avaliar bridge, streaming, consumo, lifecycle; a prova arquitetural **completa** também requer áudio e confirmação em Slices posteriores. Não declarar frontend definitivamente validado no TB-01. |
| **ARCH-R02 — Python/dependências** | Confirmar versões realmente compatíveis antes de congelar requirements/lock |
| **ARCH-R03 — proteção de credenciais** | Validar backend nativo seguro; se indisponível, bloquear sem downgrade |
| **CONTRACT-04 — streaming e estado parcial** | Eventos interrompidos não equivalem a resposta concluída; preservar correlação |
| **Custos e privacidade** | Chamada real envia o contexto selecionado ao provider e pode gerar custo; limitar envio ao necessário, sem prometer offline |
| **Licença/reutilização** | Avaliar componentes específicos do Sofia's Assistant antes de qualquer cópia; não usar o repositório como dependência |

## Deferred Items

Detalhamento e aprovação de TB-02 a TB-08; integração Memory; voz; providers/conexões completos; capacidades externas; confirmações e execution journal para side effects; tarefas duráveis multietapa; fallback automático (DEFERRED); decisão definitiva de UI/bridge após evidência da prova completa; instalador e acesso remoto.

## Completion Evidence

**Product Done requer, cumulativamente:**

1. Evidências automatizadas dos comportamentos críticos e resultados dos testes documentados.
2. Evidência de chamada real à OpenAI e streaming, sem divulgar a chave ou dados sensíveis.
3. Captura/registro da validação humana de histórico, continuidade, falhas e encerramento.
4. Registro dos achados técnicos da prova da UI e das pendências ainda abertas para voz/confirmações.
5. Código e documentação versionados no repositório JARVIS; critérios `TB01-AC01..08` verificados.

**Implementação realizada e validação funcional concluída em 2026-10-31.** Evidências, limitações e rastreabilidade: `docs/implementation/TB-01-Validation.md`. Merge na `main` continua sujeito à aprovação.

---

## 3. Project State e próximo passo legítimo

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | 08 — Technical Backlog |
| **Current artifact** | `docs/product-manager/08-JARVIS-Technical-Backlog.md` |
| **Current Slice** | TB-01 — PRODUCT DONE; PR para revisão/merge |
| **Next legitimate step** | Revisar PR do TB-01 e obter autorização para merge; TB-02 exige planejamento e aprovação próprios |
| **Forbidden inference** | TB-02 a TB-08 não estão aprovados como planos executáveis; a viabilidade da UI foi demonstrada no TB-01, mas não implica validação futura de voz e confirmações; merge não autorizado automaticamente |

*Fim de JARVIS — Technical Backlog (baseline inicial).* 

---

## 4. Registro de conclusão do TB-01 (2026-10-31)

O estado **NOT STARTED** nas seções originais de planejamento foi substituído por **PRODUCT DONE** após execução e evidência. O registro completo e as limitações estão em `docs/implementation/TB-01-Validation.md`. Este adendo não autoriza merge, não altera os Slices futuros e não aprova nova stack.


---

## 5. Handoff de execução TB-02 (2026-10-31)

O proprietário aprovou o Slice TB-02 após detalhamento do escopo; a instância HTTPS real do Sofias Memory v0.7.0 retornou `api_contract_version=1`, `contracts.cognitive_memory=1` e cinco capabilities cognitivas, sem ausências. A integração de conexão e diagnóstico foi validada na VPS; a suíte local passou com **55 testes**, antes do incremento de escrita controlada. A consulta cognitiva `global` sobre cor preferida retornou `NO_RESULTS`, o que é um resultado vazio válido e não prova ausência em outros escopos ou Knowledge.

Implementação de Cognitive Memory está em andamento na branch `feat/tb-02-memory-knowledge`: adapter dos cinco métodos, leitura por CLI e criação explícita mediante confirmação e journal operacional local. **Novos testes e criação real ainda exigem validação pelo proprietário; não declarar Product Done.** Documento de execução: `docs/implementation/TB-02-Cognitive-Adapter.md`.


---

## 6. Atualização factual TB-02 — ciclo cognitivo validado (2026-10-31)

Este adendo registra execução posterior à baseline inicial sem reabrir
a aprovação do roadmap e sem autorizar merge ou TB-03.

- **Cognitive Memory:** Create/Get/Recall global, contexto em chat e
  desktop, Supersede e Forget de amostras temporárias concluídos
  contra o Sofias Memory v0.7.0. Um par A→B foi esquecido separadamente
  com tombstones sem conteúdo e sem escopo ativo. Memória pessoal
  \`global/profile\` (preferência teal) permaneceu ativa e intacta.
- **Segurança operacional:** confirmação textual por operação, journal
  SQLite de idempotência, allowlist local e verificação de proveniência
  no serviço antes de mudar memórias temporárias.
- **Validação:** o proprietário reportou \`127 passed in 3.90s\` no Windows
  após a correção do teste multiline. Build frontend anterior também
  havia passado (\`vite build\`).
- **Knowledge Retrieval:** adapter CLI para dataset discovery e recall
  em modo chunks implementado, mas os quatro datasets reais listados
  estavam \`deleted\`; ainda não há evidência de recuperação com
  referências de um dataset ativo.
- **Estado:** TB-02 **IN PROGRESS** até evidência documental e critérios
  restantes. TB-03 a TB-08 não estão autorizados para implementação.
  \`main\` não foi alterada.
- **Registro detalhado:** \`docs/implementation/TB-02-Supersede-Forget-Smoke.md\`.

**Próximo passo legítimo:** escolher com o proprietário um documento
real, não sensível, e um dataset ativo no Sofias Memory (ou aprovar
expressamente sua criação/ingestão), então validar a cadeia documental
de trechos e proveniência sem introduzir memória cognitiva artificial.


## 7. TB-02 — autorização documental e incremento ADR-0001

Proprietário autorizou explicitamente criar um dataset no Sofias Memory e ingerir um ADR não sensível do repositório para completar a validação de Knowledge Retrieval. Dataset fixo `jarvis-knowledge`; somente a seção ADR-0001 do arquivo aprovado `docs/product-manager/07-JARVIS-ADRs.md`; comandos confirmados e sem retry automático. Foram implementados adapter e testes offline para Dataset Create, Remember `mode=full` (Run assíncrono), inspeção de Run, contadores e recuperação com proveniência. **Execução e validação reais na VPS pendentes**. Sem merge na `main`, sem avanço para TB-03. Roteiro: `docs/implementation/TB-02-ADR-Knowledge-Validation.md`.

## 9. TB-02 — Knowledge no contexto do chat (implementação CLI)

A validação real da consulta documental ao ADR-0001 retornou
`RESULTS_FOUND` com Query ID
`a7a09ded-706f-4627-8772-39d27bcf7651`, contexto e referência
com os mesmos Source/Document/Chunk IDs. O retrieval do dataset
`jarvis-knowledge` está **validado no CLI documental**.

Incremento seguinte implementado na branch: provider
`KnowledgeAwareTextProvider` com opt-in exclusivo via
`--chat --use-knowledge --knowledge-dataset jarvis-knowledge`.
A composição preserva o histórico operacional do SQLite, trata
documentos como evidência de baixa confiança e limita a contextualização
ao dataset ativo de nome esperado, com referências ligadas ao contexto.

Os testes offline do novo fluxo foram adicionados, mas aguardam
validação Windows do proprietário. O smoke real conversacional e
a integração do desktop ainda são pendentes. **TB-02 IN PROGRESS**;
nenhuma autorização de merge ou avanço ao TB-03.

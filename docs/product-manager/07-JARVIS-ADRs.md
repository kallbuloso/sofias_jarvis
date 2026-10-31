# JARVIS — Architecture Decision Records (ADRs)

| Campo | Valor |
|---|---|
| **Projeto** | JARVIS — assistente pessoal universal |
| **Fase** | 07 — Architecture Decision Records |
| **Status** | **ACCEPTED** — ADR-0001 a ADR-0006 aprovados explicitamente pelo proprietário |
| **Data** | 2026-10-30 |
| **Papel predominante** | Software Architect |
| **Destino no repositório** | `docs/product-manager/07-JARVIS-ADRs.md` |
| **Baseline** | Discovery, Product Definition, PRD, Specs, Contracts e Architecture (fases 01–06, APPROVED) |
| **Natureza** | Registro histórico sintético de decisões arquiteturais duráveis; não altera Specs, Contracts nem Architecture; não é autorização de implementação |

> **Regra de fidelidade:** cada ADR documenta uma decisão já aprovada, seu motivo, alternativas e consequências. Termos **candidatos**, **OPEN** e **DEFERRED** preservam esses estados. Mudança arquitetural material requer novo ADR e avaliação explícita de supersessão; não se reescreve uma decisão histórica aceita para alterar seu significado.

## Índice

| ADR | Assunto | Estado | Base |
|---|---|---|---|
| [ADR-0001](#adr-0001--modular-monolith-as-the-jarvis-core-architecture) | Modular Monolith | ACCEPTED | ARCH-01 |
| [ADR-0002](#adr-0002--operational-persistence--recovery) | Operational Persistence & Recovery | ACCEPTED | ARCH-02 e ARCH-05 |
| [ADR-0003](#adr-0003--protected-execution--trust-boundaries) | Protected Execution & Trust Boundaries | ACCEPTED | ARCH-03 |
| [ADR-0004](#adr-0004--local-first-desktop-deployment) | Local-first Desktop Deployment | ACCEPTED | ARCH-04 |
| [ADR-0005](#adr-0005--python-core-technology-baseline) | Python Core Technology Baseline | ACCEPTED (com ajuste expresso) | ARCH-05 |
| [ADR-0006](#adr-0006--contract-driven-provider-architecture) | Contract-Driven Provider Architecture | ACCEPTED | ARCH-06 |

---

# ADR-0001 — Modular Monolith as the JARVIS Core Architecture

**Status:** ACCEPTED  
**Date:** 2026-10-30

## Context

O MVP do JARVIS coordena conversação, tarefas, inferência, memória cognitiva, voz, integrações e operações externas autorizadas. Precisa manter autoridade operacional coerente e evitar tanto o acoplamento sem limites quanto a complexidade distribuída prematura. O produto é independente do Sofia's Assistant e atende inicialmente um proprietário por instalação.

## Decision

**Adotar Modular Monolith para o JARVIS Core, com Ports & Adapters nas fronteiras contratuais reais.** Conversas e contexto, tarefas e orquestração, políticas e execução, conexões e capacidades, auditoria e recursos, e coordenação de providers são responsabilidades lógicas — não serviços, pacotes ou processos necessariamente distintos.

O Core mantém a autoridade sobre conversas, tarefas, autorizações e execução. A interface transmite solicitações e exibe estado; adapters traduzem contratos sem conceder autoridade. O Sofias Memory permanece serviço independente para conhecimento e memória cognitiva. Modularidade lógica não equivale a isolamento de segurança: código executável não confiável exige proteção efetiva.

## Alternatives Considered

- **Monólito convencional:** implantação simples, mas risco de acoplamento entre responsabilidades críticas.
- **Modular Monolith (selecionado):** separação funcional sem infraestrutura distribuída obrigatória.
- **Microsserviços:** implantação e escala independentes, porém custo operacional injustificado para o MVP.

## Rationale

Um núcleo coeso simplifica coordenação de estado e autoridade. Fronteiras explícitas protegem a possibilidade de substituir integrações. Não serão criadas camadas abstratas ou processos separados apenas para satisfazer um padrão arquitetural.

## Consequences

- **Positive:** implantação simples, ownership claro, evolução incremental e melhor testabilidade das fronteiras.
- **Negative:** requer disciplina de dependências; falhas e recursos podem ser compartilhados no mesmo processo.
- **Trade-offs:** menor independência de implantação em troca de menor complexidade; extensões não confiáveis não obtêm privilégios irrestritos por estarem em um módulo.

## Compatibility / Migration Impact

Não migrar nem incorporar integralmente o Sofia's Assistant; reutilizar componentes apenas após auditoria. O Core não deve depender da UI nem das implementações internas do Sofias Memory. Extração futura de componentes exige decisão arquitetural justificada. Estruturas de diretórios e nomes de classes permanecem escolhas locais, não normativas.

## Related Documents

`02-JARVIS-Product-Definition.md`; `03-JARVIS-PRD.md`; `04-JARVIS-Specs.md`; `05-JARVIS-Contracts.md`; `06-JARVIS-Architecture.md` (ARCH-01).

---

# ADR-0002 — Operational Persistence & Recovery

**Status:** ACCEPTED  
**Date:** 2026-10-30

## Context

Conversas, tarefas, confirmações e operações externas devem sobreviver a falhas. Uma resposta perdida após uma ação externa não prova que a ação falhou.

## Decision

**SQLite será a autoridade de persistência operacional do MVP**, com estado transacional, **Execution Journal durável antes de cada despacho externo protegido** e recuperação conservadora. O JARVIS mantém estado e auditoria próprios, separados do Sofias Memory. Transições críticas exigem durabilidade e controle de concorrência.

## Alternatives Considered

Snapshots simples não oferecem rastreabilidade suficiente; um banco-servidor obrigatório ampliaria a infraestrutura local; Event Sourcing integral acrescentaria complexidade sem necessidade demonstrada.

## Rationale

O MVP é local-first e single-owner. Precisamos de integridade operacional e recuperação segura, não de uma plataforma distribuída de eventos.

## Consequences

- **Positive:** implantação simples, estado recuperável e auditoria das tentativas.
- **Negative:** exige disciplina transacional, manejo de concorrência, migrações e backups.
- **Trade-offs:** não existe promessa universal de *exactly-once* em serviços externos. Resultado `UNKNOWN` não autoriza repetição automática insegura; indisponibilidade da persistência bloqueia novos efeitos protegidos.

## Compatibility / Migration Impact

Sem transações distribuídas com providers ou Sofias Memory. ORM, migrações, locks, política de retenção e backup serão concretizados e validados nos Slices apropriados; nenhum mecanismo auxiliar substitui a autoridade operacional do SQLite.

## Related Documents

`06-JARVIS-Architecture.md` (ARCH-02 e ARCH-05); SPEC-01/02/10; CONTRACT-01/02/06.

---

# ADR-0003 — Protected Execution & Trust Boundaries

**Status:** ACCEPTED  
**Date:** 2026-10-30

## Context

Modelos, documentos, agentes e extensões podem propor operações, mas seus conteúdos e declarações não são autorização para produzir efeitos externos.

## Decision

**Centralized Policy Enforcement + Protected Execution Gateway + isolamento proporcional ao risco.** Toda operação executável passa pela admissão controlada do Core, com validação de alvo, conexão, parâmetros, autoridade, limites, confirmação quando necessária e registro durável pré-despacho.

## Alternatives Considered

Delegar políticas aos providers cria caminhos divergentes; exigir sandbox idêntico para todos os componentes adiciona complexidade e não constitui, por si só, garantia universal.

## Rationale

Uma autoridade única impede bypass por tools, agents, skills, providers ou conteúdo recuperado. Confirmações ficam vinculadas à operação efetiva.

## Consequences

- **Positive:** segurança auditável, controle de efeitos e fronteira consistente.
- **Negative:** validações adicionais e necessidade de provar isolamento de código executável não confiável.
- **Trade-offs:** adapters confiáveis podem integrar o Core; plugins não confiáveis ficam sem execução privilegiada enquanto não existir isolamento comprovado. Transcrição de voz isolada não comprova autorização segura.

## Compatibility / Migration Impact

Mecanismos concretos de políticas, credenciais, isolamento e confirmação por voz permanecem a validar. Dados e memória nunca modificam a política operacional.

## Related Documents

`06-JARVIS-Architecture.md` (ARCH-03); SPEC-01/06/07/10; CONTRACT-01/04/05/06/07.

---

# ADR-0004 — Local-first Desktop Deployment

**Status:** ACCEPTED  
**Date:** 2026-10-30

## Context

O MVP precisa operar em um dispositivo pessoal, usar recursos locais de áudio e preservar tarefas e histórico sem depender de um backend cloud próprio.

## Decision

**Desktop local-first para Windows, com Windows 11 como primeira plataforma de validação.** Core e estado operacional pertencem à instalação local. Sofias Memory, modelos e integrações podem ser acessados local ou remotamente conforme contrato e configuração.

## Alternatives Considered

Cloud-first amplia dependência de infraestrutura e conectividade; Core local/remoto distribuído implica sincronização e recuperação adicionais não exigidas para o MVP.

## Rationale

Reduzir a matriz inicial de implantação e manter autoridade operacional sob controle da instalação.

## Consequences

- **Positive:** operação local coesa, menos serviços obrigatórios, facilidade de validação no ambiente-alvo.
- **Negative:** depende do ciclo de vida e dos recursos do dispositivo; capacidades remotas continuam sujeitas à rede.
- **Trade-offs:** não implica funcionamento totalmente offline nem execução permanente em background. Fechamento da UI, encerramento da voz e encerramento do Core são eventos distintos.

## Compatibility / Migration Impact

Linux/macOS, acesso remoto, sincronização e distribuição final não fazem parte do compromisso inicial. O Core não exporá comandos privilegiados à rede pública por padrão.

## Related Documents

`06-JARVIS-Architecture.md` (ARCH-04); PRD-01/05/06/07; CONTRACT-05/06.

---

# ADR-0005 — Python Core Technology Baseline

**Status:** ACCEPTED — aprovado com exclusão expressa de outras linguagens da proposta de stack  
**Date:** 2026-10-30

## Context

O JARVIS exige integração com inferência, voz, ferramentas e desktop Windows, com possibilidade de reutilização seletiva de componentes existentes e implantação local simples.

## Decision

**Python é a linguagem principal escolhida para o JARVIS Core no MVP.** A versão exata do Python ainda depende de teste de compatibilidade; Python 3.13 é apenas a candidata inicial. A instalação do Sofias Memory mantém seu runtime independente.

A escolha não determina a linguagem das tecnologias de interface ou de build. **A proposta aceita não inclui outras linguagens candidatas para o Core.** A comparação histórica da ARCH-05 não é reaberta nem reescrita.

## Alternatives Considered

As alternativas foram registradas e avaliadas na ARCH-05; este ADR não as incorpora à stack escolhida, conforme aprovação expressa do proprietário.

## Rationale

Aderência às responsabilidades de IA, voz e automação e viabilidade de reaproveitamento seletivo, sem tornar o Sofia's Assistant uma dependência do JARVIS.

## Consequences

- **Positive:** menor fricção para os componentes centrais e integração com bibliotecas disponíveis.
- **Negative:** exige validar versões, concorrência, ambiente reprodutível e distribuição Windows.
- **Trade-offs:** PySide6 + Vue 3/Vuetify 3 e Qt WebChannel são **candidatos condicionados a prova técnica**, não decisões definitivas. SQLite é decisão registrada no ADR-0002 e não uma nova escolha neste ADR.

## Compatibility / Migration Impact

Auditar componentes antes de reutilização. Não sincronizar versões de Python entre serviços independentes. A interface final dependerá de validação separada.

## Related Documents

`06-JARVIS-Architecture.md` (ARCH-05); ARCH-R01/02; OQ-03/04/08; ADR-0002.

---

# ADR-0006 — Contract-Driven Provider Architecture

**Status:** ACCEPTED  
**Date:** 2026-10-30

## Context

O JARVIS deve integrar múltiplos serviços e contas sem adicionar regras próprias de cada domínio ao Core ou transferir autoridade a providers externos.

## Decision

**Adapters especializados + Provider Registry explícito + seleção de capacidades compatíveis + execução autorizada pelo Core.** Distinguir Provider, Connection e Capability. O Sofias Memory utiliza adapter dedicado conforme seus contratos; modelos, voz e ferramentas seguem seus respectivos contratos.

O desenho **prevê fallback opcional** de providers compatíveis. **Fallback automático completo permanece DEFERRED**, não obrigatório para configurar ou aprovar o MVP.

## Alternatives Considered

Integrações codificadas diretamente no Core aumentam acoplamento; protocolo único obrigatório ou instalação dinâmica de plugins antecipam complexidade sem necessidade comprovada.

## Rationale

Preservar substituibilidade dos serviços, clareza de escopo, segurança e a possibilidade de evoluir seleção e fallback quando houver casos reais.

## Consequences

- **Positive:** evolução de providers sem regras de domínio no Core; suporte a conexões independentes.
- **Negative:** adapters precisam declarar e validar capacidades, permissões e compatibilidade.
- **Trade-offs:** disponibilidade não é autorização. Fallback respeitará privacidade, custo, capacidades e estado anterior; **nunca** repetirá automaticamente uma operação WRITE/CRITICAL com resultado desconhecido.

## Compatibility / Migration Impact

Começar com adapters confiáveis registrados explicitamente; nenhum marketplace ou instalação autônoma de plugins é exigido no MVP. Providers concretos e dois domínios externos de validação ainda precisam ser selecionados. A compatibilidade real da API do Sofias Memory precisa ser auditada.

## Related Documents

`06-JARVIS-Architecture.md` (ARCH-06 e emenda de fallback); CONTRACT-01–CONTRACT-07; ARCH-R04/05/08.

---

# Revisão de consistência da Fase 07

| Verificação | Resultado |
|---|---|
| **ADR-0001–0006** | ACCEPTED por decisão explícita do proprietário |
| **Tecnologia principal** | Python para Core; SQLite como armazenamento operacional |
| **Interface** | PySide6 + Vue 3/Vuetify 3 e Qt WebChannel permanecem candidatos sujeitos à prova técnica |
| **Reutilização** | Seletiva, após auditoria; JARVIS independente do Sofia's Assistant |
| **Sofias Memory** | Serviço independente, somente autoridade cognitiva/de conhecimento |
| **Segurança** | Core autoriza; providers não concedem autoridade; execução requer persistência durável |
| **Fallback** | Possibilidade arquitetural aprovada; automação completa DEFERRED |
| **Open/Deferred** | Preservados conforme PRD, Specs, Contracts e Architecture |

## Pendências que não bloqueiam o registro dos ADRs

Persistem as pendências da Architecture, especialmente: prova da interface (ARCH-R01); compatibilidade de runtime (ARCH-R02); proteção de credenciais (ARCH-R03); API real do Sofias Memory (ARCH-R04); dois domínios externos (ARCH-R05); retenção/backup (ARCH-R06); confirmações por voz (ARCH-R07); fallback automático pós-MVP (ARCH-R08). Serão resolvidas antes das implementações ou validações dependentes.

## Project State

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | 07 — ADRs: seis registros ACCEPTED, documentação consolidada |
| **Current role** | Software Architect |
| **Approved baseline** | Fases 01–06; ADR-0001–ADR-0006 |
| **Current artifact** | `docs/product-manager/07-JARVIS-ADRs.md` |
| **Current Slice** | Nenhum Slice de implementação aprovado |
| **Next legitimate step** | 08 — Technical Backlog, após o proprietário salvar este documento; planejar o menor Slice vertical utilizável, sem implementar sem aprovação |

*Fim de JARVIS — Architecture Decision Records.*

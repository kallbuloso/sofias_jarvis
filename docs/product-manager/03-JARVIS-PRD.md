# JARVIS — Product Requirements Document (PRD)

| Campo | Valor |
|---|---|
| **Produto** | JARVIS — assistente pessoal universal |
| **Fase** | 03 — Product Requirements Document |
| **Status** | **APPROVED** — PRD-01 a PRD-11 aprovados individualmente pelo proprietário |
| **Data da consolidação** | 2026-10-28 |
| **Papel predominante** | Product Engineer / Technical Product Manager |
| **Baseline anterior** | `docs/product-manager/01-JARVIS-Discovery.md` — APPROVED; `docs/product-manager/02-JARVIS-Product-Definition.md` — APPROVED |
| **Destino no repositório** | `docs/product-manager/03-JARVIS-PRD.md` |
| **Natureza** | Requisitos de produto verificáveis; **não** é especificação técnica, contrato, ADR, arquitetura ou autorização para implementação |

> **Regra de fidelidade:** este documento consolida as decisões **PRD-01 a PRD-11** aprovadas, preservando os IDs **FR-001–FR-073**, **NFR-001–NFR-010**, **AC-001–AC-008**, **RISK-01–RISK-07** e **OQ-01–OQ-08**, além de exceções e critérios de aceitação por bloco. As decisões `OPEN` e `DEFERRED` **não** constituem escolhas técnicas aprovadas. Requisitos futuros **não** entram automaticamente no MVP. Os documentos anteriores continuam sendo baselines válidos e complementares.

## 0. Resumo executivo e linguagem normativa

**Visão aprovada:**

> JARVIS é um assistente pessoal universal, inteligente, persistente e extensível, capaz de compreender solicitações em linguagem natural, manter continuidade contextual, utilizar conhecimento e ferramentas externas, planejar e executar atividades autorizadas e propor a evolução de suas próprias capacidades sob supervisão do usuário.

O problema abordado é a fragmentação de aplicações, informações e tarefas: o usuário precisa reconstruir contexto, conectar recursos, coordenar etapas e acompanhar pendências manualmente. O JARVIS deve permitir que ele expresse objetivos e obtenha **resultados observáveis**, preservando sua autoridade sobre operações externas.

**Resultados que o MVP deverá comprovar:** (A) continuidade de conversa e memória; (B) extensibilidade real por pelo menos **dois domínios externos distintos**, sem lógica de domínio no Core; (C) execução efetiva de operação externa autorizada, acompanhada e verificável.

**Leitura das prioridades:**

- **MUST:** obrigatório dentro do escopo a que o requisito se refere; os MUST funcionais listados neste documento pertencem ao baseline do MVP.
- **SHOULD:** esperado/desejável, com exceções justificáveis; **FR-025 é SHOULD e sua implementação integral é pós-MVP**.
- **FUTURE / DEFERRED:** capacidade preservada na visão, mas **não** exigida para aprovar o MVP.
- **OPEN:** escolha ainda não realizada; deve ser resolvida antes da implementação ou validação que dela dependa.
- **OUT OF SCOPE (Core):** responsabilidade que o núcleo universal não deve assumir, mesmo que um plugin externo ofereça a capacidade correspondente.

**Atores:** (1) proprietário único por instalação no MVP, que define objetivos e aprova operações; (2) JARVIS, responsável pela interpretação, coordenação, política e execução; (3) ferramentas/serviços externos, que fornecem dados e operações; (4) Sofias Memory, responsável por persistir e recuperar memória, conhecimento e definições declarativas, **sem executar operações**. Agentes especializados são capacidades subordinadas ao JARVIS, não usuários ou autoridades independentes.

**Fronteira central:** o JARVIS administra histórico de conversas, contexto de execução, tarefas, confirmações, autorizações, auditoria e recuperação operacional. O Sofias Memory administra memória cognitiva, conhecimento, referências, proveniência e definições/configurações declarativas de skills e agentes. Informação recuperada **nunca confere autoridade**. A persistência operacional do JARVIS não deve ser confundida com memória cognitiva.

### 0.1 Fluxo universal e adaptativo (baseline PD-05)

1. Receber pedido por texto, voz ou canal disponível.
2. Entender intenção e contexto; esclarecer ambiguidades relevantes.
3. Identificar se basta responder, consultar ferramentas ou organizar uma atividade de múltiplas etapas.
4. Avaliar adequação, risco e autoridade da operação pretendida.
5. Responder ou executar somente ações autorizadas.
6. Apresentar o resultado real, suas evidências, falhas, incertezas e pendências; preservar continuidade segundo as políticas adequadas.

Esse fluxo **não** implica seis chamadas fixas de IA; pode voltar a etapas anteriores e não exige agentes para operações simples. O Core não implementa fluxos de assistência técnica, CRM, e-commerce ou outros domínios particulares.

---

## PRD-01 — Conversação Unificada e Continuidade — APPROVED

### Propósito

Conversa por texto e voz no **mesmo contexto**, com histórico persistente e retomada após encerramento. A modalidade é uma forma de interação, não uma sessão isolada. A interface deve comunicar estados relevantes. Tecnologias de STT/TTS, wake word, captura contínua e layout permanecem abertas.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-001** | MUST | O usuário deve poder conversar com o JARVIS por texto e voz. |
| **FR-002** | MUST | Voz e texto devem compartilhar o contexto da mesma conversa, sem criar sessões independentes por modalidade. |
| **FR-003** | MUST | O histórico das conversas deve persistir entre encerramentos e reinicializações da aplicação. |
| **FR-004** | MUST | O usuário deve conseguir iniciar uma nova conversa, consultar conversas anteriores e retomá-las. |
| **FR-005** | MUST | O JARVIS deve distinguir o histórico da conversa das informações cognitivas recuperadas pelo Sofias Memory. |
| **FR-006** | MUST | Falhas de reconhecimento de voz ou indisponibilidade de recursos de áudio não devem impedir a interação por texto. |
| **FR-007** | MUST | O usuário deve conseguir identificar quando o JARVIS está recebendo uma entrada de voz, processando uma solicitação ou produzindo uma resposta. |

### Regras, exceções e comportamento observado

- O usuário pode iniciar em texto e continuar por voz, ou o inverso, **na mesma conversa**.
- Retomar conversa anterior implica disponibilizar seu histórico persistido; o JARVIS pode consultar o Sofias Memory quando isso for relevante, mas não inventará detalhes ausentes.
- Criar nova conversa não deve apagar as anteriores nem tratar memórias cognitivas como se fossem mensagens daquele histórico.
- Falha de microfone, transcrição ou síntese de voz não inviabiliza o texto.
- Exemplo de jornada: conversar sobre servidores por texto → perguntar por voz “dessas opções” → encerrar → reabrir o tópico e continuar sem reconstruir manualmente todo o contexto, desde que as informações estejam disponíveis.

### Critérios de aceitação do bloco

1. Iniciar por texto e prosseguir por voz, preservando assunto e referências disponíveis.
2. Encerrar/reiniciar a aplicação e retomar uma conversa anterior.
3. Criar conversa nova sem perder históricos anteriores.
4. Utilizar texto quando recursos de áudio falharem.
5. Diferenciar contexto conversacional de informações recuperadas da memória.

---

## PRD-02 — Memória Cognitiva e Recuperação de Conhecimento — APPROVED

### Propósito

Permitir que o JARVIS se lembre de informações relevantes, recupere evidências e conhecimentos anteriores e use experiências para adaptar respostas e propostas, **sem confundir aprendizado com automodificação do Core nem concessão de permissão**.

### Categorias e responsabilidades

| Categoria | Proprietário funcional | Conteúdo exemplar |
|---|---|---|
| **Conversation History** | JARVIS | Mensagens e eventos de uma conversa concreta. |
| **Cognitive Memory** | Sofias Memory | Preferências, fatos, decisões e informações persistentes. |
| **Knowledge Memory** | Sofias Memory | Documentos, conteúdos, entidades, relações, fontes e referências de conhecimento. |

Nem toda mensagem vira memória permanente. O JARVIS diferencia **registrar** informação relevante, **recordar** o que já está persistido e **aprender** no sentido de adaptar decisões/propostas com base em experiências. O aprendizado não autoriza reescrever código, modificar modelos ou ampliar permissões. A política de gravação automática, incluindo tratamento de dados transitórios ou sensíveis, será especificada antes de ser habilitada.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-008** | MUST | O JARVIS deve integrar-se ao Sofias Memory para persistir e recuperar informações cognitivas. |
| **FR-009** | MUST | O JARVIS deve recuperar informações relevantes de conversas anteriores sem exigir que o usuário as repita. |
| **FR-010** | MUST | O usuário deve conseguir solicitar explicitamente que uma informação seja lembrada, atualizada ou esquecida. |
| **FR-011** | MUST | O JARVIS deve conseguir consultar conhecimento persistido, incluindo documentos e informações estruturadas disponíveis no Sofias Memory. |
| **FR-012** | MUST | As informações recuperadas devem preservar referências e identificação de origem quando disponibilizadas pelo Sofias Memory. |
| **FR-013** | MUST | Informações recuperadas devem ser utilizadas de acordo com seu contexto, escopo e relevância, evitando misturar fatos de projetos ou assuntos diferentes. |
| **FR-014** | MUST | O JARVIS não deve tratar memórias, documentos ou resultados de ferramentas como autorização para executar operações. |
| **FR-015** | MUST | A indisponibilidade do Sofias Memory não deve impedir funcionalidades independentes dele; o usuário deverá ser informado quando essa indisponibilidade afetar a resposta. |
| **FR-016** | MUST | O JARVIS deve distinguir informações confirmadas, inferidas, desatualizadas ou insuficientes, quando houver evidências para essa distinção. |

### Regras, exceções e comportamento observado

- Para recuperar uma decisão anterior, identificar o projeto correto, consultar informações pertinentes, avaliar a evidência e responder com referências **quando disponíveis**; se não houver suporte, explicitar insuficiência, sem inventar justificativas.
- Uma informação substituída não pode permanecer apresentada como verdade atual; uma memória esquecida não deve voltar como memória ativa.
- O JARVIS não deve assumir que o Sofias Memory implementa hoje todos os contratos necessários: compatibilidade real deve ser verificada nas etapas técnicas.
- **Definições declarativas** de skills e agentes podem ser mantidas no Sofias Memory. Sua criação dinâmica completa não é obrigação do MVP; a execução, ativação e autorização pertencem exclusivamente ao JARVIS.
- Propor o registro de uma informação útil é permitido; isso não estabelece autorização para persistir automaticamente todo dado ou informação sensível.

### Critérios de aceitação do bloco

1. Registrar e recuperar uma informação entre conversas.
2. Atualizar uma informação e deixar de apresentá-la como fato atual anterior.
3. Esquecer uma informação e não recuperá-la como memória ativa.
4. Responder usando documento/conhecimento persistido, com fontes quando disponibilizadas.
5. Informar falta de evidência em vez de inventar conclusão.
6. Continuar a conversa independente quando o serviço de memória estiver indisponível, informando a limitação relevante.
7. Demonstrar que memória e conteúdo externo não autorizam operações.

---

## PRD-03 — Descoberta e Seleção de Capacidades — APPROVED

### Propósito e vocabulário

O JARVIS identifica capacidades utilizáveis e escolhe ferramentas pertinentes à intenção em linguagem natural, sem exigir do usuário comandos técnicos nem codificar regras de domínios particulares no Core.

| Conceito | Papel no produto |
|---|---|
| **Capability** | Habilidade declarada que o assistente pode disponibilizar. |
| **Tool** | Operação concreta, de leitura ou alteração. |
| **Plugin** | Agrupamento de capacidades relacionadas. |
| **Skill** | Conhecimento/procedimento que orienta uma atividade. |
| **Agent** | Coordenação especializada de um objetivo, com etapas quando necessário. |
| **Channel** | Meio de receber pedidos e entregar respostas. |
| **Registry** | Meio de identificar/consultar capacidades presentes e utilizáveis; não impõe componente técnico específico. |

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-017** | MUST | O JARVIS deve identificar as capacidades instaladas, configuradas e disponíveis para utilização. |
| **FR-018** | MUST | O JARVIS deve selecionar ferramentas relevantes à intenção e ao contexto do usuário, sem depender de comandos técnicos explícitos. |
| **FR-019** | MUST | O JARVIS deve conseguir utilizar ferramentas de diferentes domínios sem incorporar regras de negócio específicas dessas aplicações ao Core. |
| **FR-020** | MUST | O JARVIS deve considerar disponibilidade e permissões ao selecionar capacidades, sem tratar a seleção como autorização para execução. |
| **FR-021** | MUST | Quando uma solicitação exigir múltiplas ferramentas, o JARVIS deve conseguir identificá-las e coordenar sua utilização conforme a necessidade. |
| **FR-022** | MUST | Quando não existir uma capacidade adequada, o JARVIS deve informar a limitação, sem inventar resultados ou simular execuções. |
| **FR-023** | MUST | O JARVIS deve permitir que novas capacidades compatíveis sejam disponibilizadas sem alterações nas regras específicas de domínio do Core. |
| **FR-024** | MUST | O usuário deve conseguir identificar quais integrações estão habilitadas, indisponíveis ou sem autorização suficiente. |
| **FR-025** | **SHOULD — pós-MVP** | O JARVIS poderá localizar alternativas externas e preparar propostas de novas integrações, sem instalação ou ativação não autorizada. |

### Regras, exceções e comportamento observado

- **MVP:** descobrir, selecionar e combinar ferramentas já existentes, adequadamente conectadas/habilitadas, respeitando permissões. Validar ao menos dois domínios externos reais.
- **Futuro supervisionado:** investigar recursos ausentes, pesquisar plugins/skills/agentes e preparar propostas, sem instalar, habilitar, conectar contas ou ampliar autoridade silenciosamente.
- Uma pergunta simples não exige Agent. Um pedido composto poderá combinar, por exemplo, ferramentas de agenda e e-mail em uma resposta consolidada.
- Ferramenta ausente: explicar a lacuna; ferramenta fora do ar: declarar a falha, não falsificar atualização; permissão insuficiente: não contornar usando uma segunda ferramenta.
- Ferramentas equivalentes: selecionar conforme contexto/permissões, pedindo esclarecimento quando houver consequências ou ambiguidade relevante.
- Falha parcial: aproveitar dados válidos das demais ferramentas, distinguindo claramente o que não foi concluído.
- **MCP não foi aprovado como protocolo obrigatório.** O mecanismo de extensão será decidido depois.

### Critérios de aceitação do bloco

1. Selecionar uma tool pelo pedido em linguagem natural, sem indicar seu nome técnico.
2. Utilizar capacidades de dois domínios distintos.
3. Disponibilizar nova integração compatível sem embutir regras específicas do domínio no Core.
4. Informar ferramenta ausente e serviço indisponível sem inventar operação.
5. Não executar diante de permissão insuficiente, inclusive por ferramenta alternativa não autorizada.
6. Coordenar consulta composta e distinguir resultados completos de parciais.

---

## PRD-04 — Execução de Ferramentas, Autorizações e Confirmações — APPROVED

### Propósito

Permitir ações reais, controladas, verificáveis e proporcionais ao risco. **Escolher uma ferramenta não significa possuir autoridade para executá-la.** As verificações são igualmente aplicáveis a solicitações diretas, tasks, agents, skills e plugins.

### Categorias funcionais (não são níveis técnicos de ACL)

| Tipo | Exemplo | Regra |
|---|---|---|
| Consulta | Ler agenda ou dados externos | Requer acesso de leitura autorizado. |
| Preparação | Produzir localmente um rascunho | Não deve produzir efeito externo não autorizado. |
| Alteração externa | Enviar mensagem, criar evento, modificar registro | Requer autorização compatível com alvo e efeito. |
| Operação crítica | Excluir informação importante ou alterar permissões sensíveis | Requer aprovação explícita e controles adicionais. |

Uma leitura pode expor dado sensível; criar rascunho **dentro de serviço externo** pode ser alteração. A classificação deve considerar efeitos efetivos, não apenas verbos.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-026** | MUST | Toda execução de ferramenta deve passar por verificação de autorização antes de realizar a operação. |
| **FR-027** | MUST | O JARVIS deve distinguir operações de consulta, preparação, alteração externa e operações críticas, considerando seus efeitos. |
| **FR-028** | MUST | Quando uma operação exigir confirmação, o usuário deve receber informações suficientes para compreender a ação antes de autorizá-la. |
| **FR-029** | MUST | O usuário deve conseguir aprovar ou rejeitar operações que dependam de sua confirmação. |
| **FR-030** | MUST | A autorização concedida deve valer somente para a operação e o escopo compatíveis, sem ampliação implícita de permissões. |
| **FR-031** | MUST | Agentes, skills e plugins devem respeitar as mesmas verificações de autoridade aplicadas às solicitações diretas. |
| **FR-032** | MUST | Operações rejeitadas, não autorizadas ou que não atendam aos controles necessários não devem ser executadas. |
| **FR-033** | MUST | O JARVIS deve registrar informações suficientes para permitir identificar operações solicitadas, decisões de autorização e resultados observados. |
| **FR-034** | MUST | O JARVIS deve distinguir execução confirmada, falha e resultado desconhecido, sem presumir sucesso. |
| **FR-035** | MUST | Operações com possíveis efeitos externos não devem ser repetidas automaticamente quando houver risco de duplicação ou resultado anterior desconhecido. |

### Regras, exceções e comportamento observado

- Apresentar **o que** será feito, **onde/para quem**, com qual conteúdo ou efeito relevante, antes de confirmação exigida. Aprovação de um envio a destinatário específico não autoriza outro destinatário.
- Alteração material em conteúdo, alvo ou efeito após a aprovação exige reavaliação de autoridade.
- Rejeição impede a execução, mas pode preservar rascunho/proposta para revisão.
- Não pedir confirmação para cada consulta já autorizada; confirmações são proporcionais à operação e ao risco.
- A autorização externa do serviço e a autorização operacional do JARVIS são limites **complementares**, não intercambiáveis.
- Falha de conexão após enviar pedido de alteração pode produzir **resultado desconhecido**: não declarar sucesso nem refazer automaticamente com risco de duplicação.
- Autorizações persistentes, progressivas e amplas ficam **DEFERRED**; nenhum plano ou memória concede grants.

### Critérios de aceitação do bloco

1. Consulta autorizada ocorre sem confirmação adicional desnecessária.
2. Envio que requer aprovação mostra operação, conteúdo/destino e aguarda decisão.
3. Operação rejeitada não é executada.
4. Escopo alterado ou não autorizado aciona nova validação ou bloqueio.
5. Execução iniciada por agent/skill/plugin passa pelo mesmo controle.
6. Contorno por ferramenta alternativa não permite execução indevida.
7. Falha confirmada é apresentada como falha; resultado incerto não é apresentado como sucesso.
8. Resultado desconhecido impede repetição automática insegura.
9. Histórico permite reconstruir solicitação, autorização e resultado observado.

---
## PRD-05 — Tarefas, Planejamento e Acompanhamento de Execuções — APPROVED

### Propósito

Transformar objetivos mais complexos em atividades acompanháveis, com etapas, progresso, impedimentos e continuidade operacional. **Nem toda interação vira uma tarefa formal; toda atividade que exija acompanhamento terá estado identificável.** Planejamento e agentes devem ser proporcionais à complexidade.

| Tipo | Exemplo | Comportamento |
|---|---|---|
| Resposta direta | Explicação de um conceito | Responder sem criar task acompanhável. |
| Operação pontual | Consultar próximo compromisso | Usar a tool e apresentar resultado. |
| Tarefa acompanhável | Pesquisar fornecedores, comparar e preparar relatório | Organizar etapas, progresso, resultados e pendências. |

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-036** | MUST | O JARVIS deve identificar quando uma solicitação pode ser resolvida diretamente ou precisa ser acompanhada como tarefa. |
| **FR-037** | MUST | O JARVIS deve conseguir organizar atividades de múltiplas etapas, considerando dependências e resultados necessários. |
| **FR-038** | MUST | O usuário deve conseguir consultar o estado e o progresso das tarefas acompanháveis. |
| **FR-039** | MUST | O JARVIS deve comunicar eventos relevantes da execução, incluindo etapas concluídas, impedimentos e necessidade de intervenção. |
| **FR-040** | MUST | Uma tarefa deve aguardar autorização quando uma etapa exigir aprovação ainda não concedida. |
| **FR-041** | MUST | O usuário deve conseguir solicitar a interrupção de uma tarefa em andamento, respeitando os limites técnicos e os efeitos já produzidos. |
| **FR-042** | MUST | O estado operacional necessário das tarefas acompanháveis deve persistir para permitir consulta após reinicialização da aplicação. |
| **FR-043** | MUST | O JARVIS deve avaliar a segurança de qualquer retomada após falha ou interrupção, sem repetir automaticamente operações de resultado desconhecido. |
| **FR-044** | MUST | O JARVIS deve diferenciar tarefas concluídas, interrompidas, com falha ou aguardando intervenção, preservando os resultados parciais disponíveis. |
| **FR-045** | MUST | O usuário deve conseguir consultar os resultados de tarefas anteriores sem depender exclusivamente do histórico de mensagens. |
| **FR-046** | MUST | O JARVIS deve aplicar as regras de autoridade aprovadas a cada operação realizada durante uma tarefa, inclusive quando houver várias etapas. |

### Ciclo de vida e limites

**Estados conceituais, não máquina de estados técnica fechada:** `pendente` → `em andamento` → avaliação de resultado/impedimento → `concluída` / `aguardando usuário` / `falhou` / `interrompida`. Uma tarefa que aguarda o usuário pode continuar após receber o esclarecimento ou autorização aplicável. Uma tarefa concluída não reexecuta operações só por ser consultada.

- Exemplo de jornada: identificar requisitos da hospedagem → pesquisar fornecedores → comparar preços → apresentar recomendação. Mostrar etapas efetivamente realizadas; não inventar percentuais de progresso.
- Preservar resultados parciais e comunicar exatamente o que falhou; interrupção não reverte efeitos externos já efetivados.
- Ao recuperar execução interrompida, avaliar se é seguro continuar. Resultado externo desconhecido pode exigir intervenção, em vez de repetição automática.
- O **estado de task**, operações, confirmações e recuperação pertence ao **JARVIS**, mesmo quando o Sofias Memory contenha conhecimento relacionado à tarefa.
- Scheduler recorrente avançado, monitoramento contínuo de eventos, delegação multiagente complexa e grants persistentes progressivos: **FUTURE**, não bloqueiam o MVP. Execução assíncrona de tarefas do MVP continua permitida.

### Critérios de aceitação do bloco

1. Pergunta simples respondida sem task acompanhável desnecessária.
2. Solicitação composta gera atividade com progresso consultável.
3. Etapas concluídas, pendências e impedimentos são distinguíveis.
4. A tarefa espera autorização antes de etapa protegida.
5. Usuário solicita interrupção e entende limites/efeitos.
6. Estado e resultados persistidos podem ser consultados após reinicialização.
7. Execução interrompida não repete alteração externa de resultado incerto.
8. Resultados parciais e falhas não são apresentados como tarefa concluída.
9. Histórico operacional do JARVIS é separado da memória cognitiva.

---

## PRD-06 — Experiência de Uso, Interface e Visibilidade Operacional — APPROVED

### Propósito

A conversa é o centro da experiência, mas o usuário consegue inspecionar a atividade operacional **sem precisar percorrer todo o histórico conversacional**. A interface deve permitir compreensão e controle, não exigir domínio técnico de registros internos. Uma identidade futurista é possível, porém não foi aprovado layout, tecnologia de frontend ou composição visual específica.

**Áreas funcionais (não necessariamente telas separadas):** Conversação; Atividades; Autorizações; Notificações; Configurações e Integrações.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-047** | MUST | O JARVIS deve disponibilizar uma interface para interação por texto e voz, com acesso ao histórico de conversas. |
| **FR-048** | MUST | O usuário deve conseguir identificar os estados relevantes da interação, como escuta, processamento, resposta e falha. |
| **FR-049** | MUST | A interface deve permitir consultar tarefas acompanháveis e seus estados sem depender da leitura integral do histórico de mensagens. |
| **FR-050** | MUST | O usuário deve conseguir visualizar detalhes relevantes das tarefas, incluindo etapas, resultados parciais, impedimentos e resultados finais. |
| **FR-051** | MUST | Solicitações de autorização devem apresentar a operação, seu destino ou alvo e seus efeitos relevantes antes da decisão do usuário. |
| **FR-052** | MUST | O usuário deve conseguir aprovar ou rejeitar uma solicitação de autorização pela interface. |
| **FR-053** | MUST | O usuário deve conseguir solicitar a interrupção de tarefas em andamento quando a operação permitir. |
| **FR-054** | MUST | O JARVIS deve comunicar eventos relevantes que necessitem de atenção, distinguindo informações, falhas e solicitações de intervenção. |
| **FR-055** | MUST | A interface deve permitir consultar o estado das integrações essenciais e acessar suas configurações disponibilizadas. |
| **FR-056** | MUST | A interface deve distinguir claramente operações concluídas, pendentes, não autorizadas, com falha ou de resultado desconhecido. |
| **FR-057** | MUST | O usuário deve conseguir continuar interagindo com o JARVIS enquanto consulta atividades anteriores, sem perder o contexto da conversa selecionada. |

### Regras, exceções e comportamento observado

- **Interação simples:** pedido e resposta, sem burocracia. **Acompanhamento detalhado:** etapas observáveis, tools usadas, resultados e impedimentos quando o usuário desejar.
- Não inventar porcentagem de progresso nem usar animação para sugerir conclusão sem evidência. Mostrar estados baseados em eventos reais.
- Confirmações compreensíveis devem indicar, quando aplicável, operação, destinatário/alvo, conteúdo essencial e efeito. “Permitir operação?” sem contexto não é suficiente.
- A interface deve comunicar aprovações, rejeições e situações em que a confirmação deixa de ser válida/aplicável; a modelagem precisa será feita nas etapas de especificação.
- Uma execução de task e a consulta de outra não devem eliminar a conversa atualmente selecionada.
- UI futurista e UI minimalista são **referências exploratórias**, não componentes aprovados; priorizar legibilidade, clareza, controle e facilidade de uso. **PySide6, web ou híbrida permanecem OPEN.**

### Critérios de aceitação do bloco

1. Texto/voz disponíveis e estados de interação identificáveis.
2. Tarefa consultável fora da sequência completa de mensagens.
3. Etapas concluídas, resultados parciais e impedimentos visíveis.
4. Efeitos de operações apresentadas antes de confirmação exigida.
5. Possibilidade de aprovar/rejeitar e solicitar interrupção quando aplicável.
6. Falha ou resultado desconhecido não aparentam conclusão.
7. Integrações essenciais e seus estados consultáveis.
8. Consultar tarefa anterior não apaga contexto da conversa em uso.

---

## PRD-07 — Requisitos Não Funcionais — APPROVED

### Propósito

Estabelecer qualidade observável sem fixar stack, infraestrutura, metas de latência arbitrárias ou tecnologia de isolamento antes da análise apropriada.

### Requisitos não funcionais

| ID | Prioridade | Categoria | Requisito aprovado |
|---|---|---|---|
| **NFR-001** | MUST | Segurança | A execução de ferramentas deve respeitar obrigatoriamente os controles de autorização, inclusive em caso de falha de componentes de segurança. |
| **NFR-002** | MUST | Privacidade | Credenciais e informações sensíveis não devem ser expostas indevidamente em interfaces, logs, notificações ou resultados de ferramentas. |
| **NFR-003** | MUST | Integridade | Conversas, tarefas, autorizações e resultados persistidos devem preservar consistência diante de encerramentos e falhas. |
| **NFR-004** | MUST | Recuperação | O sistema deve conseguir identificar execuções interrompidas e evitar duplicação insegura de operações externas. |
| **NFR-005** | MUST | Disponibilidade | A falha de uma integração não deve inutilizar as funcionalidades independentes dela. |
| **NFR-006** | MUST | Desempenho percebido | Operações demoradas não devem bloquear desnecessariamente a interface; o usuário deve receber indicação de atividade ou espera. |
| **NFR-007** | MUST | Auditabilidade | Operações externas devem possuir registros suficientes para reconstruir solicitações, decisões de autorização e resultados, sem expor segredos. |
| **NFR-008** | MUST | Controle de recursos | O JARVIS deve respeitar limites configurados para utilização de modelos, ferramentas e serviços que consumam recursos ou gerem custos. |
| **NFR-009** | MUST | Acessibilidade | As funcionalidades essenciais devem permitir interação por texto e controles visuais, sem depender exclusivamente de voz, cores ou animações. |
| **NFR-010** | MUST | Extensibilidade | Adicionar uma integração compatível não deve exigir alterações nas regras de negócio específicas do Core. |

### Regras de qualidade e exceções

- **Fail-closed para operações protegidas:** uma falha na verificação de autorização não pode ser interpretada como permissão. Isso alcança tools, plugins, skills, agents e tarefas.
- **Dados sensíveis:** limitar informações utilizadas à necessidade da operação autorizada e impedir a exposição indevida de segredos; política detalhada de retenção segue OPEN.
- **Persistência confiável:** recuperar o estado registrado não significa concluir operações externas nem repetir ações desconhecidas.
- **Degradação controlada:** falha em Sofias Memory, provider de IA, áudio ou conexão externa deve ser comunicada conforme o impacto, mantendo o que não depende do componente falho.
- **Responsividade/feedback/controle:** interface utilizável durante operações longas sempre que viável; indicar processamento e suportar pedido de interrupção com limites definidos.
- **Custos:** limites configuráveis e aplicados também a tasks/agents, sem criar aqui um valor monetário ou orçamento arbitrário.
- **Acessibilidade:** texto permanece possível sem microfone; estado não pode depender exclusivamente de cor; animações não são obrigatórias para entender o resultado.
- **Sem SLA inventado:** latência, CPU/RAM, sistema operacional, deployment e mecanismo de sandbox só serão definidos com base em ambiente, medidas e especificações reais.

### Critérios de aceitação do bloco

1. Verificador de autorização indisponível resulta em bloqueio de operação protegida.
2. Credencial não é revelada indevidamente em log/interface/notificação.
3. Reinício em meio a uma tarefa permite consultar estado anterior consistente.
4. Resultado incerto de alteração não gera repetição insegura.
5. Falha de Sofias Memory não impede funcionalidade independente.
6. Tarefa longa apresenta feedback sem bloquear desnecessariamente a interface.
7. Auditoria permite rastrear solicitação, autorização e resultado sem segredos.
8. Limites configurados de recursos são respeitados.
9. Falha do microfone não impede conversa textual.
10. Nova integração compatível não exige regra de domínio no Core.

---

## PRD-08 — Configuração e Gerenciamento de Integrações — APPROVED

### Propósito

Permitir ao proprietário configurar, habilitar, desabilitar e remover conexões, compreender suas condições e evitar que disponibilidade técnica seja confundida com autorização operacional.

**Condições distintas:** `instalada` (presente no ambiente), `configurada` (dados necessários informados), `habilitada` (liberada para disponibilização), `autorizada` (permissões compatíveis com a operação) e `disponível` (operante no momento). Um serviço pode estar configurado e habilitado, mas com credencial expirada ou somente leitura.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-058** | MUST | O usuário deve conseguir visualizar as integrações disponíveis para configuração e utilização. |
| **FR-059** | MUST | O JARVIS deve permitir a configuração das integrações essenciais ao MVP, incluindo os dados de conexão necessários. |
| **FR-060** | MUST | O usuário deve conseguir habilitar e desabilitar integrações configuradas. |
| **FR-061** | MUST | O JARVIS deve apresentar informações compreensíveis sobre o estado de conexão, disponibilidade e permissões relevantes de cada integração. |
| **FR-062** | MUST | O usuário deve conseguir remover uma conexão e revogar seu uso pelo JARVIS, sem que isso implique excluir dados armazenados no serviço externo. |
| **FR-063** | MUST | O JARVIS deve identificar conexões inválidas, expiradas ou indisponíveis e impedir operações que dependam de autorização não verificável. |
| **FR-064** | MUST | Configurações de integração devem persistir entre reinicializações, respeitando os requisitos de proteção de credenciais e informações sensíveis. |
| **FR-065** | MUST | Quando houver mais de uma conexão adequada para uma operação, o JARVIS deve determinar o destino a partir do contexto ou solicitar esclarecimento se houver ambiguidade relevante. |

### Regras, exceções e comportamento observado

- A **permissão do provedor externo** e a **autoridade do JARVIS** devem ser ambas compatíveis. Habilitar e-mail não autoriza envio, exclusão ou alteração de conta sem autoridade correspondente.
- **Desabilitar** impede novas operações por aquela integração e bloqueia a continuidade de tasks dependentes, ainda que as credenciais externas sigam válidas.
- **Remover conexão** impede seu uso pelo JARVIS; **não** implica exclusão de dados no serviço externo, nem autoriza dizer que o token foi revogado no provedor se isso não ocorreu.
- **Reconectar** quando expirar ou falhar requer respeitar os mecanismos normais de autenticação; não contorná-los.
- Multi-contas do mesmo proprietário são permitidas; destino ambíguo de ação externa exige esclarecimento antes de agir.
- Google Calendar, e-mail e GitHub aparecem apenas como **exemplos**, não como as duas integrações escolhidas para o MVP.
- Protocolos (MCP etc.), OAuth2/API key, manifestos, secret store e refresh automático são decisões de Specs/Contracts/Architecture e/ou variáveis por serviço.

### Critérios de aceitação do bloco

1. Configurar e habilitar integrações reais do MVP.
2. Identificar integração configurada mas indisponível.
3. Não confundir acesso de leitura com permissão de escrita.
4. Desabilitação impede novas operações daquela conexão.
5. Remoção impede uso e não exclui dados externos indevidamente.
6. Credencial expirada não é tratada como válida.
7. Configurações sobrevivem ao reinício sem expor segredos.
8. Destino ambíguo exige esclarecimento antes de efeito externo.

---

## PRD-09 — Contextos, Identidade e Organização das Informações — APPROVED

### Propósito

Permitir que o mesmo proprietário utilize o assistente em contextos pessoais, profissionais e técnicos **sem obrigatoriedade de modos separados**, preservando escopos e origens de informações, contas e decisões.

### Requisitos funcionais

| ID | Prioridade | Requisito aprovado |
|---|---|---|
| **FR-066** | MUST | O MVP deve atender um usuário proprietário por instalação, permitindo a configuração de múltiplas conexões externas desse proprietário. |
| **FR-067** | MUST | O JARVIS deve identificar o contexto relevante de uma solicitação utilizando a conversa, as informações disponíveis e referências explícitas do usuário. |
| **FR-068** | MUST | O JARVIS deve distinguir informações de diferentes projetos, assuntos e contextos, respeitando seus escopos e referências de origem. |
| **FR-069** | MUST | O JARVIS não deve exigir a seleção obrigatória de modos pessoais, profissionais ou técnicos para utilizar suas capacidades gerais. |
| **FR-070** | MUST | Quando não conseguir identificar com segurança o contexto necessário, o JARVIS deve solicitar esclarecimento antes de executar operações que dependam dessa identificação. |
| **FR-071** | MUST | O usuário deve conseguir esclarecer ou corrigir a identificação de um contexto feita pelo JARVIS. |
| **FR-072** | MUST | O JARVIS deve associar operações e resultados às conexões externas efetivamente utilizadas, permitindo distinguir contas diferentes de um mesmo serviço. |
| **FR-073** | MUST | As informações de contexto recuperadas não devem ampliar permissões, substituir autorizações ou modificar os limites operacionais do JARVIS. |

### Regras, exceções e comportamento observado

- Preferências **gerais** podem ser relevantes em diversos contextos; decisões **de projeto** permanecem ligadas ao projeto apropriado. Contextualização não significa isolamento absoluto de toda informação.
- Informação originada de uma conta externa preserva identificação da conexão/fonte. Histórico de task preserva vínculo com a execução. Autorizações ficam limitadas ao escopo concedido.
- O JARVIS deve permitir correção de inferência contextual equivocada. Em ações externas, ambiguidade de destinatário/conta/projeto exige esclarecimento quando não houver referência inequívoca e autoridade compatível.
- A mesma pessoa pode usar o assistente para software, trabalho e vida pessoal, sem criar apps ou perfis separados obrigatórios.
- Vocabulário funcional preliminar: `Owner`, `Conversation`, `Context`, `ExternalConnection`, `Capability`, `Task`, `Authorization`, `MemoryReference`. Não implica entidades de banco, campos ou API aprovados.
- Multiusuário e compartilhamento entre proprietários permanecem **FUTURE**, não parte do MVP.

### Critérios de aceitação do bloco

1. Utilizar contextos pessoais/profissionais/técnicos sem seleção compulsória de modo.
2. Não atribuir decisão específica de um projeto a outro.
3. Utilizar preferência geral quando relevante.
4. Permitir correção de contexto inferido.
5. Solicitar esclarecimento quando alvo/conta da ação estiver ambíguo.
6. Distinguir duas contas conectadas do mesmo serviço.
7. Preservar origem de informações e operações.
8. Não elevar permissões com base em memórias ou inferências.

---
## PRD-10 — Escopo Verificável do MVP e Critérios de Aceitação — APPROVED

### Propósito

O MVP não será considerado concluído porque a UI abriu ou o assistente respondeu a uma pergunta. Deve demonstrar, de ponta a ponta, **continuidade**, **extensibilidade** e **execução real sob supervisão**, mantendo segurança e persistência.

### Capacidades obrigatórias do MVP

| Área | Resultado requerido |
|---|---|
| Conversação | Texto e voz compartilham o mesmo contexto e histórico. |
| Memória cognitiva | Registrar, recuperar, atualizar e esquecer informações relevantes usando Sofias Memory. |
| Conhecimento | Consultar conhecimento persistido e preservar referências quando disponíveis. |
| Seleção de ferramentas | Descobrir e selecionar capacidades presentes e pertinentes. |
| Integrações | Operar efetivamente em **pelo menos dois domínios externos distintos**. |
| Autorizações | Respeitar permissões e confirmações para efeitos externos. |
| Tarefas | Permitir estados, progresso, interrupção quando cabível, resultados e recuperação segura. |
| Interface | Conversas, tarefas, confirmações e integrações utilizáveis/consultáveis. |
| Segurança | Bloquear operações não autorizadas e evitar duplicação insegura. |
| Persistência operacional | Conversas, tarefas e configurações essenciais sobrevivem à reinicialização. |

A implementação poderá ocorrer por **incrementos menores, funcionais e verificáveis**. Isso não reduz os critérios obrigatórios de aprovação do MVP completo.

### Jornada de validação A — Continuidade e memória

1. Usuário inicia conversa por **texto**, continua por **voz** na mesma sessão e registra uma informação relevante.
2. Encerra a aplicação e retorna posteriormente.
3. Reabre a conversa ou retoma o assunto e utiliza a memória recuperada.
4. **Aceite:** histórico recuperável, continuidade entre modalidades, memória persistente relevante e distinção entre mensagem da conversa e conhecimento/memória. Falta de informação deve ser explicitada, não inventada.

**Cobertura principal:** FR-001–FR-016, FR-047–FR-048, NFR-003, NFR-005, NFR-009.

### Jornada de validação B — Extensibilidade real

1. Usuário apresenta pedido que exige informações de **dois serviços/domínios externos diferentes**.
2. JARVIS identifica capabilities relevantes, verifica disponibilidade/autorização, consulta serviços reais e consolida informações.
3. **Aceite:** informações realmente obtidas, fontes/limitações comunicadas, seleções por contexto e ausência de regras particulares desses domínios no Core.

**Cobertura principal:** FR-017–FR-024, FR-058–FR-065, FR-067–FR-073, NFR-005, NFR-010.

### Jornada de validação C — Execução real supervisionada

1. Usuário apresenta objetivo de múltiplas etapas que inclui **uma alteração efetiva em serviço externo**.
2. JARVIS planeja apenas quando necessário, inicia atividade acompanhável e prepara operação.
3. Antes da ação protegida, verifica a autoridade e solicita confirmação quando exigida.
4. Executa somente o autorizado, apresenta resultado verificável e mantém a task consultável.
5. **Aceite:** acompanhamento real; autorizações compreensíveis; rejeição impede operação; sucesso/falha/incerteza distinguidos; sem reenvio ou alteração duplicados quando o resultado anterior for desconhecido.

**Cobertura principal:** FR-026–FR-057, NFR-001–NFR-004, NFR-006–NFR-008.

### Comportamentos excepcionais obrigatórios para validação

| Situação de teste | Comportamento esperado | Referências principais |
|---|---|---|
| Sofias Memory indisponível | Funções independentes continuam; limitação informada. | FR-015; NFR-005 |
| Serviço externo desconectado | Falha/indisponibilidade informada; nenhum dado fictício apresentado como atual. | FR-022, FR-063 |
| Confirmação rejeitada | Ação bloqueada; resultado não tratado como execução. | FR-029, FR-032 |
| Conteúdo/alvo materialmente alterado após aprovação | Reavaliar a autorização antes da ação. | FR-028, FR-030 |
| Usuário interrompe uma tarefa | Preservar estado/resultados disponíveis; não prometer reversão automática. | FR-041, FR-044 |
| Aplicação reiniciada durante task | Recuperar estado e avaliar segurança de continuidade. | FR-042, FR-043; NFR-003–004 |
| Resposta perdida após possível alteração externa | Tratar como resultado desconhecido e não duplicar automaticamente. | FR-034–035; NFR-004 |
| Integração desabilitada | Impedir novas operações por ela; tratar tasks dependentes. | FR-060, FR-063 |
| Microfone indisponível | Texto continua utilizável. | FR-006; NFR-009 |
| Projeto/conta/destinatário ambíguo | Pedir esclarecimento antes da ação dependente dessa informação. | FR-065, FR-070 |
| Verificação de autorização indisponível | Bloquear operação protegida. | FR-026, FR-032; NFR-001 |

### Critérios formais de saída do MVP

| ID | Obrigatório | Critério aprovado |
|---|---|---|
| **AC-001** | Sim | Os três cenários principais funcionam de ponta a ponta. |
| **AC-002** | Sim | Os requisitos funcionais classificados como MUST no MVP estão atendidos. |
| **AC-003** | Sim | Os dez NFRs aprovados possuem evidências de atendimento. |
| **AC-004** | Sim | Os comportamentos excepcionais críticos foram verificados. |
| **AC-005** | Sim | Não existem defeitos conhecidos que permitam executar operações sem autorização compatível. |
| **AC-006** | Sim | As integrações utilizadas na validação realizam operações reais, não apenas simulações. |
| **AC-007** | Sim | As limitações conhecidas estão documentadas e não contradizem os requisitos obrigatórios. |
| **AC-008** | Sim | O proprietário aprova explicitamente o resultado da validação. |

**Notas de validação:** testes podem ocorrer em contas e ambientes controlados, evitando danos a sistemas reais de produção; contudo, as integrações precisam **executar operações reais**, não apenas respostas simuladas. A aprovação das três jornadas **não** substitui os testes dos demais MUST e NFR. Uma falha crítica de autorização, segurança ou integridade operacional **impede** a aprovação, mesmo com demonstrações aparentemente bem-sucedidas. Percentuais arbitrários de cobertura e metas inventadas de tempo de resposta não são requisitos aprovados nesta fase.

### Funcionalidades que NÃO bloqueiam o MVP

Marketplace; criação dinâmica completa de skills/agents; código executável gerado automaticamente; colaboração multiagente complexa; autonomia progressiva com permissões persistentes; proatividade contínua e agendamento recorrente avançado; Knowledge Galaxy 3D; ambient context; desktop automation avançada; multiusuário; Developer Assistant como especialização obrigatória; novos canais como WhatsApp/Telegram. A visão é preservada, mas nenhum desses itens adquire prioridade de MVP por estar mencionado aqui.

---

## PRD-11 — Riscos, Dependências e Questões em Aberto — APPROVED

### Propósito e critério de aprovação

Registrar incertezas com honestidade: **BLOCKER** impede a aprovação do PRD por ambiguidade funcional crítica; **DEFERRED** precisa ser resolvido antes da implementação/validação afetada, mas não impede fechar este documento; **RISK** deve ser acompanhado e mitigado.

**Conclusão aprovada:** não foi identificado BLOCKER funcional que exija reabrir PRD-01–PRD-10. Isso **não** resolve escolhas técnicas abertas nem autoriza implementação sem Specs, Contracts, Architecture e aprovações correspondentes.

### Riscos aprovados

| ID | Risco | Mitigação/direção aprovada |
|---|---|---|
| **RISK-01** | A integração com Sofias Memory pode não contemplar todos os contratos necessários de conhecimento e memória. | Auditar os contratos existentes antes da implementação. |
| **RISK-02** | A combinação de seleção dinâmica de ferramentas e execução externa pode introduzir caminhos de autorização inseguros. | Exigir verificações centralizadas e testes de execução não autorizada. |
| **RISK-03** | Tarefas interrompidas podem provocar repetição de operações com efeitos externos. | Exigir recuperação segura e tratamento explícito de resultados desconhecidos. |
| **RISK-04** | O número de funcionalidades obrigatórias pode aumentar a complexidade da primeira entrega. | Implementar incrementos funcionais, preservando todos os critérios obrigatórios de aceite. |
| **RISK-05** | Integrações de terceiros podem apresentar restrições, indisponibilidade ou mudanças de API. | Separar falhas de integração das demais funções do assistente. |
| **RISK-06** | A persistência automática de memórias pode registrar informações desnecessárias ou sensíveis. | Definir política específica de memória antes de habilitar persistência automática. |
| **RISK-07** | O desempenho e a qualidade da experiência por voz podem variar conforme os modelos e o ambiente escolhido. | Validar em ambiente real antes de estabelecer metas quantitativas. |

### Dependências funcionais do MVP

| Dependência | Decisão e ressalva |
|---|---|
| **Sofias Memory** | Serviço de memória cognitiva e conhecimento **definido**. Compatibilidade dos contratos necessários ainda a verificar. Não executa tools, agents ou tarefas. |
| **Inferência por IA** | Necessária; providers, modelos e forma de hospedagem **OPEN**. |
| **Integrações externas** | Pelo menos dois domínios reais no MVP; nomes e operação de escrita específica **não escolhidos**. |
| **Persistência operacional** | Necessária para conversas, tasks, decisões e configurações; tecnologia **OPEN**, sob responsabilidade do JARVIS. |
| **Autorizações, confirmações e auditoria** | Comportamento obrigatório; formatos e contratos técnicos **OPEN**. |
| **Recursos de voz** | Obrigatórios; STT/TTS, modos e provedores **OPEN**. |

### Questões adiadas, com dono da próxima decisão

| ID | Pergunta aprovada como DEFERRED | Etapa indicada |
|---|---|---|
| **OQ-01** | Quais serão as duas integrações reais utilizadas na validação inicial? | Specs / planejamento do MVP |
| **OQ-02** | Quais sistemas operacionais serão suportados inicialmente? | Specs / Architecture |
| **OQ-03** | Qual tecnologia será utilizada para a interface? | Architecture |
| **OQ-04** | Quais modelos e tecnologias atenderão voz e inferência? | Specs / Architecture |
| **OQ-05** | Qual será a política detalhada de persistência automática de memórias? | Specs |
| **OQ-06** | Como serão representados os contratos técnicos de ferramentas, autorizações e tarefas? | Contracts |
| **OQ-07** | Quais metas quantitativas de desempenho serão exigidas no ambiente escolhido? | Specs / validação técnica |
| **OQ-08** | Quais componentes existentes do Sofia's Assistant poderão ser reutilizados? | Architecture / auditoria técnica |

**Regra para DEFERRED:** cada questão deve ser resolvida **antes** da implementação ou validação dela dependente. Ex.: duas integrações ainda não precisam estar nomeadas neste PRD, mas não é possível aprovar o cenário de extensibilidade sem testá-las de verdade.

### Revisão de consistência aprovada no PRD-11

1. **MVP versus futuro:** FR-017–FR-024 exigem descoberta/seleção de capacidades já disponíveis. FR-025 (`SHOULD`) trata de pesquisa e proposta de novas integrações para evolução posterior. Não há aprovação de instalação silenciosa.
2. **Memória versus estado operacional:** Sofias Memory persiste/recupera informação cognitiva e documental; JARVIS governa conversas, task runtime, autorizações, auditoria e recuperação. Nenhuma memória concede acesso.
3. **Autonomia versus autoridade:** JARVIS pode planejar e preparar; cada efeito externo depende de autoridade compatível. Decisão semântica de usar uma ferramenta não é grant.
4. **Continuidade versus repetição:** preservar estado não significa retomar automaticamente operações externas cujo resultado ainda é desconhecido.

**Condição de fechamento:** todos os requisitos aprovados serão preservados, questões adiadas não serão tratadas como resolvidas, riscos serão acompanhados e qualquer mudança relevante após a aprovação será alteração explícita de baseline — não edição silenciosa.

---

## 12. Escopo e fronteiras normativas transversais

### 12.1 IN SCOPE — baseline obrigatório do MVP

- Conversação unificada por texto/voz e histórico persistente.
- Integração com Cognitive Memory e Knowledge Memory do Sofias Memory, com proveniência quando disponível e operações explícitas de lembrar/atualizar/esquecer.
- Descoberta/seleção contextual de tools existentes, com pelo menos dois domínios externos reais.
- Configuração de integrações pelo proprietário; múltiplas contas externas do mesmo proprietário.
- Execução de uma ação externa real de escrita/alteração, com autoridade apropriada, confirmações quando aplicáveis e resultado verificável.
- Tarefas de múltiplas etapas com estados, controle, persistência e recuperação segura.
- Interface principal de conversa, acompanhamento de tarefas, autorizações, eventos e status de integrações.
- Requisitos de segurança, privacidade, integridade, auditabilidade, responsividade, acessibilidade, controle de custos e extensibilidade.

### 12.2 FUTURE / DEFERRED — preservar sem exigir no MVP

| Capacidade | Limite da decisão |
|---|---|
| **Agent Builder** | Sugerir, configurar/criar e habilitar agentes especializados, com aprovações separadas. |
| **Skill Evolution** | Pesquisar necessidades e propor novas skills/refinamentos. |
| **Plugin Discovery** | Pesquisar novos plugins, preparar instalação, sem instalar/ativar silenciosamente. |
| **Autonomia progressiva** | Grants persistentes estritos e revogáveis (opção C adiada). |
| **Proatividade avançada** | Monitoramento contínuo, agendamentos recorrentes complexos e atividades baseadas em eventos. |
| **Multi-Agent Collaboration** | Delegação e coordenação entre vários agents. |
| **Desktop Automation** | Controle avançado de aplicações, janelas e SO. |
| **Ambient Context** | Contexto de tela/aplicações/ambiente sob controles de privacidade. |
| **Knowledge Galaxy** | Exploração 3D interativa de conhecimento e fontes. |
| **Developer Assistant** | Capacidade especializada em software, sem mudar a identidade universal do Core. |
| **Multi-Channel** | WhatsApp, Telegram e APIs como canais adicionais. |
| **Multi-User** | Identidades/autorizações independentes de vários usuários. |
| **Geração de código de capacidades** | Exige revisão/autorização/isolamento distintos da criação de descrição declarativa. |

Essa relação é **visão**, não cronograma, ordem de entrega ou autorização para construir recursos além do escopo aprovado. Proatividade **supervisionada** faz parte da visão; autonomia progressiva com autoridade persistente segue adiada. Não criar agentes quando uma tool resolve o pedido.

### 12.3 OUT OF SCOPE — limites permanentes de responsabilidade do Core

- Regras nativas de OS, estoque, cotação, CRM, e-commerce ou domínio particular de cliente; esses comportamentos pertencem às aplicações e integrações externas.
- Transformar Sofias Memory em executor operacional (scripts, tools, agents, tarefas), ainda que ele persista definições declarativas.
- Substituir sistemas externos como objetivo geral do produto.
- Executar componentes externos sem autorização, permitir grants baseados apenas em memória, ou permitir bypass por agentes/skills/plugins.
- Modificar silenciosamente seu próprio Core em produção ou conceder autonomamente permissões mais amplas.

**Exemplo histórico, sem requisito nativo:** o fluxo de ordens de serviço de uma assistência técnica foi usado no Discovery para ilustrar integração externa. Suas regras de diagnóstico, cotação, aprovação e compra de peças **não são requisitos do JARVIS Core**. Nem assistência técnica, nem Gmail, Google Calendar, GitHub ou WhatsApp foram escolhidos como integrações obrigatórias do MVP.

### 12.4 Decisões tecnológicas não tomadas

**OPEN/DEFERRED conforme baseline:** linguagem e runtime do Core; PySide6/Web/híbrido; sistema(s) operacional(is); local/cloud/híbrido; providers de IA e voz; MCP ou outro protocolo para tools; mecanismo de secrets, banco e persistência operacional; sandbox/isolamento; schemas, endpoints e especificação de grants/confirmations/audit; limiares quantitativos de desempenho; distribuição, atualizações e licença definitiva do JARVIS.

O JARVIS é **novo produto independente** do Sofia's Assistant. Poderá reutilizar componentes próprios **somente após avaliação funcional e de adequação**, sem transformar a aplicação original em dependência operacional. Eventuais licenças de componentes de terceiros serão revisadas quando houver reutilização concreta; a licença do código próprio do usuário não foi classificada como impeditivo no Discovery.

---

## 13. Matriz de rastreabilidade dos blocos aprovados

| Bloco | Tema aprovado | Identificadores normativos | Aceite específico |
|---|---|---|---|
| **PRD-01** | Conversação unificada e continuidade | FR-001–FR-007 | Cinco verificações listadas no próprio bloco |
| **PRD-02** | Memória cognitiva e conhecimento | FR-008–FR-016 | Sete verificações |
| **PRD-03** | Descoberta e seleção de capacidades | FR-017–FR-025 (**FR-025 SHOULD / pós-MVP**) | Seis verificações |
| **PRD-04** | Execução, autoridade e confirmações | FR-026–FR-035 | Nove verificações |
| **PRD-05** | Tarefas, planejamento e continuidade operacional | FR-036–FR-046 | Nove verificações |
| **PRD-06** | Interface e visibilidade operacional | FR-047–FR-057 | Oito verificações |
| **PRD-07** | Segurança, privacidade e demais NFRs | NFR-001–NFR-010 | Dez verificações |
| **PRD-08** | Configuração e gerenciamento de integrações | FR-058–FR-065 | Oito verificações |
| **PRD-09** | Identidade e contextualização | FR-066–FR-073 | Oito verificações |
| **PRD-10** | Aceitação integral do MVP | AC-001–AC-008 | Jornadas A/B/C e exceções críticas |
| **PRD-11** | Riscos, dependências e pendências | RISK-01–RISK-07; OQ-01–OQ-08 | Sem BLOCKER funcional identificado |

### 13.1 Invariantes a verificar em toda especificação subsequente

1. **Produto independente:** JARVIS não é renomeação/refatoração do Sofia's Assistant.
2. **Serviço de memória não executa:** Sofias Memory persiste/recupera; JARVIS decide/aplica autoridade/executa.
3. **Contexto não é grant:** documento, mensagem, resposta de tool ou memória nunca concedem privilégio.
4. **Seleção não é autorização:** uma tool relevante pode ainda estar não habilitada, sem acesso ou proibida para aquela ação.
5. **Agente não é autoridade:** agents/skills/plugins não contornam política nem a trilha de auditoria.
6. **Operação real não é simulação:** afirmar execução exige evidência compatível com o resultado.
7. **Incerto não é sucesso nem falha presumida:** resultado desconhecido deve impedir duplicação insegura.
8. **Task state não é Cognitive Memory:** tarefas e controles operacionais continuam no JARVIS.
9. **Um proprietário, múltiplas conexões:** multiusuário não é obrigatório para o MVP.
10. **Comportamento proporcional:** pedido simples não exige planejamento ou agente desnecessário.
11. **Futuro não entra no MVP por acidente:** FR-025 é SHOULD pós-MVP e demais recursos avançados seguem DEFERRED.
12. **Compromisso verificável:** a aprovação do MVP depende de AC-001–AC-008 e evidência de todos os MUST/NFR pertinentes.

---

## 14. Project State e próximo passo legítimo

| Campo | Estado consolidado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | PRD concluído e aprovado; próximo estágio: Specs |
| **Current role** | Product Engineer / Technical Product Manager |
| **Approved** | Discovery; Product Definition PD-01–PD-09; PRD-01–PRD-11; 73 FR (72 MUST, 1 SHOULD pós-MVP); 10 NFR; 8 AC gerais; 7 riscos; 8 questões adiadas |
| **Current artifact** | `docs/product-manager/03-JARVIS-PRD.md` |
| **Current Slice** | Nenhum slice de implementação aprovado |
| **Next legitimate step** | Iniciar Specs em pontos revisáveis, resolver questões necessárias na etapa apropriada e submetê-las à aprovação humana antes de Contracts, Architecture e implementação |

**Controle de alterações:** o presente PRD representa o baseline funcional explicitamente aprovado. Ajustes de escopo, prioridade, comportamento, autoridade e critérios de aceitação após esta consolidação requerem revisão e aprovação humanas explícitas, preservando histórico no Git. Nenhuma decisão `OPEN` ou `DEFERRED` foi silenciosamente preenchida neste documento.

---

*Fim do JARVIS — Product Requirements Document (PRD).*

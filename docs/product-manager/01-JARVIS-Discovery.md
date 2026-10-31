# JARVIS — Discovery

**Status:** APPROVED  
**Data de consolidação:** 2026-10-27  
**Fase:** Discovery concluído  
**Papel:** Product Engineer  
**Natureza:** baseline de descoberta de produto — não é PRD, especificação técnica nem autorização de implementação

> **Regra de leitura:** o que consta em **Decisões aprovadas** constitui o baseline deste Discovery. Itens identificados como **OPEN**, **HYPOTHESIS** ou **DEFERRED** não estão aprovados como requisitos, contratos ou compromissos de implementação.

## 1. Contexto e origem

O JARVIS nasceu do interesse em desenvolver um assistente pessoal com características de interação natural, memória persistente, uso de ferramentas e execução supervisionada. O documento *Build Your Own JARVIS — The Free Prompt Pack*, de Zubair Trabzada, serviu de inspiração para experiências como conversa por voz, recuperação de conhecimento, visualização 3D e captura de notas. Seu protótipo de seis prompts é uma referência, **não** uma especificação a ser reproduzida literalmente.

A *Auditoria técnica comparativa dos projetos Jarvis, Sofia e Jev* trouxe referências sobre experiência de assistente pessoal, context management, tool routing, MCP, agentes, revisão de decisões, autorização, scheduler, recovery e memória. As recomendações originalmente dirigidas ao Sofia's Assistant **não** foram adotadas automaticamente como roadmap do JARVIS.

O usuário já mantém dois projetos próprios relevantes:

- **Sofia's Assistant:** projeto existente que poderá fornecer componentes comprovadamente funcionais e validados.
- **Sofias Memory:** projeto especializado em persistir e recuperar informações, a ser utilizado pelo JARVIS como serviço de memória e conhecimento; poderá ser evoluído conforme necessidades legitimamente identificadas.

**JARVIS é um produto novo e independente.** Não será implementado dentro do Sofia's Assistant, nem este será renomeado ou convertido no JARVIS. A eventual reutilização é seletiva e requer avaliação técnica de cada componente.

## 2. Problema e oportunidade

O objetivo não é construir um chatbot com uma lista fixa de comandos, nem uma aplicação de domínio único. Busca-se um assistente pessoal capaz de compreender pedidos, preservar contexto, identificar capacidades disponíveis e realizar atividades úteis por meio de ferramentas externas, com continuidade e limites de autoridade.

Problemas gerais identificados:

- As tarefas do cotidiano se distribuem por aplicações e fontes de dados diferentes.
- O usuário frequentemente precisa consultar informações, interpretar o estado de uma atividade e coordenar passos manuais.
- Um assistente que apenas responde perguntas não conclui objetivos operacionais.
- Extensões diretamente codificadas no núcleo do produto limitariam sua evolução.
- Agir em nome do usuário sem controle explícito de autoridade introduziria riscos inaceitáveis.

**Oportunidade de produto:** oferecer um núcleo de assistência universal capaz de orquestrar ferramentas e extensões de domínios diferentes sem conhecer suas regras de negócio nativamente.

## 3. Visão aprovada

> **JARVIS é um assistente pessoal universal, multimodal e extensível, que interpreta solicitações e objetivos, utiliza contexto e memória, descobre e seleciona capacidades adequadas, planeja quando necessário e executa ações permitidas sob autoridade e supervisão do usuário.** Deve manter continuidade entre interações e poder evoluir suas capacidades com o uso, de forma supervisionada.

O foco inicial aprovado é **assistente pessoal universal**, para atividades pessoais e profissionais. Especializações são possíveis, mas não definem a identidade do produto.

### 3.1 Diretrizes de valor

- **Útil:** fornecer resultados observáveis, não apenas demonstrações de arquitetura.
- **Universal:** não depender de uma aplicação ou segmento de negócio específico.
- **Extensível:** permitir novas integrações sem alterar regras específicas de domínio no JARVIS Core.
- **Contínuo:** aproveitar contexto e memória para evitar recomeçar a cada conversa.
- **Controlável:** distinguir proposta, preparo, criação, ativação e execução; respeitar permissões.
- **Verificável:** informar o que realmente consultou, executou, concluiu ou não conseguiu realizar.

Essas diretrizes descrevem comportamento de produto; não definem componentes técnicos obrigatórios nem o escopo de MVP.

## 4. Usuários e atores identificados

- **Usuário principal:** pessoa que conversa com o JARVIS, concede ou revoga autorizações e aprova extensões, agentes e ações quando necessário. O próprio criador do projeto é o primeiro usuário de referência.
- **JARVIS:** assistente responsável por interação, seleção/orquestração de capacidades e execução operacional controlada.
- **Extensões e serviços externos:** tools, plugins, serviços, aplicações ou canais que oferecem funcionalidades específicas.
- **Sofias Memory:** autoridade sobre persistência e recuperação de informações, incluindo definições declarativas de skills e agentes, sem executar operações.

**OPEN:** público-alvo além do usuário inicial, eventual distribuição e políticas de múltiplos usuários.

## 5. Modelo conceitual de capacidades — aprovado

Os conceitos abaixo estão aprovados como **distinções de produto**, não como exigência de criar seis frameworks ou serviços separados.

| Conceito | Significado acordado |
|---|---|
| **Capability** | Declara uma habilidade disponibilizada ao assistente. |
| **Tool** | Realiza uma operação concreta, de consulta ou alteração. |
| **Plugin** | Disponibiliza um conjunto organizado de capacidades relacionadas. |
| **Skill** | Descreve conhecimento procedural ou um modo de conduzir uma atividade, possivelmente combinando tools. |
| **Agent** | Conduz um objetivo que pode requerer planejamento, coordenação, etapas e acompanhamento. |
| **Channel** | Meio de receber solicitações e entregar respostas, como texto ou voz e, potencialmente, integrações de mensagens. |

**Invariantes aprovados:** skill não concede permissão; agente não é autoridade de execução; uma ferramenta descoberta não está automaticamente instalada, habilitada ou autorizada.

### 5.1 Formas de atendimento

1. **Consulta simples:** identificar e utilizar uma ferramenta de leitura adequada; não exige agente ou planejamento complexo por princípio.
2. **Objetivo de múltiplas etapas:** organizar ações, combinar ferramentas e, quando útil, empregar um agente.
3. **Ação com efeito externo:** preparar, revisar e submeter a execução às autorizações pertinentes.

A proporcionalidade é parte da experiência: nem todo comando precisa se tornar uma execução agêntica longa.

## 6. Fronteira aprovada: JARVIS × Sofias Memory

Esta divisão é **normativa para o Discovery**:

| Responsabilidade | JARVIS | Sofias Memory |
|---|---|---|
| Interpretar pedidos e coordenar capacidades | **Sim** | Não |
| Executar tools, agentes, scripts ou operações externas | **Exclusivo** | **Não** |
| Aplicar authority, policy, grants e confirmations | **Sim** | Não |
| Manter runtime, scheduler operacional, audit e recovery | **Sim** | Não |
| Manter implementação executável/referência controlada | **Sim** | Não |
| Persistir e recuperar conhecimento e memórias | Consome e fornece informações | **Responsável** |
| Persistir e recuperar definições/configurações declarativas de Skills e Agents | Consome e propõe informações | **Responsável** |
| Preservar provenance e histórico informacional | Consome quando pertinente | **Responsável** |

O **Sofias Memory não executará nenhuma operação operacional**. Mesmo que sua implementação seja ampliada para armazenar descrições, configurações e versões de skills/agentes, sua função permanece **persistir e devolver informações**.

A **configuração declarativa de um agente** pode ser preservada no Sofias Memory. A **implementação executável**, ou sua referência controlada, pertence ao domínio do JARVIS. Não se aprovou nesta fase nenhum nome de campo de banco, schema, formato de pacote ou contrato público.

**Separação obrigatória:** conteúdo recordado ou recuperado constitui contexto/evidência, nunca autorização de execução. O resultado de uma tool tampouco se converte automaticamente em verdade permanente sem critérios de memória apropriados.

**Possibilidade aprovada:** alterar/evoluir o Sofias Memory se necessário para oferecer persistência e recuperação úteis ao JARVIS, **sem transferir execução para ele**. A necessidade concreta de mudança deverá ser demonstrada por análise do estado real do projeto.

## 7. Descoberta, uso e evolução supervisionada de capacidades

### 7.1 Descoberta e seleção — aprovado

- JARVIS interpreta a intenção do pedido.
- Identifica capacidades instaladas/conectadas/habilitadas e pertinentes ao contexto.
- Seleciona ferramentas aplicáveis e visíveis à autoridade do usuário.
- Verifica requisitos e permissões antes de executar.
- Trata indisponibilidade, incerteza e falhas sem afirmar sucesso inexistente.

O JARVIS deve poder usar ferramentas de domínios distintos mediante o mesmo comportamento geral, sem lógica de cada negócio embutida no Core.

### 7.2 Capacidade ausente — aprovado (combinação das opções A e C)

Quando uma capacidade necessária não estiver disponível, o JARVIS poderá:

1. Reconhecer e explicar a lacuna.
2. Localizar alternativas de tools, plugins, skills, agentes ou integrações.
3. Investigar requisitos e preparar uma proposta/configuração para avaliação, sem efeitos externos não autorizados.
4. Solicitar autorização antes de instalar, conectar contas, ativar, ampliar permissões ou executar alterações significativas.
5. Validar o funcionamento da capacidade dentro dos limites concedidos.

**Não aprovado:** instalação silenciosa, concessão autônoma de credenciais ou execução irrestrita de componentes externos.

### 7.3 Capability Evolution — aprovado

O JARVIS poderá identificar oportunidades de melhoria ou lacunas de capacidade à medida que é utilizado e **sugerir proativamente** novas tools, skills, integrações e agentes. Poderá preparar propostas e rascunhos sem efeitos externos, mantendo o usuário como autoridade para criação, ativação e mudanças relevantes.

**Modelo aprovado: proatividade supervisionada (opção B).**

**DEFERRED:** autonomia progressiva (opção C), com permissões persistentes e restritas para determinados tipos de configuração/criação automática; não faz parte do baseline inicial.

### 7.4 Criação de agentes — aprovado conceitualmente

O JARVIS poderá:

1. Identificar ou receber a necessidade de um agente.
2. Preparar uma definição declarativa com objetivo, capacidades, limites e comportamento esperado.
3. Submeter a criação à aprovação do usuário.
4. Criar e validar a configuração autorizada.
5. Quando houver necessidade de código executável, tratar sua criação como operação distinta, com revisão, aprovação e isolamento adicionais.
6. Solicitar aprovação para ativação, permissões e eventuais gatilhos de execução.
7. Executar dentro do runtime e dos limites operacionais do JARVIS, preservando informações e resultados pertinentes no Sofias Memory.

**Criar a definição ≠ criar código executável ≠ habilitar ≠ conceder autonomia para operar.** Essas decisões não podem ser condensadas em uma autorização irrestrita.

## 8. Regras de comportamento aprovadas

| Regra | Resultado esperado |
|---|---|
| Extensibilidade | Acrescentar integração não exige inserir regras específicas de cada domínio no Core. |
| Descoberta controlada | Capacidades utilizáveis são descobertas no contexto de sua disponibilidade e permissão. |
| Autoridade centralizada | Nenhuma tool, plugin, skill ou agente contorna o mecanismo de autorização/execução do JARVIS. |
| Seleção contextual | Expor/utilizar capacidades relevantes e permitidas, sem pressupor o catálogo inteiro. |
| Execução proporcional | Solicitações simples continuam simples; planejamento/agentes quando necessários. |
| Memória separada | Lembrança, documento e instrução externa não concedem grants. |
| Resultados verificáveis | Sucesso, falha, ausência de dados e incerteza são comunicados corretamente. |
| Degradação controlada | Falha de integração não derruba necessariamente o assistente inteiro. |
| Evolução supervisionada | Propostas espontâneas são possíveis; instalação/ativação/efeitos relevantes exigem controle humano. |

A implementação técnica precisa distinguir autorização de **adequação da decisão**: uma ação pode ser permitida e ainda assim não corresponder ao objetivo solicitado. A necessidade de revisão semântica foi identificada, mas o desenho de um subsistema específico permanece **OPEN**.

## 9. Workflow real observado — exemplo de validação, não escopo nativo

Um cenário real de assistência técnica foi usado para investigar a utilidade do assistente e, em seguida, **explicitamente retirado da definição de funcionalidades nativas**. Serve como exemplo de integração por tool/plugin, assim como poderiam servir calendário, GitHub ou e-mail.

### 9.1 Processo relatado

1. O equipamento chega à oficina e aguarda avaliação do técnico.
2. Na avaliação, o técnico identifica defeito, peças, preço e requisitos do conserto.
3. Quando é necessário cotar peça indisponível, a OS entra em **Aguardando Cotação**.
4. Após obter preço e concluir o orçamento, passa para **Aguardando Aprovação**.
5. O atendente envia o orçamento pelo WhatsApp, recebe a resposta do cliente e a registra **no sistema da loja**.
6. Se o cliente aprova e **não é necessário comprar peça** (porque já existe na oficina ou o reparo não a exige), a OS passa para **Reparo em andamento**.
7. Se a aprovação exige **aquisição de peça**, a OS passa para **Aguardando Peças**.

A sequência de recusa e as etapas posteriores de reparo/entrega não foram detalhadas. O nome exato do status inicial não foi validado como valor técnico de banco.

As cotações utilizam combinação de Mercado Livre, fornecedores especializados, distribuidores eletrônicos e contatos pelo WhatsApp. **Cotação para formar orçamento precede `Aguardando Aprovação`**; não confundir com compra após aprovação.

### 9.2 Implicação para o JARVIS

A lógica dessas ordens e desses status pertence ao sistema externo, não ao JARVIS. O assistente só precisará interpretar o pedido, localizar a capacidade da integração, utilizá-la dentro das permissões e comunicar os resultados.

**Exemplo hipotético:** consultar OS em `Aguardando Peças` usando uma tool de uma integração com o sistema da loja. Outro pedido poderá consultar calendário usando uma tool distinta, sem alterar o mecanismo geral.

Nenhuma integração específica com a oficina está aprovada como parte obrigatória do primeiro MVP.

## 10. Restrições e decisões de independência

- JARVIS é **novo produto e novo ambiente de desenvolvimento**; não desenvolver dentro do Sofia's Assistant.
- Reutilizar somente componentes do Sofia's Assistant cuja funcionalidade e adequação sejam verificadas. Reutilizar não equivale a depender operacionalmente da aplicação original.
- Sofias Memory permanece serviço especializado de persistência/recuperação, inclusive para definições declarativas de skills/agentes.
- O proprietário esclareceu que o Sofia's Assistant é projeto seu e ainda não tem licença definitiva; licenciamento do próprio código não constitui impedimento estabelecido no Discovery. Licenças de eventuais dependências/trechos de terceiros deverão ser verificadas quando relevantes à reutilização.
- Não escolher stack, interface, APIs, schemas, sandbox, protocolos ou deployment em Discovery sem necessidade de decisão de produto.

## 11. Referências de pesquisa — não normativas

- **`JARVIS-Prompt-Pack.pdf`** — inspiração para conversa por voz, conhecimento, fly-to-source, personalidade e captura de notas; o protótipo e sua sequência de prompts não definem o MVP.
- **`Texto colado(20261027-214247).txt`** — auditoria comparativa de projetos Jarvis, Sofia e Jev; fornece padrões e riscos observados no momento da análise, mas não estabelece automaticamente fatos sobre versões atuais nem roadmap aprovado.
- **Sofia's Assistant** — fonte candidata a componentes validados, dependente de auditoria de integração e reutilização.
- **Sofias Memory** — sistema de memória a integrar/evoluir, sujeito a exame de contratos e capacidades realmente existentes.

## 12. O que está DEFERRED ou fora do escopo inicial

- **DEFERRED:** JARVIS especializado em desenvolvimento de software (opção B do foco de produto).
- **DEFERRED:** modo de segundo cérebro dedicado, incluindo eventual *Knowledge Galaxy* 3D (opção C do foco de produto).
- **DEFERRED:** autonomia progressiva com concessões persistentes para criação/configuração automática de capacidades.
- **DEFERRED:** marketplace público, distribuição ampla de plugins e delegação multiagente avançada.
- **Não aprovado como requisito inicial:** integração específica com sistema de assistência técnica, fornecedor, WhatsApp, calendário, GitHub ou outra aplicação concreta.
- **Fora do modelo aprovado:** transformar Sofias Memory em executor de agentes/tools/scripts ou autorizar ações com base apenas em memória recuperada.

Itens adiados poderão ser reavaliados mediante valor real, riscos e aprovação futura.

## 13. Open Questions para Product Definition e investigação posterior

### NEEDS DECISION NOW, antes de aprovar uma Product Definition completa

1. **Primeira experiência realmente utilizável:** qual fluxo universal mínimo entrega valor suficiente para validar o produto, sem virar aplicativo de domínio único?
2. **Escopo inicial e atores:** uso pessoal inicial versus outros usuários e quais atividades serão suportadas na primeira entrega.
3. **Limites práticos de proatividade:** como e quando apresentar sugestões sem interromper ou agir de maneira inconveniente.

### CAN BE DEFERRED para Specs / Contracts / Architecture

- Protocolo(s) e mecanismos de extensões: MCP, tools nativas, plugins instaláveis e suas respectivas fronteiras.
- Interface definitiva, voz, canais adicionais e experiência visual.
- Stack, repositório, estrutura de módulos, deployment e ambiente de execução.
- Modelos e formatos de registro de Agent/Skill Definitions e referências executáveis.
- Esquema de versionamento, provenance e compatibilidade dos contratos com Sofias Memory.
- Detalhamento de grants, políticas de autorização, isolamento de código gerado e níveis de risco.
- Escolha entre reaproveitar, adaptar ou reimplementar cada componente do Sofia's Assistant.
- Critérios e técnicas de avaliação da qualidade de decisões e resultados de agentes.

## 14. Evidência e hipóteses

**FACTS fornecidos pelo usuário:** o JARVIS será independente; os dois projetos Sofia são de sua autoria; Sofias Memory deverá apenas persistir/recuperar informações; a oficina é um cenário ilustrativo; o usuário deseja evolução supervisionada, com propostas de novas capacidades e agentes.

**HYPOTHESES ainda não validadas:** a viabilidade de reaproveitar componentes específicos, a suficiência das APIs atuais do Sofias Memory para definições versionadas de agentes/skills, a disponibilidade de integrações reais e o primeiro fluxo ideal de validação universal.

**Research:** a auditoria técnica oferece indícios e referências sobre outros projetos, mas seus rankings e propostas de arquitetura não foram aprovados como requisitos e necessitarão de verificação pontual se forem usados para decisões técnicas.

## 15. Encerramento e Project State

**Resultado do Discovery:** há clareza suficiente sobre o tipo de produto, responsabilidade do Core, extensibilidade, separação de memória/execução e autonomia supervisionada para **iniciar Product Definition**. Não há aprovação de PRD, Specs, Contracts, ADRs ou Technical Backlog.

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | Discovery concluído |
| **Current role** | Product Engineer |
| **Approved** | Produto universal independente; modelo conceitual de capacidades; Sofias Memory somente como persistência/recuperação; execução exclusiva JARVIS; descoberta e evolução supervisionadas; distinção entre definição e código executável; regras de autoridade |
| **Open** | Experiência inicial, atores/escopo da primeira entrega, comportamento concreto da proatividade; detalhes de integração e contratos |
| **Deferred** | Especialização em desenvolvimento; segundo cérebro/galáxia; autonomia progressiva; marketplace; multiagente avançado |
| **Current artifact** | `JARVIS-Discovery.md` (este documento) |
| **Current Slice** | Nenhum |
| **Next legitimate step** | Elaborar `JARVIS-Product-Definition.md` em DRAFT, para revisão e aprovação separada |

---

*Este documento materializa as decisões tomadas em Discovery e preserva explicitamente lacunas. Qualquer alteração de baseline depende de nova decisão do proprietário do produto.*

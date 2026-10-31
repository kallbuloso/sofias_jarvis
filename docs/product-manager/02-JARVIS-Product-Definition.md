# JARVIS — Product Definition

**Status:** APPROVED  
**Data de aprovação:** 2026-10-27  
**Fase:** Product Definition concluída  
**Papel responsável:** Product Engineer  
**Baseline anterior:** `docs/product-manager/01-JARVIS-Discovery.md` — APPROVED  
**Caminho de destino:** `docs/product-manager/02-JARVIS-Product-Definition.md`  
**Natureza:** definição do produto; não é PRD, especificação técnica, contrato, ADR nem autorização para implementação.

> **Regra de leitura:** as seções PD-01 a PD-09 consolidam pontos discutidos e **aprovados individualmente** pelo proprietário do produto. Itens marcados **OPEN** ou **DEFERRED** não são decisões técnicas tomadas nem funcionalidades obrigatórias do MVP. Este documento não substitui o Discovery aprovado.

## PD-01 — Visão do Produto — APPROVED

> **JARVIS é um assistente pessoal universal, inteligente, persistente e extensível, capaz de compreender solicitações em linguagem natural, manter continuidade contextual, utilizar conhecimento e ferramentas externas, planejar e executar atividades autorizadas e propor a evolução de suas próprias capacidades sob supervisão do usuário.**

O JARVIS é um **produto novo e independente**. Não será desenvolvido dentro do Sofia's Assistant, nem este será convertido no JARVIS. Componentes existentes no Sofia's Assistant poderão ser avaliados e reutilizados quando estiverem comprovadamente funcionais e adequados.

O produto não é um chatbot de comandos predefinidos nem um sistema especializado em uma profissão, setor ou aplicativo. Seu propósito é auxiliar em atividades pessoais e profissionais, por meio de capacidades extensíveis. A evolução das próprias capacidades significa identificar necessidades, propor soluções e preparar configurações ou implementações sob supervisão; não significa alterar silenciosamente o Core nem executar código irrestritamente.

## PD-02 — Problema que o Produto Resolve — APPROVED

Usuários lidam com aplicações, serviços, documentos, conhecimentos e tarefas dispersos. Mesmo com ferramentas de IA, continuam responsáveis por ligar os recursos entre si, repetir contexto, selecionar aplicativos, coordenar etapas, acompanhar pendências e retomar atividades interrompidas.

> **Problema central:** o usuário dispõe de diferentes aplicações, informações e ferramentas, mas continua responsável por conectar esses recursos, preservar o contexto, coordenar atividades e acompanhar sua execução. Essa fragmentação gera trabalho repetitivo, perda de continuidade e limita a capacidade de delegar objetivos completos a um assistente digital confiável.

**Resultado desejado:** permitir ao usuário expressar **o que pretende alcançar**, enquanto o JARVIS identifica recursos adequados, organiza e executa etapas autorizadas, apresenta resultados e solicita intervenção quando necessária. O objetivo **não** é substituir todos os aplicativos existentes nem eliminar a autoridade humana.

## PD-03 — Público-alvo e Atores — APPROVED

### Público

O público-alvo é universal: usuários individuais que desejam um assistente para atividades pessoais e profissionais, **sem necessidade de saber programar ou automatizar processos**. Um mesmo usuário poderá atuar em diferentes contextos:

| Contexto de uso | Exemplos de necessidades |
|---|---|
| Pessoal | Compromissos, lembretes, pesquisa, organização e comunicação. |
| Profissional | Documentos, projetos, tarefas, e-mails, sistemas corporativos e automações. |
| Técnico/avançado | Infraestrutura, desenvolvimento, ferramentas especializadas, agentes e integrações personalizadas. |

Esses contextos **não** são produtos separados, perfis de autorização ou modos obrigatórios de interface.

**Limite do MVP:** um **único usuário proprietário por instalação**. Multiusuário, equipes, organizações e permissões compartilhadas ficam para avaliação futura; não bloqueiam a conexão de múltiplas contas do mesmo proprietário.

### Atores

| Ator | Responsabilidade no produto |
|---|---|
| **Usuário proprietário** | Define objetivos, configura integrações, concede ou revoga permissões, aprova ações e capacidades quando necessário. |
| **JARVIS** | Interpreta, contextualiza, planeja quando necessário, descobre recursos, coordena e executa operações sob autoridade controlada. |
| **Ferramentas e serviços externos** | Disponibilizam dados e operações específicos de cada domínio por meio de capacidades conectadas. |
| **Sofias Memory** | Persiste e recupera memórias, conhecimento e definições/configurações declarativas de skills e agentes; **não executa operações**. |

Agentes especializados são capacidades coordenadas pelo JARVIS, não usuários independentes com autoridade própria.

## PD-04 — Proposta de Valor — APPROVED

> **O JARVIS permite que o usuário se concentre no que deseja alcançar, enquanto o assistente utiliza memória, inteligência e capacidades extensíveis para organizar, executar e acompanhar atividades, mantendo o usuário no controle das decisões e autorizações.**

Os cinco benefícios centrais são:

1. **Continuidade:** recuperar contexto e informações relevantes sem exigir reconstrução manual constante, reconhecendo o que não sabe.
2. **Delegação:** receber objetivos e organizar as etapas necessárias em vez de exigir do usuário a descrição de cada operação.
3. **Economia de esforço:** reduzir consultas repetitivas, alternância entre aplicativos e coordenação manual de pendências.
4. **Adaptabilidade:** ampliar capacidades conforme necessidades surgirem, por meio de propostas supervisionadas de ferramentas, skills e agentes.
5. **Confiança e controle:** tornar claras as ações pretendidas, os recursos empregados, os resultados e os pontos que exigem autorização.

**Critérios qualitativos de valor** (não são ainda metas numéricas):

- **Utilidade real:** concluir uma atividade útil, não apenas descrever como fazê-la.
- **Continuidade comprovada:** retomar uma atividade anterior com informação persistida relevante.
- **Extensibilidade comprovada:** utilizar capacidades de diferentes domínios sem adicionar a lógica de cada domínio ao Core.

Proatividade e autonomia não são benefícios isolados. Devem reduzir o esforço do usuário e produzir resultados úteis e confiáveis, não criar supervisão excessiva ou novos problemas.

## PD-05 — Workflows Centrais — APPROVED

O JARVIS utiliza **um workflow universal, adaptativo e supervisionado** para consultas simples, objetivos de múltiplas etapas, ações externas e atividades persistentes. Não existe um workflow nativo diferente para cada aplicativo de negócio.

### Fluxo conceitual

1. **Receber solicitação:** por texto, voz ou outro canal disponível.
2. **Compreender intenção e contexto:** identificar objetivo, recuperar informações relevantes e esclarecer ambiguidades quando necessário.
3. **Determinar recursos necessários:** responder diretamente ou descobrir/selecionar tools, planejamento ou agentes, proporcionalmente à complexidade.
4. **Verificar ação e autoridade:** avaliar adequação ao objetivo, riscos, limites e necessidade de confirmação.
5. **Executar ou responder:** realizar apenas operações autorizadas ou responder sem uso de ferramentas quando suficiente.
6. **Apresentar resultado e manter continuidade:** comunicar sucesso, falhas, incertezas, pendências e informações relevantes preservadas conforme as regras de memória.

O fluxo **não** exige seis chamadas fixas ao modelo. Pode retornar a etapas anteriores, pedir esclarecimentos ou interromper uma ação.

### Comportamentos exemplificativos

| Tipo de solicitação | Conduta esperada |
|---|---|
| Pergunta simples | Responder diretamente, sem agente desnecessário. |
| Consulta externa | Selecionar a tool conectada e autorizada; apresentar dados reais. |
| Pesquisa/comparação | Coordenar múltiplas consultas, reunir evidências e comparar alternativas. |
| Alteração externa | Conferir intenção, conteúdo, alvo e autorização antes de executar. |
| Atividade recorrente/persistente | Preservar estado e retomar de acordo com gatilhos e limites autorizados. |
| Necessidade ainda não atendida | Explicar a lacuna e, quando apropriado, propor nova capacidade. |

### Exceções e controle do usuário

- **Tool ausente:** informar limitação e, se pertinente, propor integração.
- **Dados insuficientes:** solicitar apenas o esclarecimento necessário; não inventar informações.
- **Autorização negada:** não executar; oferecer alternativas permitidas quando houver.
- **Falha:** informar etapas concluídas, falhas e pendências sem alegar sucesso indevido.
- **Interrupção/queda:** permitir retomada segura sem repetir cegamente efeitos externos, especialmente quando o resultado anterior for desconhecido.
- **Memória indisponível:** continuar funções independentes, deixando claras as limitações de contexto.
- **Acompanhamento/interrupção:** permitir ao usuário acompanhar tarefas e interrompê-las quando tecnicamente possível, sem sugerir que interromper reverta ações já efetivadas.

## PD-06 — Escopo Inicial do Produto (MVP) — APPROVED

O MVP deverá comprovar três capacidades fundamentais: **conversação com continuidade, uso de ferramentas de domínios diferentes e execução real supervisionada**. Será uma aplicação utilizável e evolutiva, não uma demonstração descartável. A entrega pode ocorrer por incrementos menores.

### IN SCOPE — MVP

| Capacidade | Resultado mínimo esperado |
|---|---|
| Conversação | Chat em **texto e voz**, com histórico e contexto compartilhados. |
| Memória | Integração com Sofias Memory para registro e recuperação de informações relevantes entre conversas. |
| Conhecimento | Recuperar informações com indicação de fontes quando disponíveis. |
| Catálogo de tools | Descobrir capacidades instaladas, conectadas, habilitadas e autorizadas. |
| Seleção de ferramentas | Escolher tools apropriadas a cada solicitação. |
| Integrações | Comprovar utilização de **pelo menos dois domínios externos distintos**. |
| Execução supervisionada | Efetuar ação real, respeitando autorização e confirmação quando necessária. |
| Tarefas | Acompanhar atividades e permitir interrupção quando possível. |
| Interface utilizável | Conversar, acompanhar ações e configurar integrações essenciais. |

### Três cenários de validação

1. **Continuidade:** encerrar uma sessão e retomar depois um assunto com recuperação de informações persistidas pertinentes.
2. **Extensibilidade:** consultar dois serviços de domínios distintos usando o mesmo mecanismo geral, sem regras de negócios específicas desses serviços no Core.
3. **Execução real:** solicitar uma alteração em serviço externo; JARVIS prepara a ação, verifica/obtém autorização aplicável, executa e apresenta o resultado verificável.

Nenhum serviço ou fornecedor específico é obrigatório por esta Product Definition. A escolha das integrações de validação será feita posteriormente.

### Fora do escopo **obrigatório** do MVP

Criação automática de agentes; geração de código executável; marketplace público; colaboração multiagente avançada; controle avançado de tela/desktop; monitoramento ambiental contínuo; galáxia 3D; especialização de desenvolvimento; multiusuário; autonomia progressiva com permissões persistentes. Essas capacidades não estão rejeitadas: integram a visão futura quando aplicável (PD-09).

A **proatividade supervisionada e a sugestão de novas capacidades** estão aprovadas como comportamento do produto; sua implementação completa **não** é condição para fechar o MVP.

## PD-07 — Regras de Negócio e Limites Operacionais — APPROVED

**Princípio:** autonomia para compreender, planejar e propor; **autoridade proporcional e controlada** para executar. O JARVIS não precisa confirmar cada leitura simples já autorizada, mas não pode presumir autorização para alterações ou ações críticas.

### Categorias conceituais de autonomia

| Nível | Exemplo de comportamento | Limite |
|---|---|---|
| 1 — Conversar e raciocinar | Responder, analisar, sugerir, planejar | Sem confirmação por operação. |
| 2 — Consultar | Ler dados em integrações conectadas | Dentro dos acessos concedidos. |
| 3 — Preparar | Elaborar rascunhos e propostas | Sem efeitos externos não autorizados. |
| 4 — Alterar | Enviar, criar ou modificar informações | Autoridade compatível com a operação. |
| 5 — Crítico | Excluir, executar código desconhecido, ampliar acesso sensível | Controles adicionais e aprovação explícita. |

Os níveis são **categorias de produto**, não um enum, schema ou mecanismo de policy aprovado.

### Regras aprovadas

| ID | Regra | Comportamento obrigatório |
|---|---|---|
| **RN-01** | Autoridade do usuário | Usuário controla integrações e permissões; memória, skill, tool e agente não concedem autoridade. |
| **RN-02** | Execução controlada | Todas as tools, plugins e agentes obedecem aos mesmos controles de autorização do JARVIS. |
| **RN-03** | Conhecimento ≠ execução | Sofias Memory somente persiste e recupera informações, inclusive definições de skills/agentes; **não** executa operações. |
| **RN-04** | Evolução supervisionada | JARVIS pode pesquisar, preparar e propor capacidades; criação, instalação, ativação e ampliação de acesso dependem de aprovação. Criar definição não autoriza executá-la. |
| **RN-05** | Transparência | Distinguir claramente intenção, ação realizada, sucesso verificado, falha, incerteza e pendência. |
| **RN-06** | Segurança e privacidade | Proteger credenciais/dados sensíveis; informações externas não podem elevar sua própria autoridade. |
| **RN-07** | Continuidade e recuperação | Preservar estado necessário; evitar duplicação de efeitos externos quando resultado anterior for desconhecido. |
| **RN-08** | Controle de recursos | Respeitar limites configurados de custo, recursos, modelos e ferramentas, inclusive em tarefas longas. |

A autorização para **preparar** uma mensagem, por exemplo, não é automaticamente autorização para **enviá-la**; permissão de leitura não autoriza exclusão.

## PD-08 — Restrições e Dependências — APPROVED

| ID | Restrição consolidada |
|---|---|
| **R-01** | JARVIS é produto independente do Sofia's Assistant. |
| **R-02** | Sofias Memory é o serviço especializado de memória e conhecimento. |
| **R-03** | Sofias Memory não executa operações. |
| **R-04** | Regras de domínio das integrações não pertencem ao JARVIS Core. |
| **R-05** | Reutilização de componentes do Sofia's Assistant depende de comprovação funcional e avaliação de adequação/acoplamento. |
| **R-06** | Operações externas respeitam permissões e capacidades reais dos serviços utilizados. |
| **R-07** | Primeiro produto utilizável atende um usuário proprietário por instalação. |
| **R-08** | Desenvolvimento prioriza incrementos funcionais, verificáveis e com valor observável. |

### Dependências funcionais

- **Sofias Memory — definida:** persistência/recuperação de memória cognitiva, conhecimento e definições declarativas de skills e agentes. Sua eventual evolução requer análise dos contratos e funcionalidades existentes; a execução continua no JARVIS.
- **Ferramentas/serviços externos — variáveis:** podem falhar ou estar desconectados; sua indisponibilidade não deve, por si, derrubar o assistente inteiro.
- **Inferência de IA — necessária, tecnologia aberta:** não vincular definitivamente o produto nesta fase a um único fornecedor ou modelo.

### Escolhas técnicas OPEN, não aprovadas

Linguagem do Core; PySide6, web ou UI híbrida; desktop exclusivo ou outros ambientes; MCP como protocolo obrigatório; sistemas operacionais suportados; local/cloud/híbrido; modelos locais/cloud/ambos. Estratégia de distribuição/atualização e licença definitiva do JARVIS permanecem **DEFERRED**.

O Sofia's Assistant é projeto de propriedade do usuário e não possui licença definitiva estabelecida; o licenciamento de seu código próprio **não** foi definido como bloqueio de reutilização. Licenças de dependências ou código de terceiros devem ser verificadas quando houver transferência concreta.

**Independência não significa ausência de dependências:** limitações e falhas externas devem ser explicitadas sem alegar acesso ou resultados inexistentes.

## PD-09 — Limites do Produto e Evolução Futura — APPROVED

### FUTURE / DEFERRED — possibilidades preservadas

| Capacidade | Objetivo futuro |
|---|---|
| **Agent Builder** | Sugerir, configurar, criar e habilitar agentes sob aprovações adequadas. |
| **Skill Evolution** | Identificar necessidades e sugerir novas skills ou refinamentos. |
| **Plugin Discovery** | Localizar alternativas e preparar propostas de novas integrações. |
| **Autonomia progressiva** | Avaliar permissões persistentes restritas e revogáveis para atividades delimitadas. |
| **Proatividade avançada** | Acompanhar eventos, objetivos e atividades de forma contínua e autorizada. |
| **Multi-Agent Collaboration** | Coordenar vários agentes especializados quando houver benefício. |
| **Desktop Automation** | Interagir mais profundamente com aplicações/janelas/sistema operacional. |
| **Ambient Context** | Utilizar contexto de tela/aplicações/ambiente com proteção de privacidade. |
| **Knowledge Galaxy** | Explorar visualmente memória e conhecimento, incluindo visualização 3D. |
| **Developer Assistant** | Capacidades especializadas de desenvolvimento e manutenção de software. |
| **Multi-Channel** | Canais adicionais como WhatsApp, Telegram e APIs. |
| **Multi-User** | Identidades, usuários e autorizações separados. |

A presença nessa relação **não estabelece prioridade, cronograma ou compromisso de entrega**. Criação supervisionada de agentes e descoberta assistida de integrações são parte da visão aprovada, mas sua implementação completa fica além do MVP.

### OUT OF SCOPE — limites permanentes de responsabilidade

- Embutir no JARVIS Core regras específicas de assistência técnica, CRM, e-commerce ou qualquer domínio de integração.
- Transformar o Sofias Memory em executor de agentes, ferramentas, scripts ou operações externas.
- Substituir os aplicativos existentes como objetivo do produto.
- Executar componentes externos irrestritamente ou permitir que plugins contornem a autorização central.
- Modificar silenciosamente o próprio Core em produção.
- Tratar informação recordada ou recomendação de agente como concessão de permissão.

**Diretriz de evolução:** cada capacidade adicionada deve oferecer benefício identificável, preservar segurança, transparência e possibilidade de reversão. Não criar um agente quando uma ferramenta simples resolve o problema; não converter automaticamente definições declarativas em código executável.

## Fronteiras conceituais transversais — consolidação do Discovery

| Conceito | Papel aprovado |
|---|---|
| **Capability** | Declara habilidade disponível ao assistente. |
| **Tool** | Executa operação concreta. |
| **Plugin** | Agrupa capacidades de um domínio/serviço. |
| **Skill** | Conhecimento procedural reutilizável. |
| **Agent** | Conduz objetivos que podem exigir planejamento, várias etapas e acompanhamento. |
| **Channel** | Recebe solicitações e entrega respostas. |

JARVIS responde por **orquestração, execução, policy, auditoria e estado operacional**. Sofias Memory responde por **persistência e recuperação de memórias, conhecimento, provenance e definições/configurações declarativas**. Implementações executáveis ou referências controladas a elas pertencem ao JARVIS; conteúdo recuperado nunca confere autorização.

A descoberta dinâmica de capacidades é aprovada com **preparação assistida e instalação controlada**: JARVIS pode identificar lacunas, localizar soluções, examinar requisitos e preparar propostas sem efeitos externos não autorizados; instalar, conectar contas, ativar ou aumentar permissões requer aprovação. Proatividade supervisionada (**opção B**) está aprovada. Autonomia progressiva com permissões persistentes (**opção C**) permanece DEFERRED.

**Separação de decisões:** criar configuração declarativa de um agente ≠ criar código executável ≠ ativar agente ≠ autorizá-lo a agir. O formato técnico exato desses artefatos permanece aberto.

## Exemplos de validação — não são requisitos de domínio

A rotina de uma assistência técnica foi usada no Discovery para ilustrar uma possível tool externa que consulta ordens de serviço. Também podem ser usados calendário, GitHub ou outro serviço. **O JARVIS não terá módulo nativo obrigatório de assistência técnica.** As integrações reais do MVP ainda serão escolhidas.

## Questões ainda abertas para PRD, Specs, Contracts e Architecture

Estas questões **não impedem a aprovação da Product Definition**; não devem ser respondidas por suposição:

1. Escolha das duas integrações/domínios reais para validar o MVP e da operação externa de escrita supervisionada.
2. Requisitos detalhados da experiência de chat/voz, estados visíveis de task e interações de confirmação.
3. Critérios verificáveis de persistência, busca, atualização e proveniência de memórias/conhecimento.
4. Avaliação de contratos e capacidades de Skills/Agents existentes no Sofias Memory; mudanças necessárias, se houver, para definições declarativas.
5. Auditoria dos componentes candidatos do Sofia's Assistant e decisão justificada de reutilizar/adaptar/reimplementar.
6. Escolha de stack, ambiente, interface, protocolo de ferramentas, provedores de IA, isolamento e deployment.
7. Definições operacionais de permissões, grants, confirmações, revisão de decisões, auditoria e recuperação.
8. Metas de qualidade, limites mensuráveis, testes e validação humana para os slices posteriores.

Nenhuma dessas questões autoriza iniciar implementação sem os artefatos e aprovações adequados.

## Decisões e aprovação

| Ponto | Título | Estado |
|---|---|---|
| **PD-01** | Visão do Produto | **APPROVED** |
| **PD-02** | Problema que o Produto Resolve | **APPROVED** |
| **PD-03** | Público-alvo e Atores | **APPROVED** |
| **PD-04** | Proposta de Valor | **APPROVED** |
| **PD-05** | Workflows Centrais | **APPROVED** |
| **PD-06** | Escopo Inicial (MVP) | **APPROVED** |
| **PD-07** | Regras de Negócio e Limites Operacionais | **APPROVED** |
| **PD-08** | Restrições e Dependências | **APPROVED** |
| **PD-09** | Limites do Produto e Funcionalidades Futuras | **APPROVED** |

Cada ponto foi discutido e recebeu aprovação explícita em conversa antes desta materialização. **O documento DRAFT gerado anteriormente não constituiu baseline e foi substituído por esta consolidação.**

## Project State / Next Step

| Campo | Estado |
|---|---|
| **Project** | JARVIS |
| **Current phase** | Product Definition concluída |
| **Current role** | Product Engineer |
| **Approved** | PD-01 a PD-09; Discovery anterior; visão universal, Core independente, Memory somente informacional, MVP delimitado, autoridade central e evolução supervisionada |
| **Open** | Detalhes verificáveis do comportamento e escolhas técnicas posteriores |
| **Deferred** | Agentes criados automaticamente, código executável gerado, marketplace, multiagente, ambient/desktop avançado, Knowledge Galaxy, modo Developer, multiusuário e autonomia progressiva |
| **Current artifact** | `docs/product-manager/02-JARVIS-Product-Definition.md` |
| **Current Slice** | Nenhum |
| **Next legitimate step** | Iniciar PRD a partir desta Product Definition, discutindo e aprovando os pontos individualmente antes de materializar o próximo artefato. |

---

*Esta Product Definition materializa o baseline aprovado do produto. Alterações posteriores relevantes de visão, escopo, limites, autoridade ou dependências exigem decisão explícita do proprietário.*

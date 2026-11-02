# TB-02 — Supervised Supersede / Forget Test

**Estado:** ciclo cognitivo supervisionado VALIDADO na instância real (2026-10-31); Knowledge Retrieval ainda pendente.

## Escopo e isolamento

O fluxo modifica **somente memórias temporárias** criadas pelo comando
\`--memory-test-create\`. Essas memórias têm conteúdo fixo, tipo \`semantic\`,
escopo \`project:jarvis\`, \`origin_kind=assistant_generated\`, marcador
\`jarvis-tb02-test:<UUID-da-criação>\` e registro em allowlist persistente
do SQLite local. Para Supersede ou Forget, é obrigatório encontrar o UUID
nessa allowlist, verificar a mesma URL, tipo, escopo, estado e marcador no
Sofias Memory. A memória pessoal de preferência por teal
(\`ab89ac04-7134-49c6-9fa2-2880a296d50a\`) não foi criada por esse
procedimento e **não é elegível**.

A migração SQLite \`v2 → v3\` preserva o histórico de conversas e os
intents já existentes, adiciona a tabela de memórias descartáveis e
registra \`operation_kind\` / \`target_memory_id\` no journal. Mutação
pendente, \`in_flight\` ou \`unknown\` bloqueia novas mutações no mesmo
UUID. Não há repetição automática nem reconciliação automática.

## Etapa A — Somente testes locais

\`\`\`powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --memory-test-list
\`\`\`

Não avance se a suíte não estiver 100% verde.

## Etapa B — Criar amostra descartável real (consentimento local)

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-test-create
\`\`\`

Verifique o conteúdo fixo e a confirmação. Digite \`CRIAR TESTE\` apenas se
aceitar criar exatamente **uma nova memória de laboratório** no
Sofias Memory. Registre o \`memory_id\` retornado (chamaremos \`ID_A\`).
Se \`CANCELLED\`, nenhuma mutação é enviada.

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-get ID_A
.\.venv\Scripts\python.exe main.py --memory-test-list
\`\`\`

O Get deve mostrar \`active\`, \`semantic\`, \`project:jarvis\`, conteúdo
\`JARVIS TB-02 TESTE DESCARTAVEL: valor de laboratorio = A.\`,
marcador de origem e ID A.

## Etapa C — Substituir somente ID_A

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-test-supersede ID_A
\`\`\`

O comando faz preflight (Get e allowlist) antes de pedir confirmação.
Somente a digitação literal \`SUBSTITUIR ID_A\` (substituindo pelo UUID
completo mostrado no terminal) autoriza a mutação. Uma segunda validação
acontece logo antes do envio. Esperado: \`CONFIRMED\`, \`old_memory_id=ID_A\`,
\`replacement_memory_id=ID_B\` (novo UUID). Em seguida:

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-get ID_A
.\.venv\Scripts\python.exe main.py --memory-get ID_B
\`\`\`

O antigo deve estar \`superseded\`, referenciando ID_B; o novo \`active\`
com conteúdo \`... valor de laboratorio = B.\`. Nenhum outro UUID muda.

## Etapa D — Esquecer as duas memórias de teste

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-test-forget ID_B
.\.venv\Scripts\python.exe main.py --memory-test-forget ID_A
\`\`\`

Em **cada** confirmação, digite literalmente \`ESQUECER <UUID_COMPLETO>\`.
O Sofias Memory preservará o tombstone de cada registro, mas limpará
seu conteúdo e seu escopo. Esquecer ID_B **não** esquece automaticamente
ID_A (superseded), por isso há dois comandos independentes.

Depois:

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-get ID_A
.\.venv\Scripts\python.exe main.py --memory-get ID_B
.\.venv\Scripts\python.exe main.py --memory-test-list
\`\`\`

Get deve mostrar \`forgotten\`, \`scope=null\`, \`content=null\` para
ambos. Em \`--memory-test-list\`, os dois IDs permanecem registrados com
\`lifecycle=forgotten\` apenas para auditoria local.

## Abortos e resultados incertos

Se surgir \`RESULT_UNKNOWN\` ou se o processo for interrompido durante
uma operação, **não refaça a mutação com uma nova chave**. Consulte apenas:

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --memory-operation UUID_DA_OPERACAO
.\.venv\Scripts\python.exe main.py --memory-test-list
\`\`\`

Envie os status sem API key. O JARVIS bloqueia automaticamente novas
mutações sobre o alvo incerto; reconciliação requer análise específica,
fora deste smoke. A ausência do \`CONFIRMED\` não prova ausência de efeito
na VPS.

## Itens ainda não aceitos

- Testes automatizados (127 PASS) e Create/Get/Recall/Supersede/Forget reais
  validados pelo proprietário, com IDs e estados documentados abaixo.
- Não habilitar Supersede/Forget genéricos no chat/UI.
- Knowledge Retrieval com dataset ativo e fonte documental permanece
  pendente, independentemente desta prova de ciclo cognitivo.


## Evidência final de validação humana — 2026-10-31

**Resultado:** PASS do ciclo de vida da memória cognitiva, limitado ao
fluxo controlado e a esta instalação. A prova consiste nas saídas CLI
fornecidas pelo proprietário; não representa uma auditoria direta da
base PostgreSQL.

### Operações e identidades

| Etapa | operation_id | memory_id | Evidência |
|---|---|---|---|
| Create temporário | \`7cf8b746-62ae-4844-96ac-df79ed15a3e3\` | \`a34c1a18-0109-4568-8b0e-02bd97c169b5\` | CONFIRMED, semantic, project:jarvis, active, conteúdo A |
| Supersede A → B | \`efe56ce7-7606-45b8-b9c1-c9463609fcd6\` | A → \`3b9f338d-7c19-4be7-941f-0ec1195f06e8\` | CONFIRMED; A superseded e superseded_by=B; B active, conteúdo B |
| Forget B | \`7e82a675-12c8-4fd1-b425-7a7c2dbd0f8d\` | \`3b9f338d-7c19-4be7-941f-0ec1195f06e8\` | CONFIRMED; B forgotten, content/scope/source_ref=null; A permanece superseded |
| Forget A | \`86497356-3589-4649-8af5-48ba3e99f048\` | \`a34c1a18-0109-4568-8b0e-02bd97c169b5\` | CONFIRMED; A forgotten, content/scope/source_ref=null; B permanece forgotten |

**Get remoto após ambos os Forget**:
- A: \`lifecycle=forgotten\`, \`content=null\`, \`scope=null\`,
  \`forgotten_at=2026-10-31T21:52:40.452087Z\`, conserva
  \`superseded_by=3b9f338d-7c19-4be7-941f-0ec1195f06e8\` para
  linhagem do tombstone. \`provenance.source_ref=null\`.
- B: \`lifecycle=forgotten\`, \`content=null\`, \`scope=null\`,
  \`forgotten_at=2026-10-31T21:32:31.041768Z\`, sem sucessor.
  \`provenance.source_ref=null\`.
- A lista **local** \`--memory-test-list\` contém ambos como
  \`forgotten\`, com \`root_memory_id=A\`; mantém o escopo
  \`project:jarvis\` apenas como metadado operacional do JARVIS,
  **não** como escopo ativo no Sofias Memory.

**Prova de não interferência em memória real:**
\`--memory-get ab89ac04-7134-49c6-9fa2-2880a296d50a\`
retornou \`FOUND\`, \`profile\`, \`global\`, \`active\`, conteúdo
\`Para interfaces gráficas, prefiro a cor teal.\` com proveniência
\`origin_kind=user_asserted\`, \`source_system=jarvis\`, \`source_ref=memory-operation:d168be4b-e411-478c-b881-e1d61f91b172\`.
O registro não foi afetado pelas quatro operações do laboratório.

### Testes automatizados

Após a correção de parsing do JSON multiline no teste da confirmação
do Forget, o proprietário informou \`127 passed in 3.90s\`
no Windows, Python 3.13. Isso cobre a suíte atual no momento da prova;
não há alegação de que falhas simuladas tenham sido reproduzidas na VPS.

### Limites e próximos passos

O ciclo cognitivo supervisionado está **validado**. Ainda não estão
concluídas: prova de recuperação documental \`Knowledge Retrieval\`
com dataset ativo e source references reais, integração da evidência
documental no desktop, e reconciliação supervisionada de operações com
estado \`unknown\` (não exercitada na VPS).

Os quatro datasets da consulta real \`--knowledge-datasets\` tinham
\`status=deleted\` e nomes \`production-smoke-*\`; não foi identificado
um dataset ativo apto ao teste. A memória cognitiva teal não faz
parte desses datasets.

**Estado do Slice TB-02: IN PROGRESS.** Nenhuma autorização de merge
para \`main\` é inferida desta validação.

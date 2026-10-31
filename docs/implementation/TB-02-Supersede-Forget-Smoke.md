# TB-02 — Supervised Supersede / Forget Test

**Estado:** implementação na branch \`feat/tb-02-memory-knowledge\`, validação Windows/VPS pendente.

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

- Testes automatizados adicionais e smoke real ainda não executados no
  Windows do proprietário.
- Não habilitar Supersede/Forget genéricos no chat/UI.
- Knowledge Retrieval com dataset ativo e fonte documental permanece
  pendente, independentemente desta prova de ciclo cognitivo.

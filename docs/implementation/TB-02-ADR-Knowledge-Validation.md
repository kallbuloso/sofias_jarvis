# TB-02 — Validação de Knowledge Retrieval com ADR-0001

**Estado:** autorizado pelo proprietário para criar o dataset e ingerir um
ADR real; código e testes adicionados na branch; **nenhuma criação/ingestão
real foi executada por esta alteração**.

## Fonte exata

- Arquivo de origem do repositório: `docs/product-manager/07-JARVIS-ADRs.md`
- Documento: `ADR-0001 — Modular Monolith as the JARVIS Core Architecture`
- Estado do ADR: `ACCEPTED`
- Dataset permitido: `jarvis-knowledge`
- Nome humano: `JARVIS Knowledge`
- Fonte inserida: apenas a seção literal iniciada em `# ADR-0001` e
  encerrada antes de `# ADR-0002` (sem reescrever a decisão)
- SHA-256 do conteúdo calculado localmente e registrado em metadata
  como `source_sha256`
- Não importa o arquivo inteiro, outros ADRs, segredos ou dados pessoais

## 1. Testar apenas localmente

```powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

Não prossiga à operação real se houver falhas. Os **127 testes anteriores**
são a última suíte validada pelo proprietário antes deste incremento;
os testes adicionais de ingestão ainda requerem execução no Windows.

## 2. Criar somente o namespace autorizado

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-create-dataset
```

Revise o destino e confirme literalmente:

```text
CRIAR DATASET jarvis-knowledge
```

O endpoint é `POST /api/v1/datasets` (HTTP 201). A resposta deve ser
`CREATED` com `dataset_id` e slug esperado; uma segunda chamada com
mesma identidade retorna `ALREADY_EXISTS` sem novo POST.
Se o slug já pertencer a outro dataset ou estiver deletado, a operação
é bloqueada e não recria silenciosamente um namespace.

Verifique:

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-datasets
```

Esperado: `jarvis-knowledge`, `status=active`. Os datasets antigos
`production-smoke-*` marcados `deleted` não devem ser usados.

## 3. Ingerir exclusivamente o ADR-0001

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-ingest-adr
```

O programa exibe documento, caminho, SHA-256 e bytes. Confirme:

```text
INGESTIR ADR-0001
```

O endpoint é `POST /api/v1/remember` com `dataset=jarvis-knowledge`,
`mode=full`, `wait=false`, `force=false`, conteúdo literal da
seção e metadata de proveniência. **A operação pode usar serviços
externos de embedding e LLM e gera persistência real.**

Resultado típico: `ACCEPTED`, `pipeline_status=queued`,
`run_id=<UUID>`. Isso **não comprova** indexação concluída.

**Se o envio resultar em erro de rede, resposta incerta, ou interrupção
do processo, pare e não repita imediatamente.** A falta do retorno não
prova ausência de efeito na VPS; a operação pode ter enfileirado.
A deduplicação do Memory não substitui a análise do histórico de Runs
e Sources em caso de resultado desconhecido.

## 4. Acompanhar o PipelineRun, sem retries automáticos

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-run RUN_ID
```

Substitua RUN_ID pelo UUID real da etapa 3. Execute de novo apenas
este comando de leitura até o estado terminal. Se ficar `failed`,
registre `error_code`; não use retry sem diagnóstico.
O estado `succeeded` é pré-requisito para o passo seguinte.

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-stats
```

Verifique se o dataset tem `sources.active >= 1` e
`chunks.active >= 1`. Contadores zerados indicam que a recuperação
documental ainda não está comprovada.

## 5. Recuperação verificável

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-query --knowledge-dataset jarvis-knowledge
```

Pergunta sugerida:

```text
Por que o Core do JARVIS usa Modular Monolith e não microsserviços?
```

Critérios:
- `status=RESULTS_FOUND` e `query_id` válido.
- `context[].text` contém trechos reais do ADR autorizado.
- `references[]`, quando retornadas, são derivadas de chunks
  recuperados e mantêm `source_id`, `document_id` e `chunk_id`.
- Resposta `NO_RESULTS` não significa falha de rede nem comprova
  resultado; confirmar `run.status=succeeded` e chunks ativos.
- O adapter usa `mode=chunks`, sem segunda resposta gerada pelo
  Sofias Memory. O backend grava uma auditoria `query_id`.

## Limites

- O adapter documental e a CLI não enviam evidências documentais ao
  OpenAI dentro do chat desktop ainda. Esse é o próximo incremento.
- `Supersede/Forget` e a memória teal são independentes de datasets.
- TB-02 permanece `IN PROGRESS` até retrieval real, proveniência e
  integração de conhecimento ao desktop serem validados.
- `main` não é alterada nem há autorização de merge.


## Evidência real — Dataset criado e listado (2026-10-31)

O proprietário executou `--knowledge-create-dataset`, digitou a autorização
literal `CRIAR DATASET jarvis-knowledge` e recebeu:

- `status=CREATED`
- `dataset_id=21100a21-d6e3-4dcc-a730-fe2f26111b5c`
- `slug=jarvis-knowledge`
- `name=JARVIS Knowledge`

A listagem posterior por `--knowledge-datasets` retornou `total=5` e
confirmou que `jarvis-knowledge` está `active`; os quatro outros
datasets `production-smoke-*` permanecem `deleted`.

**Critério de criação/listagem: PASS.** Não há ainda prova de
`Remember`, processamento `mode=full`, chunks ativos, `Recall`
documental ou referências reais. A criação do dataset não implica
ingestão. O último relatório do proprietário sobre testes adicionais
apontou 140 aprovados e duas falhas, que tiveram correções publicadas
no commit `76cb87f`. A suíte pós-correção não foi reportada ainda.

**Próximo teste autorizado:** validar pytest pós-correção e, somente
se passar, executar `--knowledge-ingest-adr` com confirmação
`INGESTIR ADR-0001`; registrar `run_id` sem repetir a operação.


## Evidência real — Ingestão do ADR aceita, processamento pendente (2026-10-31)

O proprietário executou a suíte completa no Windows e relatou
`142 passed in 3.99s`. Em seguida, executou
`--knowledge-ingest-adr`, conferiu a origem e autorizou literalmente
`INGESTIR ADR-0001`.

Payload de origem selecionado pelo JARVIS:
- Documento: `JARVIS ADR-0001 — Modular Monolith`
- Caminho: `docs/product-manager/07-JARVIS-ADRs.md`
- SHA-256 do recorte: `a684bed7596e6d2f8f1d2a1d44a8ec65e96bf57851d8abd822bcd58c290269ed`
- Tamanho: 2.882 bytes
- Dataset previamente confirmado: `jarvis-knowledge`
  (`21100a21-d6e3-4dcc-a730-fe2f26111b5c`)

Retorno real da operação:
- `status=ACCEPTED`
- `run_id=21899eed-281f-4399-a6f4-8d73750da71b`
- `pipeline_status=queued`
- `dataset_id=null`, `source_id=null` na resposta inicial

**Aceitação de submissão: PASS.** O retorno `queued` não comprova
processamento, persistência de chunks ou disponibilidade para retrieval.
As identidades de dataset e source no resultado de submissão ainda
não estavam materializadas. Não reexecutar `--knowledge-ingest-adr`
para verificar andamento.

**Próxima verificação estritamente read-only:**

```powershell
.\.venv\Scripts\python.exe main.py --knowledge-run 21899eed-281f-4399-a6f4-8d73750da71b
```

Se retornar `succeeded`, consultar `--knowledge-stats`;
somente após fonte e chunks ativos, executar `--knowledge-query`
com slug `jarvis-knowledge` e inspecionar proveniência dos resultados.
Se `failed`, capturar `error_code`, sem novo envio/retry.

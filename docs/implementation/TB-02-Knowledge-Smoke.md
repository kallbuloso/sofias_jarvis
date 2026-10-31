# JARVIS — TB-02 Step 05: Knowledge Retrieval validation

**Status:** published to feature branch; real Windows test pending.
**API:** Sofias Memory v0.7.0 / contract 1.

## Verified contract design

Knowledge Retrieval uses \`POST /api/v1/recall\`, NOT the Cognitive
\`POST /api/v1/memories/recall\` endpoint. The first JARVIS adapter uses
only \`mode=chunks\`, \`only_context=true\`, \`include_references=true\`,
\`include_session_context=false\`, with one or more explicit dataset
slugs. No Sofias Memory RAG answer is generated.

The response carries a durable \`query_id\` audit identifier on the
Sofias Memory server, along with retrieved chunk text, dataset,
source/document/chunk IDs, source names, similarity scores, and
references when provided by the service. JARVIS validates references
against actual retrieved chunks and never makes up a citation.

**Retrieval is read-only for stored knowledge, but a Query audit record
is persisted by the Sofias Memory server.** It requires explicit
activation; no knowledge requests are made by ordinary chat.

## Windows runbook

\`\`\`powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q

cd frontend
npm run build
cd ..

.\.venv\Scripts\python.exe main.py --knowledge-datasets
\`\`\`

Review \`items\` and choose a dataset slug where knowledge has been
ingested and processed. If no datasets are available, report that
instead of inventing a dataset or writing new content.

Then run:

\`\`\`powershell
.\.venv\Scripts\python.exe main.py --knowledge-query --knowledge-dataset EXISTING_DATASET_SLUG
\`\`\`

At the prompt, enter a question that can be answered from that dataset.
If \`RESULTS_FOUND\`, verify that every returned \`reference\` refers
to a real retrieved \`context\` \`chunk_id/source_id/document_id\`.
If \`NO_RESULTS\`, distinguish an empty retrieval from a service error.
Do not treat a dataset with no processed chunks as a Knowledge failure.
If an error is returned, capture the safe status; do not share API keys.

## Current acceptance limits

- Offline unit/CLI tests were added, but are not yet validated by owner.
- No dataset query has yet been observed from the deployed service.
- The Knowledge results are exposed through CLI, not yet selected for
  context inside the desktop UI.
- Supervised Supersede/Forget lifecycle **has been verified against the real service** (2026-10-31); see `TB-02-Supersede-Forget-Smoke.md`.
- TB-02 remains IN PROGRESS; no merge to main is authorized.


## Observação real de datasets — 2026-10-31

O proprietário executou `--knowledge-datasets` com sucesso e recebeu `total: 4`, todos os registros `production-smoke-*` com `status: deleted`. Isso comprova leitura do catálogo, **não** recuperação documental com proveniência: nenhum dataset ativo foi encontrado na listagem. Não criar dados fictícios sem autorização e não confundir esses datasets com memórias cognitivas pessoais.


## Teste aprovado com ADR-0001 (implementação pendente de validação real)

O proprietário autorizou a criação do dataset `jarvis-knowledge` e a ingestão de **um ADR não sensível do JARVIS**. Foi escolhido o ADR-0001 aprovado, extraído literalmente de `docs/product-manager/07-JARVIS-ADRs.md`. Adicionados comandos supervisionados para criar o dataset (201), enviar `mode=full` com resposta assíncrona (202), acompanhar o Run, consultar estatísticas e recuperar chunks. Nenhuma alteração foi enviada à VPS por esses commits. Roteiro: `docs/implementation/TB-02-ADR-Knowledge-Validation.md`.

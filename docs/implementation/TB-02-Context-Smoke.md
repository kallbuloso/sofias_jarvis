# JARVIS — TB-02 Step 03: Cognitive Context Smoke

**Status:** Feature branch implementation; owner's Windows validation pending.

## Verified prerequisites

Sofias Memory service reported by the owner as compatible: v0.7.0,
API contract 1, Cognitive Memory contract 1, five capabilities present.
Live explicit Create→Recall has succeeded with an existing global
profile item.

## Runbook (Windows 11 PowerShell)

\`\`\`powershell
git fetch origin
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --memory-get ab89ac04-7134-49c6-9fa2-2880a296d50a
.\.venv\Scripts\python.exe main.py --chat --model gpt-6-luna --use-memory --memory-scope global
\`\`\`

In the console chat, ask \`Qual minha cor preferida para interfaces gráficas?\`.
Expect a response acknowledging the stored preference and the safe
post-response diagnostic \`"memory_retrieval": "RESULTS_FOUND"\`,
\`memory_ids\` containing the existing memory ID, and \`scopes=["global"]\`.
The output \`NO_RESULTS\` means a real completed recall with no hits.
\`UNAVAILABLE\` means the retrieval could not be completed and must not
be represented as successful memory recall.

**Safety:** This is an explicit read-only recall with a user-specified
scope. It sends the prompted text to Sofias Memory and sends bounded
retrieved evidence to the configured OpenAI model for this inference.
Nothing is automatically stored as a new Cognitive Memory, and the
retrieved evidence is not appended to SQLite conversation history.
The default \`--chat\` path does not query Memory.

Test a degraded case separately (optional) by using \`--use-memory\`
with an absent credential or a deliberately unreachable HTTPS origin
in \`JARVIS_MEMORY_URL\` (avoid editing the saved real configuration).
The chat must continue, clearly signaling \`UNAVAILABLE\`, without
claiming retrieved memories. Do not put API keys into CLI arguments.

No real Supersede or Forget is included in this smoke. Both require
a separate deliberate confirmation and verification strategy.


## Evidence observed from the owner (2026-10-31)

The owner submitted actual results from the deployed Sofias Memory service:

- \`--memory-get ab89ac04-7134-49c6-9fa2-2880a296d50a\`: \`FOUND\`,
  active global profile with the teal preference and traceable
  \`source_ref: memory-operation:d168be4b-e411-478c-b881-e1d61f91b172\`.
- \`--chat --model gpt-6-luna --use-memory --memory-scope global\`:
  User asked about preferred color for graphical interfaces.
  JARVIS answered that teal is the stored preference.
  Explicit post-turn evidence: \`memory_retrieval: RESULTS_FOUND\`,
  \`memory_ids: [ab89ac04-7134-49c6-9fa2-2880a296d50a]\`,
  \`scopes: [global]\`.

**Observed:** real Get and memory-assisted inference passed in the console.
**Not yet observed:** latest full pytest output, desktop memory mode,
knowledge retrieval, Supersede, Forget, and failure-mode desktop behavior.

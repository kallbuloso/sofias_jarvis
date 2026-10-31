# JARVIS — TB-02 Step 04: Desktop Cognitive Recall Smoke

**Status:** feature branch published for Windows user validation. NOT Product Done.

The desktop integration is read-only for Cognitive Memory. There is no automatic
cognitive write, and no memory content or API key is sent to the Qt WebChannel:
only non-secret configuration flags and per-turn retrieval status.

## Build and run (PowerShell)

\`\`\`powershell
git switch feat/tb-02-memory-knowledge
git pull --ff-only origin feat/tb-02-memory-knowledge

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q

cd frontend
npm run build
cd ..

$env:JARVIS_MODEL = "gpt-6-luna"
.\.venv\Scripts\python.exe main.py --desktop
\`\`\`

## Human acceptance checklist

1. App starts and existing conversations remain intact.
2. **Consultar Sofias Memory** switch starts **OFF**; normal text chat works.
3. Turn the switch ON, choose **Global** explicitly. A short notice explains
   that the question goes to Sofias Memory and selected evidence to the model.
4. Ask: **Qual minha cor preferida para interfaces gráficas?**
5. Confirm incremental text response and the notice
   **Sofias Memory: memórias recuperadas para esta resposta.**
6. Switch to **Projeto JARVIS** and ask the same question. A valid outcome is
   NO_RESULTS (unless an equivalent project-scoped memory exists).
   Global facts are NOT automatically included in project scope.
7. Switch OFF: new turns must use only normal chat context; no Memory call.
8. Closing/reopening defaults the Memory switch OFF again. The conversation
   transcript remains continuous, but the retrieved auxiliary data was never
   persisted into SQLite as a separate conversation message.
9. If Memory becomes unavailable, UI displays an unavailable notice and
   the text chat continues, without claiming successful recall.
10. App can close normally; no API key appears in bootstrap/UI or journal.

Do not interpret a model saying "teal" on a **later non-memory turn** as
proof of Memory access: prior conversational history may contain the answer.
The retrieval status is the explicit evidence for the particular turn.

## Follow-up boundaries

Still needed before TB-02 Product Done:
- Verify the expanded pytest suite and desktop UI build on Windows.
- Verify real Supersede/Forget with explicit authorization and lifecycle
  evidence, without affecting unrelated memory records.
- Validate Knowledge Retrieval from a real dataset with source references.
- Final UI/product acceptance for provenance and degraded service behavior.

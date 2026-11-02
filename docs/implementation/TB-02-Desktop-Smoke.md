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


## Owner observation and follow-up (2026-10-31)

The owner reported \`85 passed in 2.61s\` on Windows **before**
the patches listed below. Screenshots show:

- Desktop chat worked with memory OFF, including a later answer that
  retrospectively claimed the assistant had "guessed" the preference.
  That explanation is not grounded in source evidence; do not represent
  a model's self-report about its hidden reasoning as an observed fact.
- With Memory ON and scope Global, the app answered the teal-preference
  query and displayed "memórias recuperadas para esta resposta."
- The status was rendered in a vertically oversized blue \`v-alert\` above
  the conversation; it obscured important history content.
- The user mentioned npm build but did not include the build output.
  Updated desktop assets being displayed support that a build was
  loaded, but do not constitute a captured build log.

### Fix under validation

1. Move the retrieval notice to a bounded, compact status line inside
   the memory controls, eliminating the oversized alert.
2. Add an ephemeral trusted source-attribution instruction to the
   desktop provider: distinguish user claims, earlier assistant claims
   and actually retrieved memories. No assumption that the prompt is
   a deterministic factuality checker.
3. Add tests for the prompt boundary and ordinary desktop behavior.

**Re-run the full Windows test suite, npm build, and desktop visual smoke.**
Do not mark this visual bug resolved or declare TB-02 Product Done
before those validations are reported.


## Subsequent evidence and presentation correction

The owner reported **88 passed in 3.87s**, plus Vite build SUCCESS
(557 modules, 5.20s). Vite displayed a non-fatal warning that the
JavaScript bundle exceeded the recommended 500 kB chunk threshold.
Screenshots in two new conversations showed: with Memory OFF, JARVIS
responded that the preference had not been provided in the conversation;
with Memory ON + Global, JARVIS acknowledged the retrieved teal
preference. The oversized Memory retrieval notice was resolved.

A third screenshot exposed a still-oversized *generic validation warning*
when the memory scope was missing. The response UI also displayed
\`**teal**\` literally, showing the lack of Markdown handling.

Fixes now published on the feature branch:
- Replace both generic \`v-alert\` panels with non-growing inline alerts.
- Render simple **bold** syntax with escaped Vue interpolations, not
  potentially unsafe HTML injection.
- Revalidate on Windows; screenshots are not yet available after this
  second visual patch.

The 88-pass result predates the new Knowledge and presentation commits.
Do not report the revised suite as passing without a new run.

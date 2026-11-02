# TB-02 — Step 01: Sofias Memory connection

Status: implemented in feature branch; real Windows validation pending.
Scope: secure connection and capability check only. Cognitive mutations and retrieval are NOT yet implemented.

Service target: https://pefil-sofias-memory.q8cqqr.easypanel.host
Documentation: /docs and /openapi-docs.json as supplied by the owner.
Owner-reported /health/live and /health/ready: passed.
Owner-reported /api/v1/info: service 0.7.0, API contract 1, Cognitive contract 1, five cognitive capabilities.

The connector only requests /health/live, /health/ready and /api/v1/info; HTTPS required, no redirects, 8-second timeout, limited JSON response.
API key uses a different Windows Credential Manager service entry from the OpenAI key. URL is non-secret and stored locally.

Windows validation commands:
.\.venv\Scripts\python.exe main.py --configure-memory-url "https://pefil-sofias-memory.q8cqqr.easypanel.host"
.\.venv\Scripts\python.exe main.py --configure-memory-key
.\.venv\Scripts\python.exe main.py --memory-check
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q

Expected: COMPATIBLE and missing_capabilities []. Do not disclose credentials.
Next: Cognitive Memory Create/Get/Recall/Supersede/Forget, Context Integration, Knowledge Retrieval with provenance, UI, end-to-end tests.
TB-02 remains IN PROGRESS; this increment is not Product Done.

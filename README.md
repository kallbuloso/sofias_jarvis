# JARVIS

Independent, local-first desktop assistant. **TB-01 is in progress**, not Product Done.

## Current implementation

The first two commits contain a Python bootstrap, SQLite conversation store,
OpenAI Responses streaming adapter, a conversation runtime, and a fail-closed
Windows Credential Manager adapter. The provider and secret adapters have
automated mock-based tests, **not** a live OpenAI or Windows 11 verification.

There is **no desktop UI or end-user chat yet**. See
`docs/product-manager/08-JARVIS-Technical-Backlog.md` for approved criteria.

Python 3.13 or 3.14 is required for the candidate runtime.

```powershell
py -3.13 main.py --diagnose
py -3.13 main.py --create-conversation "Teste"
py -3.13 main.py --list-conversations
```

For local development/tests:

```powershell
py -3.13 -m venv .venv
.venv\\Scripts\\python.exe -m pip install -e ".[dev]"
.venv\\Scripts\\python.exe -m pytest -q
```

By default data lives in `%LOCALAPPDATA%\\JARVIS\\jarvis.sqlite3` on Windows.
For isolated development, set `JARVIS_DATA_DIR` to another directory. Never
commit runtime databases or API keys.

## Next within TB-01

Wire OpenAI and credential vault into the application entrypoint; validate the
real API and Windows backend; implement the minimal PySide6 + Vue/Vuetify
desktop; verify streaming, restart, and shutdown on Windows 11.

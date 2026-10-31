# JARVIS

Independent, local-first desktop assistant. **TB-01 is in progress**, not Product Done.

## Current implementation

This first commit contains a Python bootstrap and a durable SQLite conversation
store. It does **not** yet provide a desktop interface, OpenAI integration,
streaming UI, or protected Windows secrets. See `docs/product-manager/` for the
approved architecture and TB-01 acceptance criteria.

Python 3.13 or 3.14 is required for the candidate runtime.

```powershell
py -3.13 main.py --diagnose
py -3.13 main.py --create-conversation "Teste"
py -3.13 main.py --list-conversations
```

For local tests (with `pytest` installed):

```powershell
py -3.13 -m pip install -e ".[dev]"
py -3.13 -m pytest -q
```

By default data lives in `%LOCALAPPDATA%\\JARVIS\\jarvis.sqlite3` on Windows.
For isolated development, set `JARVIS_DATA_DIR` to another directory. Never
commit runtime databases or API keys.

## Next within TB-01

OpenAI Responses streaming adapter, Windows Credential Manager integration,
minimal PySide6 + Vue/Vuetify desktop and human validation on Windows 11.

"""Sofias Memory credentials must never share OpenAI's credential entry."""

import sys
from types import SimpleNamespace

from jarvis.secrets import windows


class Vault:
    entries = None
    def __init__(self):
        self.entries = {}
    def get_password(self, service, account):
        return self.entries.get((service, account))
    def set_password(self, service, account, password):
        self.entries[(service, account)] = password
    def delete_password(self, service, account):
        del self.entries[(service, account)]


def test_memory_key_isolated_from_openai(monkeypatch):
    NativeVault = type("WinVaultKeyring", (Vault,), {"__module__": "keyring.backends.Windows"})
    vault = NativeVault()
    monkeypatch.setattr(windows.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_keyring=lambda: vault))
    store = windows.WindowsCredentialStore()
    store.set_openai_key("OPENAI_ONLY")
    store.set_memory_key("MEMORY_ONLY")
    assert store.get_openai_key() == "OPENAI_ONLY"
    assert store.get_memory_key() == "MEMORY_ONLY"
    store.delete_memory_key()
    assert store.get_memory_key() is None
    assert store.get_openai_key() == "OPENAI_ONLY"

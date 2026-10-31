from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from jarvis.secrets import windows


class FakeVault:
    def __init__(self):
        self.entries = {}

    def set_password(self, service, account, secret):
        self.entries[(service, account)] = secret

    def get_password(self, service, account):
        return self.entries.get((service, account))

    def delete_password(self, service, account):
        del self.entries[(service, account)]


def test_refuses_non_windows(monkeypatch):
    monkeypatch.setattr(windows.os, "name", "posix")
    with pytest.raises(windows.SecureStorageUnavailable):
        windows.WindowsCredentialStore().get_openai_key()


def test_refuses_unverified_backend(monkeypatch):
    monkeypatch.setattr(windows.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_keyring=lambda: FakeVault()))
    with pytest.raises(windows.SecureStorageUnavailable):
        windows.WindowsCredentialStore().set_openai_key("secret")


def test_accepts_only_native_windows_vault(monkeypatch):
    monkeypatch.setattr(windows.os, "name", "nt")
    NativeVault = type("WinVaultKeyring", (FakeVault,), {"__module__": "keyring.backends.Windows"})
    vault = NativeVault()
    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_keyring=lambda: vault))
    store = windows.WindowsCredentialStore()
    store.set_openai_key("secret")
    assert store.get_openai_key() == "secret"
    store.delete_openai_key()
    assert store.get_openai_key() is None

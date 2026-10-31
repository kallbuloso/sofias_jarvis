"""Windows Credential Manager, fail-closed when no native vault is available."""

from __future__ import annotations

import os


class SecureStorageUnavailable(RuntimeError):
    """No verified Windows vault backend is available."""


class WindowsCredentialStore:
    SERVICE = "sofias-jarvis/openai"
    ACCOUNT = "default"

    @staticmethod
    def _vault():
        if os.name != "nt":
            raise SecureStorageUnavailable("Windows Credential Manager requires Windows")
        try:
            import keyring
        except ImportError as exc:
            raise SecureStorageUnavailable("Install Python keyring on Windows") from exc
        backend = keyring.get_keyring()
        kind = type(backend)
        if not (kind.__module__ == "keyring.backends.Windows" and kind.__name__ == "WinVaultKeyring"):
            raise SecureStorageUnavailable("No verified Windows Credential Manager backend")
        return backend

    def get_openai_key(self) -> str | None:
        return self._vault().get_password(self.SERVICE, self.ACCOUNT)

    def set_openai_key(self, secret: str) -> None:
        if not secret or not secret.strip():
            raise ValueError("API key cannot be empty")
        self._vault().set_password(self.SERVICE, self.ACCOUNT, secret)

    def delete_openai_key(self) -> None:
        self._vault().delete_password(self.SERVICE, self.ACCOUNT)

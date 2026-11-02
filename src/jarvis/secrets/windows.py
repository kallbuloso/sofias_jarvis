"""Windows Credential Manager, fail-closed when no native vault is available."""

from __future__ import annotations

import os
from uuid import UUID


class SecureStorageUnavailable(RuntimeError):
    """No verified Windows vault backend is available."""


class WindowsCredentialStore:
    SERVICE = "sofias-jarvis/openai"
    MEMORY_SERVICE = "sofias-jarvis/sofias-memory"
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

    def get_memory_key(self) -> str | None:
        return self._vault().get_password(self.MEMORY_SERVICE, self.ACCOUNT)

    def set_memory_key(self, secret: str) -> None:
        if not secret or not secret.strip():
            raise ValueError("API key cannot be empty")
        self._vault().set_password(self.MEMORY_SERVICE, self.ACCOUNT, secret)

    def delete_memory_key(self) -> None:
        self._vault().delete_password(self.MEMORY_SERVICE, self.ACCOUNT)

    @staticmethod
    def connection_service(connection_id: str) -> str:
        connection_id = str(UUID(connection_id))
        return f"sofias-jarvis/connection/{connection_id}"

    def get_connection_secret(self, connection_id: str) -> str | None:
        return self._vault().get_password(
            self.connection_service(connection_id), self.ACCOUNT,
        )

    def set_connection_secret(self, connection_id: str, secret: str) -> None:
        if not isinstance(secret, str) or not secret.strip():
            raise ValueError("connection secret cannot be empty")
        self._vault().set_password(
            self.connection_service(connection_id), self.ACCOUNT, secret.strip(),
        )

    def delete_connection_secret(self, connection_id: str) -> None:
        vault = self._vault()
        service = self.connection_service(connection_id)
        try:
            vault.delete_password(service, self.ACCOUNT)
        except Exception as exc:
            # Deleting an already-missing credential is idempotent, but any
            # other vault failure must remain visible to the caller.
            if (type(exc).__name__ == "PasswordDeleteError"
                    and type(exc).__module__.startswith("keyring")):
                return
            raise

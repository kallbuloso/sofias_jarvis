"""Connection lifecycle coordinator. Secrets never leave this boundary."""
from __future__ import annotations

from jarvis.connections.github import GitHubConnectionAdapter, GitHubConnectionError
from jarvis.connections.registry import ProviderRegistry
from jarvis.connections.store import ConnectionStore
from jarvis.secrets.windows import WindowsCredentialStore


class ConnectionManager:
    def __init__(self, store: ConnectionStore, vault: WindowsCredentialStore):
        self.store = store
        self.vault = vault
        self.registry = ProviderRegistry()
        self._adapters = {"github": GitHubConnectionAdapter()}

    def providers(self) -> list[dict]:
        return self.registry.list()

    @staticmethod
    def _public(item: dict, *, configured: bool) -> dict:
        return {
            "id": item["id"],
            "provider_id": item["provider_id"],
            "display_identity": item["display_identity"],
            "external_account_ref": item["external_account_ref"],
            "configuration": item["configuration"],
            "enabled": item["enabled"],
            "configured": bool(configured),
            "observed_permissions": item["observed_permissions"],
            "availability": item["availability"],
            "last_error_code": item["last_error_code"],
            "last_verified_at": item["last_verified_at"],
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
        }

    def _configured(self, connection_id: str) -> bool:
        return bool(self.vault.get_connection_secret(connection_id))

    def list_connections(self) -> list[dict]:
        result = []
        for item in self.store.list():
            result.append(self._public(
                item, configured=self._configured(item["id"]),
            ))
        return result

    def create_github(self, token: str, *, label: str = "") -> dict:
        descriptor = self.registry.get("github")
        if descriptor is None:
            raise ValueError("unknown_provider")
        connection = self.store.create(
            "github",
            configuration={"label": label.strip()} if label.strip() else {},
        )
        connection_id = connection["id"]
        try:
            self.vault.set_connection_secret(connection_id, token)
        except Exception:
            self.store.delete(connection_id)
            raise
        return self.inspect(connection_id)

    def inspect(self, connection_id: str) -> dict:
        item = self.store.get(connection_id)
        if item is None:
            raise KeyError("unknown_connection")
        adapter = self._adapters.get(item["provider_id"])
        if adapter is None:
            raise ValueError("OPERATION_UNSUPPORTED")
        token = self.vault.get_connection_secret(connection_id)
        if not token:
            updated = self.store.record_inspection(
                connection_id,
                display_identity=item["display_identity"],
                external_account_ref=item["external_account_ref"],
                observed_permissions=item["observed_permissions"],
                availability="auth_required",
                error_code="AUTHENTICATION_REQUIRED",
            )
            return self._public(updated, configured=False)
        try:
            observed = adapter.inspect(token)
            updated = self.store.record_inspection(
                connection_id,
                display_identity=observed["display_identity"],
                external_account_ref=observed["external_account_ref"],
                observed_permissions=observed["observed_permissions"],
                availability=observed["availability"],
                error_code=None,
            )
        except GitHubConnectionError as exc:
            availability = {
                "AUTHENTICATION_REQUIRED": "auth_required",
                "AUTHENTICATION_FAILED": "auth_required",
                "EXTERNAL_PERMISSION_INSUFFICIENT": "permission_insufficient",
                "PROVIDER_UNAVAILABLE": "unavailable",
            }.get(exc.code, "error")
            updated = self.store.record_inspection(
                connection_id,
                display_identity=item["display_identity"],
                external_account_ref=item["external_account_ref"],
                observed_permissions=item["observed_permissions"],
                availability=availability,
                error_code=exc.code,
            )
        return self._public(updated, configured=True)

    def set_enabled(self, connection_id: str, enabled: bool) -> dict:
        item = self.store.get(connection_id)
        if item is None:
            raise KeyError("unknown_connection")
        if enabled:
            if not self._configured(connection_id):
                raise ValueError("AUTHENTICATION_REQUIRED")
            if item["external_account_ref"] is None:
                raise ValueError("CONNECTION_NOT_VERIFIED")
        updated = self.store.set_enabled(connection_id, bool(enabled))
        return self._public(updated, configured=self._configured(connection_id))

    def remove(self, connection_id: str) -> bool:
        if self.store.get(connection_id) is None:
            return False
        # Secret first: a DB failure leaves a safe unusable connection, while
        # deleting DB first could orphan a live credential.
        self.vault.delete_connection_secret(connection_id)
        return self.store.delete(connection_id)

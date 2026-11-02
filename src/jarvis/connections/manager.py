"""Connection lifecycle coordinator. Secrets never leave this boundary."""
from __future__ import annotations

from jarvis.connections.github import GitHubConnectionAdapter, GitHubConnectionError
from jarvis.connections.ai_verification import (
    AIConnectionVerificationError,
    AnthropicConnectionVerifier,
)
from jarvis.connections.registry import ProviderRegistry
from jarvis.connections.store import ConnectionStore
from jarvis.secrets.windows import WindowsCredentialStore


class ConnectionManager:
    def __init__(self, store: ConnectionStore, vault: WindowsCredentialStore):
        self.store = store
        self.vault = vault
        self.registry = ProviderRegistry()
        self._adapters = {"github": GitHubConnectionAdapter()}
        self._ai_verifiers = {"anthropic": AnthropicConnectionVerifier()}

    def providers(self) -> list[dict]:
        return self.registry.list()

    def _public(self, item: dict, *, configured: bool) -> dict:
        descriptor = self.registry.get(item["provider_id"])
        return {
            "id": item["id"],
            "provider_id": item["provider_id"],
            "provider_type": descriptor.provider_type if descriptor else "unknown",
            "provider_name": descriptor.display_name if descriptor else item["provider_id"],
            "status_check_support": bool(
                descriptor.status_check_support if descriptor else False
            ),
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

    def _secret_for(self, item: dict) -> str | None:
        ref = item.get("credential_ref")
        if ref == "legacy:openai:default":
            return self.vault.get_openai_key()
        return self.vault.get_connection_secret(item["id"])

    def _configured(self, connection_id: str) -> bool:
        item = self.store.get(connection_id)
        return bool(item and self._secret_for(item))

    def ensure_default_openai_connection(self) -> dict | None:
        """Represent the existing OpenAI vault entry as a normal AI Connection.

        The secret remains in the legacy Windows Credential Manager entry during
        TB-04; only a non-secret credential_ref is added to SQLite.
        """
        existing = self.store.list_by_provider("openai")
        if existing:
            enabled = [item for item in existing if item["enabled"]]
            chosen = enabled[0] if enabled else existing[0]
            return self._public(
                chosen, configured=bool(self._secret_for(chosen)),
            )

        legacy = self.vault.get_openai_key()
        if not legacy:
            return None

        item = self.store.create(
            "openai",
            configuration={
                "label": "OpenAI principal",
                "migration_source": "legacy_openai_credential",
            },
            credential_ref="legacy:openai:default",
        )
        self.store.set_enabled(item["id"], True)
        migrated = self.store.get(item["id"])
        return self._public(migrated, configured=True)

    def resolve_ai_connection(
        self, *, provider_id: str = "openai",
        connection_id: str | None = None,
    ) -> tuple[dict, str]:
        descriptor = self.registry.get(provider_id)
        if descriptor is None or descriptor.provider_type != "ai_inference":
            raise ValueError("AI_PROVIDER_UNKNOWN")

        if provider_id == "openai" and not self.store.list_by_provider("openai"):
            self.ensure_default_openai_connection()

        if connection_id is not None:
            item = self.store.get(connection_id)
            candidates = [item] if item is not None else []
        else:
            candidates = [
                item for item in self.store.list_by_provider(provider_id)
                if item["enabled"]
            ]

        candidates = [
            item for item in candidates
            if item is not None
            and item["provider_id"] == provider_id
            and item["enabled"]
        ]
        if not candidates:
            raise ValueError("AI_CONNECTION_NOT_AVAILABLE")
        if len(candidates) > 1 and connection_id is None:
            raise ValueError("AI_CONNECTION_AMBIGUOUS")

        item = candidates[0]
        secret = self._secret_for(item)
        if not secret:
            raise ValueError("AI_CREDENTIAL_NOT_CONFIGURED")
        return self._public(item, configured=True), secret

    def list_connections(self) -> list[dict]:
        result = []
        for item in self.store.list():
            result.append(self._public(
                item, configured=self._configured(item["id"]),
            ))
        return result

    def create_ai(
        self, provider_id: str, api_key: str, *, label: str = "",
    ) -> dict:
        descriptor = self.registry.get(provider_id)
        if descriptor is None or descriptor.provider_type != "ai_inference":
            raise ValueError("AI_PROVIDER_UNKNOWN")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("AUTHENTICATION_REQUIRED")
        if not isinstance(label, str) or len(label) > 120:
            raise ValueError("invalid_label")

        connection = self.store.create(
            provider_id,
            configuration={"label": label.strip()} if label.strip() else {},
        )
        connection_id = connection["id"]
        try:
            self.vault.set_connection_secret(connection_id, api_key)
        except Exception:
            self.store.delete(connection_id)
            raise
        item = self.store.get(connection_id)
        return self._public(item, configured=True)

    def verify_ai(self, connection_id: str) -> dict:
        item = self.store.get(connection_id)
        if item is None:
            raise KeyError("unknown_connection")

        descriptor = self.registry.get(item["provider_id"])
        if descriptor is None or descriptor.provider_type != "ai_inference":
            raise ValueError("AI_PROVIDER_UNKNOWN")
        if not descriptor.status_check_support:
            raise ValueError("OPERATION_UNSUPPORTED")

        secret = self._secret_for(item)
        if not secret:
            updated = self.store.record_inspection(
                connection_id,
                display_identity=item["display_identity"],
                external_account_ref=item["external_account_ref"],
                observed_permissions=item["observed_permissions"],
                availability="auth_required",
                error_code="AUTHENTICATION_REQUIRED",
            )
            result = self._public(updated, configured=False)
            result["available_models"] = []
            return result

        verifier = self._ai_verifiers.get(item["provider_id"])
        if verifier is None:
            raise ValueError("OPERATION_UNSUPPORTED")

        try:
            observed = verifier.inspect(secret)
            updated = self.store.record_inspection(
                connection_id,
                display_identity=item["display_identity"],
                external_account_ref=item["external_account_ref"],
                observed_permissions=item["observed_permissions"],
                availability=observed["availability"],
                error_code=None,
            )
            result = self._public(updated, configured=True)
            result["available_models"] = observed["available_models"]
            return result
        except AIConnectionVerificationError as exc:
            availability = {
                "AUTHENTICATION_REQUIRED": "auth_required",
                "AUTHENTICATION_FAILED": "auth_required",
                "EXTERNAL_PERMISSION_INSUFFICIENT": "permission_insufficient",
                "RATE_LIMITED": "unavailable",
                "PROVIDER_UNAVAILABLE": "unavailable",
                "NO_MODELS_AVAILABLE": "permission_insufficient",
            }.get(exc.code, "error")
            updated = self.store.record_inspection(
                connection_id,
                display_identity=item["display_identity"],
                external_account_ref=item["external_account_ref"],
                observed_permissions=item["observed_permissions"],
                availability=availability,
                error_code=exc.code,
            )
            result = self._public(updated, configured=True)
            result["available_models"] = []
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
            descriptor = self.registry.get(item["provider_id"])
            if descriptor is None:
                raise ValueError("unknown_provider")
            if (descriptor.provider_type == "external_integration"
                    and descriptor.status_check_support
                    and item["external_account_ref"] is None):
                raise ValueError("CONNECTION_NOT_VERIFIED")
        updated = self.store.set_enabled(connection_id, bool(enabled))
        return self._public(updated, configured=self._configured(connection_id))

    def remove(self, connection_id: str) -> bool:
        item = self.store.get(connection_id)
        if item is None:
            return False
        # Secret first for connection-owned credentials: a DB failure leaves
        # a safe unusable connection rather than an orphaned live credential.
        # Legacy OpenAI remains in its original vault entry during TB-04.
        if item.get("credential_ref") != "legacy:openai:default":
            self.vault.delete_connection_secret(connection_id)
        return self.store.delete(connection_id)

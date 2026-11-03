"""TB-04E2 provider catalog: catalog discovery must never imply authority."""
from types import SimpleNamespace

from jarvis.connections.catalog import LiteLLMProviderCatalog


def _sdk():
    return SimpleNamespace(
        provider_list=["openai", "anthropic", "gemini", "groq", "other_service"],
        get_provider_fields=lambda: [
            {
                "litellm_provider": "groq",
                "provider_display_name": "Groq",
                "credential_fields": [
                    {
                        "key": "api_key",
                        "label": "API Key",
                        "field_type": "password",
                        "required": True,
                        "default_value": "DO_NOT_EXPOSE",
                    },
                    {
                        "key": "api_base",
                        "field_type": "text",
                        "default_value": "DO_NOT_EXPOSE",
                    },
                ],
            }
        ],
        get_supported_openai_params=lambda **kwargs: ["stream", "response_format"],
    )


def test_catalog_discovers_sdk_providers_but_does_not_authorize_them():
    catalog = LiteLLMProviderCatalog(litellm_module=_sdk()).list()
    by_id = {item["provider_id"]: item for item in catalog}
    assert by_id["openai"]["connectable"]
    assert by_id["anthropic"]["connectable"]
    assert by_id["gemini"]["connectable"]
    assert by_id["groq"]["connection_status"] == "catalog_only"
    assert by_id["groq"]["connectable"] is False
    assert by_id["groq"]["connection_fields"] == []
    assert by_id["groq"]["metadata_fields"][0]["key"] == "api_key"
    assert "DO_NOT_EXPOSE" not in str(catalog)


def test_catalog_handles_unavailable_metadata_without_losing_managed_providers():
    fake = SimpleNamespace(
        provider_list=(),
        get_provider_fields=lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    items = LiteLLMProviderCatalog(litellm_module=fake).list()
    providers = {item["provider_id"]: item for item in items}
    assert providers["openai"]["connectable"]
    assert providers["gemini"]["connectable"]
    assert providers["anthropic"]["connectable"]


def test_model_capabilities_are_hints_not_account_access():
    catalog = LiteLLMProviderCatalog(litellm_module=_sdk())
    hints = catalog.model_hints("openai", "gpt-test")
    assert hints == {
        "status": "catalog_hint", "params": ["response_format", "stream"],
    }


def test_malformed_provider_metadata_does_not_create_connection_fields():
    fake = SimpleNamespace(
        provider_list=["/bad", "groq", "groq"],
        get_provider_fields=lambda: [
            {
                "provider": "/bad",
                "credential_fields": [{"key": "api_key", "default_value": "S"}],
            }
        ],
    )
    by_id = {
        item["provider_id"]: item
        for item in LiteLLMProviderCatalog(litellm_module=fake).list()
    }
    assert "/bad" not in by_id
    assert by_id["groq"]["connectable"] is False


class _FakeVault:
    def __init__(self):
        self.secrets = {}
        self.deleted = []

    def get_openai_key(self):
        return None

    def get_connection_secret(self, connection_id):
        return self.secrets.get(connection_id)

    def set_connection_secret(self, connection_id, secret):
        self.secrets[connection_id] = secret

    def delete_connection_secret(self, connection_id):
        self.deleted.append(connection_id)
        self.secrets.pop(connection_id, None)


def test_catalog_only_provider_cannot_create_connection(tmp_path):
    import pytest
    from jarvis.connections.manager import ConnectionManager
    from jarvis.connections.store import ConnectionStore

    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = _FakeVault()
    manager = ConnectionManager(store, vault)

    with pytest.raises(ValueError, match="AI_PROVIDER_UNKNOWN"):
        manager.create_ai("groq", "TOP-SECRET", label="not trusted")
    assert store.list() == []
    assert vault.secrets == {}
    assert b"TOP-SECRET" not in (tmp_path / "jarvis.sqlite3").read_bytes()


def test_generic_connection_create_keeps_secrets_out_of_store_and_public_ui(
    tmp_path,
):
    import json
    from jarvis.connections.manager import ConnectionManager
    from jarvis.connections.store import ConnectionStore

    path = tmp_path / "jarvis.sqlite3"
    vault = _FakeVault()
    manager = ConnectionManager(ConnectionStore(path), vault)

    first = manager.create_ai("gemini", "PRIVATE-GEMINI-ONE", label="Pessoal")
    second = manager.create_ai("gemini", "PRIVATE-GEMINI-TWO", label="Trabalho")

    assert first["id"] != second["id"]
    assert first["enabled"] is False and second["enabled"] is False
    assert first["configured"] and second["configured"]
    assert vault.secrets[first["id"]] == "PRIVATE-GEMINI-ONE"
    assert vault.secrets[second["id"]] == "PRIVATE-GEMINI-TWO"

    public = json.dumps(manager.list_connections())
    raw = path.read_bytes()
    for secret in ("PRIVATE-GEMINI-ONE", "PRIVATE-GEMINI-TWO"):
        assert secret not in public
        assert secret.encode() not in raw
    assert first["id"] in public and second["id"] in public

    assert manager.remove(first["id"]) is True
    assert vault.secrets == {second["id"]: "PRIVATE-GEMINI-TWO"}
    assert manager.store.get(first["id"]) is None
    assert manager.store.get(second["id"]) is not None


def test_generic_connection_vault_failure_rolls_back_local_identity(tmp_path):
    import pytest
    from jarvis.connections.manager import ConnectionManager
    from jarvis.connections.store import ConnectionStore

    class BrokenVault(_FakeVault):
        def set_connection_secret(self, connection_id, secret):
            raise RuntimeError("vault_unavailable")

    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    manager = ConnectionManager(store, BrokenVault())

    with pytest.raises(RuntimeError, match="vault_unavailable"):
        manager.create_ai("anthropic", "PRIVATE-ANTHROPIC")
    assert store.list() == []
    assert b"PRIVATE-ANTHROPIC" not in (tmp_path / "jarvis.sqlite3").read_bytes()


def test_catalog_metadata_does_not_override_trusted_connection_contract():
    fake = SimpleNamespace(
        provider_list=["gemini", "groq"],
        get_provider_fields=lambda: [
            {
                "litellm_provider": "gemini",
                "provider_display_name": "Spoofed Provider",
                "credential_fields": [
                    {"key": "oauth_token", "field_type": "password",
                     "required": True, "default_value": "SENSITIVE"},
                ],
            },
        ],
    )
    by_id = {
        item["provider_id"]: item
        for item in LiteLLMProviderCatalog(litellm_module=fake).list()
    }
    gemini = by_id["gemini"]
    assert gemini["connectable"] is True
    assert gemini["display_name"] == "Google Gemini"
    assert [field["key"] for field in gemini["connection_fields"]] == ["api_key"]
    assert "SENSITIVE" not in str(gemini)
    assert by_id["groq"]["connectable"] is False

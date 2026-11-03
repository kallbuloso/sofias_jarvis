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

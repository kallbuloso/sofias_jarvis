"""Local, read-only LiteLLM provider catalog for the JARVIS desktop.

Discovery is NOT registration, authorization, connectivity, or runtime parity.
Only explicit trusted JARVIS AI adapters can create Connections in TB-04E2.
No environment credentials or remote discovery endpoints are consulted.
"""
from __future__ import annotations

import re
from typing import Any

from jarvis.connections.registry import ProviderRegistry

_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


def _mapping(item: Any) -> dict:
    if isinstance(item, dict):
        return item
    dump = getattr(item, "model_dump", None)
    if callable(dump):
        try:
            value = dump()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}
    return {}


def _provider_id(value: Any) -> str | None:
    value = getattr(value, "value", value)
    if not isinstance(value, str) or not _PROVIDER_ID.fullmatch(value):
        return None
    return value


def _fields(value: Any) -> list[dict]:
    """Sanitize field metadata. Never propagate defaults or secret values."""
    if not isinstance(value, (tuple, list)):
        return []
    result = []
    seen = set()
    for candidate in value:
        item = _mapping(candidate)
        key = item.get("key")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", key):
            continue
        if key in seen:
            continue
        seen.add(key)
        field_type = item.get("field_type", "text")
        if field_type not in {"text", "password", "select", "textarea"}:
            field_type = "text"
        options = item.get("options")
        result.append({
            "key": key,
            "label": str(item.get("label") or key)[:120],
            "field_type": field_type,
            "required": item.get("required") is True,
            "options": [
                x[:120] for x in options[:50] if isinstance(x, str)
            ] if isinstance(options, list) else [],
        })
    return result


class LiteLLMProviderCatalog:
    """Merges SDK metadata with the explicit JARVIS connection contract."""

    def __init__(
        self, registry: ProviderRegistry | None = None, litellm_module=None,
    ) -> None:
        self.registry = registry or ProviderRegistry()
        self._sdk = litellm_module

    def list(self) -> list[dict]:
        sdk = self._sdk
        sdk_available = sdk is not None
        if sdk is None:
            try:
                import litellm as sdk
                sdk_available = True
            except ImportError:
                sdk_available = False
        candidates: dict[str, dict] = {}
        if sdk_available:
            provider_list = getattr(sdk, "provider_list", ())
            if not isinstance(provider_list, (list, tuple, set)):
                provider_list = ()
            for candidate in provider_list:
                provider_id = _provider_id(candidate)
                if provider_id:
                    candidates[provider_id] = {
                        "display_name": provider_id.replace("_", " ").title(),
                        "metadata_fields": [],
                    }

            get_fields = getattr(sdk, "get_provider_fields", None)
            if callable(get_fields):
                try:
                    metadata = get_fields()
                except (TypeError, ValueError, NotImplementedError, ImportError):
                    metadata = ()
                except Exception:
                    # An SDK metadata failure must not expose a secret, block
                    # existing registered Connections, or claim an available provider.
                    metadata = ()
                if isinstance(metadata, (tuple, list)):
                    for raw in metadata:
                        info = _mapping(raw)
                        provider_id = _provider_id(
                            info.get("litellm_provider") or info.get("provider")
                        )
                        if not provider_id:
                            continue
                        display = info.get("provider_display_name")
                        candidates[provider_id] = {
                            "display_name": (
                                display[:120] if isinstance(display, str)
                                and display.strip() else
                                provider_id.replace("_", " ").title()
                            ),
                            "metadata_fields": _fields(
                                info.get("credential_fields")
                            ),
                        }

        for item in self.registry.list():
            if item["provider_type"] != "ai_inference":
                continue
            provider_id = item["provider_id"]
            current = candidates.setdefault(provider_id, {
                "display_name": item["display_name"],
                "metadata_fields": [],
            })
            current["display_name"] = item["display_name"]

        result = []
        for provider_id in sorted(candidates):
            entry = candidates[provider_id]
            descriptor = self.registry.get(provider_id)
            managed = bool(
                descriptor is not None
                and descriptor.supports_ai_api_key_connection()
            )
            # JARVIS currently stores one per-Connection API key and does not
            # support arbitrary OAuth, uploads, endpoint URLs or SDK env auth.
            # Do not render unsupported fields as an actionable form.
            connection_fields = [{
                "key": "api_key",
                "label": "API Key",
                "field_type": "password",
                "required": True,
                "options": [],
            }] if managed else []
            result.append({
                "provider_id": provider_id,
                "display_name": entry["display_name"],
                "transport": "litellm",
                "catalog_source": "litellm_sdk" if sdk_available else "jarvis_registry",
                "connection_status": "managed" if managed else "catalog_only",
                "connectable": managed,
                "connection_fields": connection_fields,
                "metadata_fields": entry["metadata_fields"],
            })
        return result

    def model_hints(self, provider_id: str, model_id: str) -> dict:
        """Hints are never proof of account access or JSON-schema compatibility."""
        if not _provider_id(provider_id) or not isinstance(model_id, str):
            raise ValueError("INVALID_MODEL_REFERENCE")
        model_id = model_id.strip()
        if not model_id or len(model_id) > 200:
            raise ValueError("INVALID_MODEL_REFERENCE")
        sdk = self._sdk
        if sdk is None:
            import litellm as sdk
        get_params = getattr(sdk, "get_supported_openai_params", None)
        if not callable(get_params):
            return {"status": "unknown", "params": []}
        try:
            params = get_params(
                model=model_id, custom_llm_provider=provider_id,
            )
        except Exception:
            return {"status": "unknown", "params": []}
        if not isinstance(params, (list, tuple)):
            return {"status": "unknown", "params": []}
        return {
            "status": "catalog_hint",
            "params": sorted(set(
                value for value in params if isinstance(value, str)
            )),
        }

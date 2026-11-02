"""Explicit trusted integration provider registry for TB-04."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    provider_type: str
    contract_versions: tuple[str, ...]
    capabilities: tuple[str, ...]
    supported_auth_methods: tuple[str, ...]
    multi_connection_support: bool
    status_check_support: bool
    reconnect_support: bool
    provider_revoke_support: bool

    def as_dict(self) -> dict:
        data = asdict(self)
        for key in (
            "contract_versions", "capabilities", "supported_auth_methods",
        ):
            data[key] = list(data[key])
        return data


OPENAI = ProviderDescriptor(
    provider_id="openai",
    display_name="OpenAI",
    provider_type="ai_inference",
    contract_versions=("inference-v1", "connection-v1"),
    capabilities=(
        "inference.text.streaming",
        "inference.structured_json",
    ),
    supported_auth_methods=("api_key",),
    multi_connection_support=True,
    status_check_support=False,
    reconnect_support=True,
    provider_revoke_support=False,
)


ANTHROPIC = ProviderDescriptor(
    provider_id="anthropic",
    display_name="Anthropic",
    provider_type="ai_inference",
    contract_versions=("inference-v1", "connection-v1"),
    capabilities=(
        "inference.text.streaming",
        "inference.structured_json",
    ),
    supported_auth_methods=("api_key",),
    multi_connection_support=True,
    status_check_support=True,
    reconnect_support=True,
    provider_revoke_support=False,
)


GITHUB = ProviderDescriptor(
    provider_id="github",
    display_name="GitHub",
    provider_type="external_integration",
    contract_versions=("connection-v1", "capability-v1"),
    capabilities=(
        "github.identity.inspect",
        "github.repositories.read",
        "github.issues.read",
    ),
    supported_auth_methods=("fine_grained_pat",),
    multi_connection_support=True,
    status_check_support=True,
    reconnect_support=True,
    provider_revoke_support=False,
)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers = {
            OPENAI.provider_id: OPENAI,
            ANTHROPIC.provider_id: ANTHROPIC,
            GITHUB.provider_id: GITHUB,
        }

    def list(self) -> list[dict]:
        return [self._providers[key].as_dict() for key in sorted(self._providers)]

    def get(self, provider_id: str) -> ProviderDescriptor | None:
        return self._providers.get(provider_id)

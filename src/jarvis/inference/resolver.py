"""Deterministic inference profile resolution for TB-04D.

This layer resolves policy only. It never reads provider credentials, creates
SDK clients or performs inference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from jarvis.connections.registry import ProviderRegistry
from jarvis.connections.store import ConnectionStore
from jarvis.inference.profiles import InferenceProfileStore


_PRECEDENCE = ("task", "agent", "conversation", "project")
_REQUIREMENT_CAPABILITIES = {
    "streaming": "inference.text.streaming",
    "structured_output": "inference.structured_json",
}


class InferenceResolutionError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class InferenceResolutionContext:
    """Available policy scopes for one inference invocation."""

    conversation_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    requested_profile_id: str | None = None


@dataclass(frozen=True)
class ResolvedInferencePlan:
    """Non-secret deterministic output of policy resolution."""

    profile_id: str
    profile_slug: str
    selected_from: str
    selected_scope_id: str | None
    provider_id: str
    connection_id: str
    model: str
    requirements: dict
    constraints: dict
    fallback_enabled: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


class InferenceResolver:
    """Resolve the most-specific active binding into one validated plan."""

    def __init__(
        self,
        profile_store: InferenceProfileStore,
        connection_store: ConnectionStore,
        registry: ProviderRegistry | None = None,
    ):
        self.profiles = profile_store
        self.connections = connection_store
        self.registry = registry or ProviderRegistry()

    @classmethod
    def from_database(cls, path: Path | str) -> "InferenceResolver":
        return cls(
            InferenceProfileStore(path),
            ConnectionStore(path),
        )

    def _profile_for_context(
        self, context: InferenceResolutionContext,
    ) -> tuple[dict, str, str | None]:
        if context.requested_profile_id is not None:
            try:
                profile = self.profiles.get_profile(context.requested_profile_id)
            except ValueError as exc:
                raise InferenceResolutionError(
                    "INFERENCE_PROFILE_NOT_FOUND"
                ) from exc
            if profile is None:
                raise InferenceResolutionError("INFERENCE_PROFILE_NOT_FOUND")
            return profile, "request", None

        scope_values = {
            "task": context.task_id,
            "agent": context.agent_id,
            "conversation": context.conversation_id,
            "project": context.project_id,
        }
        for scope_type in _PRECEDENCE:
            scope_id = scope_values[scope_type]
            if scope_id is None:
                continue
            binding = self.profiles.get_binding(
                scope_type=scope_type,
                scope_id=scope_id,
            )
            if binding is None or not binding["enabled"]:
                continue
            profile = self.profiles.get_profile(binding["profile_id"])
            if profile is None:
                raise InferenceResolutionError("INFERENCE_PROFILE_NOT_FOUND")
            return profile, scope_type, scope_id

        binding = self.profiles.get_binding(scope_type="global")
        if binding is None or not binding["enabled"]:
            raise InferenceResolutionError("INFERENCE_PROFILE_NOT_CONFIGURED")
        profile = self.profiles.get_profile(binding["profile_id"])
        if profile is None:
            raise InferenceResolutionError("INFERENCE_PROFILE_NOT_FOUND")
        return profile, "global", "*"

    def _validate_plan(
        self,
        profile: dict,
        selected_from: str,
        selected_scope_id: str | None,
    ) -> ResolvedInferencePlan:
        if not profile["enabled"]:
            raise InferenceResolutionError("INFERENCE_PROFILE_DISABLED")

        configuration = profile.get("configuration")
        if not isinstance(configuration, dict):
            raise InferenceResolutionError("INFERENCE_PROFILE_INVALID")
        primary = configuration.get("primary")
        if not isinstance(primary, dict):
            raise InferenceResolutionError("INFERENCE_PROFILE_INVALID")

        connection_id = primary.get("connection_id")
        model = primary.get("model")
        if not isinstance(connection_id, str) or not isinstance(model, str):
            raise InferenceResolutionError("INFERENCE_PROFILE_INVALID")

        connection = self.connections.get(connection_id)
        if connection is None:
            raise InferenceResolutionError("AI_CONNECTION_NOT_AVAILABLE")
        if not connection["enabled"]:
            raise InferenceResolutionError("AI_CONNECTION_NOT_AVAILABLE")

        provider_id = connection["provider_id"]
        descriptor = self.registry.get(provider_id)
        if descriptor is None or descriptor.provider_type != "ai_inference":
            raise InferenceResolutionError("AI_PROVIDER_UNKNOWN")

        if descriptor.status_check_support:
            if connection["availability"] == "unknown":
                raise InferenceResolutionError("AI_CONNECTION_NOT_VERIFIED")
            if connection["availability"] in {
                "auth_required",
                "permission_insufficient",
                "unavailable",
                "error",
            }:
                raise InferenceResolutionError("AI_CONNECTION_NOT_AVAILABLE")
            observed_models = connection["configuration"].get(
                "observed_models", []
            )
            if observed_models and model not in observed_models:
                raise InferenceResolutionError("AI_MODEL_NOT_AVAILABLE")

        requirements = configuration.get("requirements", {})
        constraints = configuration.get("constraints", {})
        if not isinstance(requirements, dict) or not isinstance(constraints, dict):
            raise InferenceResolutionError("INFERENCE_PROFILE_INVALID")

        unknown_requirements = set(requirements) - set(
            _REQUIREMENT_CAPABILITIES
        )
        if unknown_requirements:
            raise InferenceResolutionError(
                "INFERENCE_PROFILE_REQUIREMENT_UNKNOWN"
            )
        for requirement, capability in _REQUIREMENT_CAPABILITIES.items():
            if requirement not in requirements:
                continue
            required = requirements[requirement]
            if not isinstance(required, bool):
                raise InferenceResolutionError(
                    "INFERENCE_PROFILE_INVALID"
                )
            if required and capability not in descriptor.capabilities:
                raise InferenceResolutionError(
                    "INFERENCE_PROFILE_CAPABILITY_UNAVAILABLE"
                )

        return ResolvedInferencePlan(
            profile_id=profile["id"],
            profile_slug=profile["slug"],
            selected_from=selected_from,
            selected_scope_id=selected_scope_id,
            provider_id=provider_id,
            connection_id=connection_id,
            model=model,
            requirements=dict(requirements),
            constraints=dict(constraints),
            fallback_enabled=False,
        )

    def resolve(
        self, context: InferenceResolutionContext,
    ) -> ResolvedInferencePlan:
        if not isinstance(context, InferenceResolutionContext):
            raise TypeError("context must be InferenceResolutionContext")
        profile, selected_from, scope_id = self._profile_for_context(context)
        return self._validate_plan(profile, selected_from, scope_id)

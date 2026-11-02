"""Bridge deterministic inference policy to executable provider access."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.inference.resolver import (
    InferenceResolutionContext,
    InferenceResolver,
    ResolvedInferencePlan,
)
from jarvis.secrets.windows import WindowsCredentialStore


@dataclass(frozen=True)
class ResolvedInferenceExecution:
    """Ephemeral execution material. Credential must never be persisted/logged."""

    plan: ResolvedInferencePlan
    connection: dict
    credential: str


def resolve_inference_execution(
    path: Path | str,
    vault: WindowsCredentialStore,
    context: InferenceResolutionContext,
) -> ResolvedInferenceExecution:
    resolver = InferenceResolver.from_database(path)
    plan = resolver.resolve(context)
    manager = ConnectionManager(ConnectionStore(path), vault)
    connection, credential = manager.resolve_ai_connection(
        provider_id=plan.provider_id,
        connection_id=plan.connection_id,
        model_id=plan.model,
    )
    return ResolvedInferenceExecution(
        plan=plan,
        connection=connection,
        credential=credential,
    )

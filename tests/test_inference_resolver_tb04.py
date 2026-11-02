from __future__ import annotations

import pytest

from jarvis.connections.store import ConnectionStore
from jarvis.inference.profiles import InferenceProfileStore
from jarvis.inference.resolver import (
    InferenceResolutionContext,
    InferenceResolutionError,
    InferenceResolver,
)


def _enabled_openai(path):
    connections = ConnectionStore(path)
    item = connections.create("openai")
    connections.set_enabled(item["id"], True)
    return connections, connections.get(item["id"])


def _profile(profiles, slug, connection_id, model="gpt-6-luna"):
    return profiles.create_profile(
        slug,
        slug.replace("-", " ").title(),
        connection_id=connection_id,
        model=model,
        requirements={
            "streaming": True,
            "structured_output": True,
        },
        constraints={"locality": "cloud_allowed"},
    )


def test_resolver_uses_global_profile_when_no_specific_binding_exists(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    general = _profile(profiles, "general", openai["id"])
    profiles.bind(general["id"], scope_type="global")

    plan = InferenceResolver(profiles, connections).resolve(
        InferenceResolutionContext(conversation_id="conversation-1")
    )

    assert plan.profile_id == general["id"]
    assert plan.profile_slug == "general"
    assert plan.selected_from == "global"
    assert plan.selected_scope_id == "*"
    assert plan.provider_id == "openai"
    assert plan.connection_id == openai["id"]
    assert plan.model == "gpt-6-luna"
    assert plan.fallback_enabled is False


def test_resolver_precedence_is_task_agent_conversation_project_global(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)

    global_profile = _profile(profiles, "global-profile", openai["id"], "global-model")
    project_profile = _profile(profiles, "project-profile", openai["id"], "project-model")
    conversation_profile = _profile(
        profiles, "conversation-profile", openai["id"], "conversation-model"
    )
    agent_profile = _profile(profiles, "agent-profile", openai["id"], "agent-model")
    task_profile = _profile(profiles, "task-profile", openai["id"], "task-model")

    profiles.bind(global_profile["id"], scope_type="global")
    profiles.bind(project_profile["id"], scope_type="project", scope_id="project-1")
    profiles.bind(
        conversation_profile["id"],
        scope_type="conversation",
        scope_id="conversation-1",
    )
    profiles.bind(agent_profile["id"], scope_type="agent", scope_id="agent-1")
    profiles.bind(task_profile["id"], scope_type="task", scope_id="task-1")

    resolver = InferenceResolver(profiles, connections)
    context = InferenceResolutionContext(
        project_id="project-1",
        conversation_id="conversation-1",
        agent_id="agent-1",
        task_id="task-1",
    )

    task = resolver.resolve(context)
    assert (task.selected_from, task.model) == ("task", "task-model")

    profiles.set_binding_enabled(
        scope_type="task", scope_id="task-1", enabled=False,
    )
    agent = resolver.resolve(context)
    assert (agent.selected_from, agent.model) == ("agent", "agent-model")

    profiles.set_binding_enabled(
        scope_type="agent", scope_id="agent-1", enabled=False,
    )
    conversation = resolver.resolve(context)
    assert (conversation.selected_from, conversation.model) == (
        "conversation", "conversation-model",
    )

    profiles.set_binding_enabled(
        scope_type="conversation", scope_id="conversation-1", enabled=False,
    )
    project = resolver.resolve(context)
    assert (project.selected_from, project.model) == (
        "project", "project-model",
    )

    profiles.set_binding_enabled(
        scope_type="project", scope_id="project-1", enabled=False,
    )
    global_plan = resolver.resolve(context)
    assert (global_plan.selected_from, global_plan.model) == (
        "global", "global-model",
    )


def test_explicit_profile_override_has_highest_precedence(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    general = _profile(profiles, "general", openai["id"], "global-model")
    override = _profile(profiles, "override", openai["id"], "override-model")
    profiles.bind(general["id"], scope_type="global")

    plan = InferenceResolver(profiles, connections).resolve(
        InferenceResolutionContext(
            conversation_id="conversation-1",
            requested_profile_id=override["id"],
        )
    )

    assert plan.profile_id == override["id"]
    assert plan.selected_from == "request"
    assert plan.selected_scope_id is None
    assert plan.model == "override-model"


def test_more_specific_enabled_binding_fails_closed_if_profile_disabled(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    general = _profile(profiles, "general", openai["id"])
    task = _profile(profiles, "task-profile", openai["id"], "task-model")
    profiles.bind(general["id"], scope_type="global")
    profiles.bind(task["id"], scope_type="task", scope_id="task-1")
    profiles.set_profile_enabled(task["id"], False)

    with pytest.raises(
        InferenceResolutionError, match="INFERENCE_PROFILE_DISABLED"
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext(task_id="task-1")
        )


def test_missing_global_profile_fails_closed(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, _ = _enabled_openai(path)
    profiles = InferenceProfileStore(path)

    with pytest.raises(
        InferenceResolutionError, match="INFERENCE_PROFILE_NOT_CONFIGURED"
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext()
        )


def test_resolver_refuses_disabled_connection_instead_of_falling_back(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    general = _profile(profiles, "general", openai["id"])
    profiles.bind(general["id"], scope_type="global")
    connections.set_enabled(openai["id"], False)

    with pytest.raises(
        InferenceResolutionError, match="AI_CONNECTION_NOT_AVAILABLE"
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext()
        )


def test_resolver_validates_verified_anthropic_model(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections = ConnectionStore(path)
    anthropic = connections.create(
        "anthropic",
        configuration={"observed_models": ["claude-sonnet-5-5"]},
    )
    connections.set_enabled(anthropic["id"], True)
    current = connections.get(anthropic["id"])
    connections.record_inspection(
        anthropic["id"],
        display_identity=current["display_identity"],
        external_account_ref=current["external_account_ref"],
        observed_permissions=current["observed_permissions"],
        availability="available",
        error_code=None,
    )

    profiles = InferenceProfileStore(path)
    bad = _profile(
        profiles, "bad-model", anthropic["id"], "claude-not-observed",
    )
    profiles.bind(bad["id"], scope_type="global")

    with pytest.raises(
        InferenceResolutionError, match="AI_MODEL_NOT_AVAILABLE"
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext()
        )


def test_resolved_plan_is_non_secret_and_preserves_selection_provenance(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    profile = _profile(profiles, "general", openai["id"])
    profiles.bind(
        profile["id"],
        scope_type="conversation",
        scope_id="conversation-1",
    )
    profiles.bind(profile["id"], scope_type="global")

    plan = InferenceResolver(profiles, connections).resolve(
        InferenceResolutionContext(conversation_id="conversation-1")
    ).as_dict()

    assert plan["selected_from"] == "conversation"
    assert plan["selected_scope_id"] == "conversation-1"
    assert "credential" not in str(plan).lower()
    assert "api_key" not in str(plan).lower()
    assert "secret" not in str(plan).lower()

def test_explicit_invalid_profile_id_is_normalized_to_domain_error(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, _ = _enabled_openai(path)
    profiles = InferenceProfileStore(path)

    with pytest.raises(
        InferenceResolutionError, match="INFERENCE_PROFILE_NOT_FOUND"
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext(requested_profile_id="not-a-uuid")
        )


def test_unknown_requirement_fails_closed(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    connections, openai = _enabled_openai(path)
    profiles = InferenceProfileStore(path)
    profile = profiles.create_profile(
        "future-capability",
        "Future capability",
        connection_id=openai["id"],
        model="gpt-6-luna",
        requirements={"tool_calling": True},
    )
    profiles.bind(profile["id"], scope_type="global")

    with pytest.raises(
        InferenceResolutionError,
        match="INFERENCE_PROFILE_REQUIREMENT_UNKNOWN",
    ):
        InferenceResolver(profiles, connections).resolve(
            InferenceResolutionContext()
        )


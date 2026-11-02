from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.vue"


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_toolbar_exposes_conversation_profile_and_resolved_provenance():
    value = source()
    assert 'label="Perfil da conversa"' in value
    assert "inferenceProfileItems" in value
    assert "onConversationProfileChanged" in value
    assert "resolvedInference.profile_slug" in value
    assert "resolvedInference.selected_from" in value
    assert "resolvedInference.provider_id" in value
    assert "resolvedInference.model" in value


def test_profile_ui_uses_bridge_policy_surface_not_provider_secrets():
    value = source()
    for method in (
        "listInferenceProfiles",
        "getConversationInference",
        "setConversationInferenceProfile",
        "createInferenceProfile",
    ):
        assert f"'{method}'" in value
    assert "profile.connectionId" not in value
    assert "profile.credential" not in value


def test_profile_creation_uses_current_connection_and_model():
    value = source()
    create = value.split("async function createInferenceProfile() {", 1)[1].split(
        "\nasync function refreshIntegrations()", 1
    )[0]
    assert "aiConnectionId.value" in create
    assert "model.value.trim()" in create
    assert "'createInferenceProfile'" in create
    assert "refreshInferenceProfiles()" in create


def test_open_conversation_refreshes_effective_inference_policy():
    value = source()
    open_conversation = value.split("async function openConversation(", 1)[1].split(
        "\nfunction requestDeleteConversation", 1
    )[0]
    assert "refreshConversationInference(id)" in open_conversation


def test_general_physical_selection_refreshes_profile_and_resolution_ui():
    value = source()
    selection = value.split("async function ensureAISelection() {", 1)[1].split(
        "\nasync function configureGitHub()", 1
    )[0]
    assert "selectAIConnection" in selection
    assert "refreshInferenceProfiles()" in selection
    assert "refreshConversationInference(selected.value)" in selection

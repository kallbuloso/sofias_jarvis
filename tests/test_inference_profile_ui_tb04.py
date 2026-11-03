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
        "updateInferenceProfilePrimary",
    ):
        assert f"'{method}'" in value
    assert "profile.connectionId" not in value
    assert "profile.credential" not in value


def test_profile_creation_has_its_own_provider_connection_and_model():
    value = source()
    create = value.split("async function createInferenceProfile() {", 1)[1].split(
        "\nasync function refreshIntegrations()", 1
    )[0]
    assert "profileProvider.value" in create
    assert "profileConnectionId.value" in create
    assert "profileModel.value.trim()" in create
    assert "aiConnectionId.value" not in create
    assert "'createInferenceProfile'" in create
    assert "refreshInferenceProfiles()" in create

    assert 'label="Provider do perfil"' in value
    assert 'label="Conexão do perfil"' in value
    assert 'label="Modelo do perfil"' in value


def test_open_conversation_refreshes_effective_inference_policy():
    value = source()
    open_conversation = value.split("async function openConversation(", 1)[1].split(
        "\nfunction requestDeleteConversation", 1
    )[0]
    assert "refreshConversationInference(id)" in open_conversation


def test_physical_selection_edits_effective_profile_not_always_general():
    value = source()
    selection = value.split("async function ensureAISelection() {", 1)[1].split(
        "\nasync function configureGitHub()", 1
    )[0]
    assert "effectiveInferenceProfileId()" in selection
    assert "updateInferenceProfilePrimary" in selection
    assert "selectAIConnection" not in selection
    assert "refreshInferenceProfiles()" in selection
    assert "refreshConversationInference(selected.value)" in selection


def test_resolved_profile_synchronizes_toolbar_provider_connection_and_model():
    value = source()
    apply = value.split("function applyResolvedInference(plan) {", 1)[1].split(
        "\nfunction effectiveInferenceProfileId()", 1
    )[0]
    assert "aiProvider.value = plan.provider_id" in apply
    assert "aiConnectionId.value = plan.connection_id" in apply
    assert "model.value = plan.model" in apply

    change = value.split(
        "async function onConversationProfileChanged(profileId) {", 1
    )[1].split("\nfunction onProfileProviderChanged", 1)[0]
    assert "applyResolvedInference(result.resolved" in change

def test_unchanged_resolved_profile_is_not_rewritten_on_every_send():
    value = source()
    selection = value.split("async function ensureAISelection() {", 1)[1].split(
        "\nasync function configureGitHub()", 1
    )[0]
    assert "const alreadyResolved = (" in selection
    assert "if (alreadyResolved)" in selection
    assert selection.index("if (alreadyResolved)") < selection.index(
        "'updateInferenceProfilePrimary'"
    )

def test_effective_profile_can_be_saved_without_sending_a_message():
    value = source()
    assert "async function saveEffectiveInferenceProfile()" in value
    assert '@click="saveEffectiveInferenceProfile"' in value
    assert ">\n                Salvar perfil\n" in value
    helper = value.split(
        "async function saveEffectiveInferenceProfile() {", 1
    )[1].split("\nasync function configureGitHub()", 1)[0]
    assert "ensureAISelection()" in helper
    assert "refreshConversationInference(selected.value)" in helper


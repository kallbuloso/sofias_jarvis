from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.vue"


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_conversation_toolbar_only_changes_profile_and_shows_provenance():
    value = source()
    toolbar = value.split('<div class="toolbar">', 1)[1].split(
        '<div v-if="!credentialConfigured"', 1
    )[0]

    assert 'label="Perfil da conversa"' in toolbar
    assert "inferenceProfileItems" in toolbar
    assert "onConversationProfileChanged" in toolbar
    assert "resolvedInference.profile_slug" in toolbar
    assert "resolvedInference.selected_from" in toolbar
    assert "resolvedInference.provider_id" in toolbar
    assert "resolvedInference.model" in toolbar

    # Physical profile administration belongs to Integrations, not Conversation.
    assert 'label="Provider"' not in toolbar
    assert 'label="Conexão"' not in toolbar
    assert 'label="Modelo de IA"' not in toolbar
    assert "Salvar perfil" not in toolbar


def test_profile_ui_uses_bridge_policy_surface_not_provider_secrets():
    value = source()
    for method in (
        "listInferenceProfiles",
        "getConversationInference",
        "setConversationInferenceProfile",
        "createInferenceProfile",
        "updateInferenceProfile",
        "deleteInferenceProfile",
    ):
        assert f"'{method}'" in value
    assert "profile.credential" not in value


def test_profile_creation_has_its_own_provider_connection_and_model():
    value = source()
    create = value.split("async function createInferenceProfile() {", 1)[1].split(
        "\nfunction openProfileEditor", 1
    )[0]
    assert "profileProvider.value" in create
    assert "profileConnectionId.value" in create
    assert "profileModel.value.trim()" in create
    assert "'createInferenceProfile'" in create
    assert "refreshInferenceProfiles()" in create

    assert 'label="Provider do perfil"' in value
    assert 'label="Conexão do perfil"' in value
    assert 'label="Modelo do perfil"' in value


def test_profile_cards_offer_edit_and_safe_delete():
    value = source()
    assert '@click="openProfileEditor(profile)"' in value
    assert '@click="requestDeleteProfile(profile)"' in value
    assert "profile.bindingCount" in value
    assert "profile.reserved" in value
    assert "profile.deletable" in value
    assert "Remova os vínculos antes de excluir" in value
    assert "O perfil global é obrigatório" in value


def test_profile_editor_can_change_metadata_provider_connection_and_model():
    value = source()
    assert 'title="Editar perfil de inferência"' in value
    assert 'v-model="profileEditName"' in value
    assert 'v-model="profileEditSlug"' in value
    assert ':disabled="profileEditTarget?.reserved"' in value
    assert 'v-model="profileEditProvider"' in value
    assert 'v-model="profileEditConnectionId"' in value
    assert 'v-model="profileEditModel"' in value

    save = value.split("async function saveProfileEdit() {", 1)[1].split(
        "\nfunction requestDeleteProfile", 1
    )[0]
    assert "'updateInferenceProfile'" in save
    assert "profileEditName.value.trim()" in save
    assert "profileEditSlug.value.trim()" in save
    assert "profileEditProvider.value" in save
    assert "profileEditConnectionId.value" in save
    assert "profileEditModel.value.trim()" in save


def test_profile_delete_has_confirmation_and_refresh():
    value = source()
    delete = value.split("async function confirmDeleteProfile() {", 1)[1].split(
        "\nasync function refreshIntegrations()", 1
    )[0]
    assert "'deleteInferenceProfile'" in delete
    assert "refreshInferenceProfiles()" in delete
    assert 'title="Excluir perfil de inferência?"' in value


def test_open_conversation_refreshes_effective_inference_policy():
    value = source()
    open_conversation = value.split("async function openConversation(", 1)[1].split(
        "\nfunction requestDeleteConversation", 1
    )[0]
    assert "refreshConversationInference(id)" in open_conversation


def test_changing_conversation_profile_applies_resolved_plan():
    value = source()
    change = value.split(
        "async function onConversationProfileChanged(profileId) {", 1
    )[1].split("\nfunction onProfileProviderChanged", 1)[0]
    assert "setConversationInferenceProfile" in change
    assert "applyResolvedInference(result.resolved" in change


def test_send_only_validates_resolved_profile_and_does_not_edit_it():
    value = source()
    selection = value.split("async function ensureAISelection() {", 1)[1].split(
        "\nasync function configureGitHub()", 1
    )[0]
    assert "resolvedInference.value?.profile_id" in selection
    assert "credentialConfigured.value" in selection
    assert "updateInferenceProfile" not in selection
    assert "selectAIConnection" not in selection

def test_integrations_exposes_ai_connections_through_generic_catalog_form():
    """E2: providers are metadata, not provider-specific Vue source code."""
    from jarvis.connections.catalog import LiteLLMProviderCatalog
    from jarvis.connections.registry import ProviderRegistry

    gemini = ProviderRegistry().get("gemini")
    assert gemini is not None
    assert gemini.display_name == "Google Gemini"
    assert gemini.provider_type == "ai_inference"
    assert gemini.litellm_prefix == "gemini"

    # SDK metadata absence must not disable a trusted, registered connection.
    items = LiteLLMProviderCatalog(
        litellm_module=type("OfflineSDK", (), {"provider_list": ()})()
    ).list()
    assert any(item["provider_id"] == "gemini" and item["connectable"]
               for item in items)

    value = source()
    assert "'loadAIProviderCatalog'" in value
    assert 'v-model="newAIProviderId"' in value
    assert ':items="allAIProviderItems"' in value
    assert 'v-for="field in selectedAIProviderCatalog?.connection_fields || []"' in value
    assert 'v-model="newAIFields[field.key]"' in value
    assert ':disabled="integrationBusy || !requiredAIFieldsPresent"' in value
    assert '@click="configureSelectedAIProvider"' in value

    configure = value.split(
        "async function configureSelectedAIProvider() {", 1
    )[1].split("\nfunction chooseModelForConnection", 1)[0]
    assert "'configureAIConnection', providerId, label, apiKey" in configure
    assert "newAIFields.value = {}" in configure

    # Adding a provider must not require a new hard-coded credential form.
    for legacy in (
        'v-model="geminiToken"',
        'v-model="anthropicToken"',
        'label="Gemini API key"',
        '@click="configureGemini"',
        '@click="configureAnthropic"',
    ):
        assert legacy not in value


def test_ai_connection_cards_expose_provider_neutral_litellm_diagnostics():
    value = source()
    assert "'diagnoseAIConnection'" in value
    assert "function runAIConnectionDiagnostic(connection)" in value
    assert 'label="Modelo de diagnóstico"' in value
    assert "Diagnóstico LiteLLM" in value
    assert "diagnosticStatus(aiDiagnostics[connection.id].plain)" in value
    assert "diagnosticStatus(aiDiagnostics[connection.id].structured)" in value
    assert "diagnosticStatus(aiDiagnostics[connection.id].streaming)" in value
    assert "litellm_version" in value
    assert "qualified_model" in value


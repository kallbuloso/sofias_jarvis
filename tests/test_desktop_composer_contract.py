"""Guard the desktop composer against silent inability to submit.

Static wiring contracts complement (do not replace) a human Qt WebView smoke.
They catch the exact no-selected-conversation regression after bulk deletion.
"""
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.vue"


def composer_source() -> str:
    return APP.read_text(encoding="utf-8")


def test_submit_can_create_first_conversation_after_history_was_cleared():
    source = composer_source()
    submit = source.split("async function sendMessage() {", 1)[1].split(
        "\nonMounted(", 1
    )[0]
    assert "!selected.value || !text" not in submit
    assert "if (!conversationId) {" in submit
    assert "await call('createConversation')" in submit
    assert "await call('sendConversationalMessage'," in submit
    assert submit.index("busy.value = true") < submit.index(
        "await call('createConversation')"
    )


def test_click_and_keyboard_share_send_with_no_selected_gate():
    source = composer_source()
    assert '@keydown.ctrl.enter.prevent="sendMessage"' in source
    assert '@click="sendMessage"' in source
    # A missing conversation is resolved by the submit handler, not a
    # permanent disabled state on the button.
    button = source.split('<v-btn color="primary" size="large" :loading="busy || memoryPreviewBusy"', 1)[1].split("</v-btn>", 1)[0]
    assert "!selected" not in button


def test_missing_model_cannot_fail_silently():
    source = composer_source()
    assert "Informe o modelo OpenAI antes de enviar a mensagem." in source
    assert "draft.value = text" in source
    assert "O JARVIS criará a conversa ao enviar." in source

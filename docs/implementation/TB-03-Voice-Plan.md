# JARVIS — TB-03 Voice Conversation Plan

**Slice:** TB-03 — Conversação por voz  
**Status:** APPROVED / IN PROGRESS  
**Branch:** `feat/tb-03-voice-conversation`  
**Baseline:** SPEC-07 + CONTRACT-05 + ARCH-04/05/06, já aprovados

## Objective

Permitir interação por voz no desktop Windows sem criar um pipeline conversacional paralelo. Voz deve produzir a mesma entrada canônica usada pelo chat textual e a resposta deve permanecer registrada na mesma Conversation.

## Slice decisions

Estas escolhas são de implementação do TB-03, não restrições permanentes do produto:

- **Push-to-talk** como mecanismo inicial de captura.
- **Windows 11** como alvo de validação.
- Captura/reprodução no **host Python/PySide6**, não no WebView.
- QtMultimedia, já distribuído com PySide6, como primeira opção de dispositivo/captura/reprodução.
- Voice Provider acessado por adapter; o Core não depende de API específica.
- Primeiro provider pode reutilizar a credencial OpenAI já protegida no Windows Credential Manager.
- Transcrição **final** entra no mesmo `sendConversationalMessage`; partial nunca é mensagem nem autoridade.
- Resposta textual continua canônica; TTS é saída derivada.
- Áudio bruto é efêmero e não persistido por padrão.
- Wake word, escuta contínua, full-duplex e barge-in automático ficam fora do Slice.

## Increment 1 — PTT + STT + canonical conversation

Fluxo:

`hold microphone → local capture → release → transcription final → sendConversationalMessage → normal JARVIS reply`

Acceptance:
- pressionar inicia captura;
- soltar encerra captura;
- transcrição final aparece como mensagem do usuário na Conversation selecionada;
- texto e voz compartilham exatamente o mesmo histórico;
- troca de Conversation durante captura não redireciona o turn;
- falha de microfone/STT não derruba chat;
- nenhuma partial dispara side effect;
- áudio capturado não é persistido.

## Increment 2 — TTS + playback control + spoken confirmation

Fluxo:

`assistant final text → synthesis → local playback`

Acceptance:
- resposta textual concluída pode ser falada;
- falha TTS preserva texto;
- usuário pode interromper somente o playback;
- playback interrompido não cancela tarefa/operação;
- áudio do próprio JARVIS não é reinterpretado como novo comando;
- `Confirmo.` vindo de uma transcrição final percorre o mesmo confirmation gate já validado no TB-02;
- autoridade não aumenta por ser voz.

## Out of Scope

- wake word;
- always-listening;
- automatic VAD as primary control;
- full-duplex;
- automatic barge-in;
- voice biometrics;
- voice-only authorization for critical operations;
- general execution-risk engine (TB-06);
- multiple mandatory voice providers;
- permanent raw-audio retention.

## TB-03 acceptance criteria

1. Text → voice continuation preserves context.
2. Voice → text continuation preserves context.
3. PTT lifecycle is visible and controllable.
4. Only final transcript becomes canonical input.
5. STT failure preserves text mode.
6. TTS failure preserves textual answer.
7. Conversation switch cannot steal an in-flight voice turn.
8. Stopping playback does not cancel unrelated work.
9. Spoken low-risk memory requests follow the same Core policy as typed requests.
10. Spoken Forget confirmation uses the same one-use conversational gate.
11. Critical operations do not become voice-authorized merely because STT produced `Confirmo`.
12. Shutdown during capture does not materialize a partial command.
13. No raw audio is durably stored by default.

## Validation strategy

Tests remain proportional to risk:
- unit tests for session identity/state and final-vs-partial handling;
- adapter tests with fake audio/provider;
- Qt boundary tests for capture lifecycle;
- one Windows microphone smoke per increment;
- one final full regression and Vite build at Product Done.

Do not repeat full-suite regression after every small edit.

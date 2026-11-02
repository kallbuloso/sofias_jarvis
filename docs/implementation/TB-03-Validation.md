# JARVIS — TB-03 Completion Evidence

**Slice:** TB-03 — Conversação por voz  
**Status:** PRODUCT DONE — validated by owner  
**Validation date:** 2026-11-02  
**Repository:** `kallbuloso/sofias_jarvis`  
**Implementation branch:** `feat/tb-03-voice-conversation`  
**Target branch:** `main`

## Delivered capability

TB-03 closes the first usable voice interaction slice of JARVIS:

- push-to-talk capture on Windows through PySide6 / QtMultimedia;
- microphone audio remains ephemeral and is not written to disk;
- completed PCM capture is wrapped as WAV in memory;
- OpenAI STT adapter produces one final transcript per turn;
- final transcript is routed through the same canonical `sendConversationalMessage` path used by typed text;
- the Conversation is bound when capture starts, preventing an in-flight turn from migrating silently to another Conversation;
- partial/incomplete capture never becomes a canonical command;
- voice failures degrade to text mode without taking down the desktop;
- local Windows TTS through PySide6 `QTextToSpeech`;
- assistant speech is generated from the already persisted assistant text, never from a second inference;
- pt-BR is preferred when available from the host speech engine;
- playback can be interrupted independently from conversation, memory or external work;
- spoken `Confirmo.` reaches the same one-use conversational confirmation gate already validated in TB-02;
- voice does not grant additional authority compared with typed text.

## Slice implementation decisions

These decisions belong to TB-03 and do not permanently constrain the product:

- push-to-talk is the initial capture mode;
- Windows 11 is the validation target;
- capture and playback live in the Python/PySide6 host, not in the WebView;
- QtMultimedia handles local microphone capture;
- OpenAI is the first STT provider through an adapter;
- local Windows/Qt TTS is the initial speech-output adapter;
- response text remains canonical;
- wake word, always-listening, full-duplex and automatic barge-in are deferred.

## Human validation

Owner validated on Windows:

1. push-to-talk captured a real microphone utterance;
2. the final transcript entered the normal Conversation feed;
3. JARVIS answered through the normal inference path;
4. the same assistant response was spoken by local TTS;
5. `Parar voz` stopped audible playback while preserving the full text and conversation;
6. natural spoken Create completed successfully;
7. natural spoken Forget produced the conversational confirmation question;
8. spoken `Confirmo.` was transcribed into the same Conversation and executed the existing one-use Forget gate;
9. JARVIS replied `Informação esquecida.` and spoke the result;
10. desktop remained open and usable after the complete voice/memory lifecycle.

## Automated validation

Focused voice regression reported by the owner:

```text
8 passed in 0.22s
```

After the complete human voice smoke, the owner also reported:

- full pytest regression: **PASS**;
- frontend production build: **PASS**.

Exact final full-suite count and build duration were not supplied in the acceptance message and are therefore not fabricated here.

## Safety and lifecycle evidence

- Only final STT output becomes canonical user input.
- A voice turn remains bound to its originating Conversation.
- Shutdown during active capture discards the incomplete turn.
- Spoken confirmation does not bypass the existing Core authorization gate.
- Stopping speech affects only playback.
- TTS failure preserves the textual answer.
- Raw microphone audio is not durably retained by default.
- Voice unavailability does not disable text interaction.

## Deferred / not claimed

- wake word;
- always-listening mode;
- automatic VAD as primary control;
- full-duplex audio;
- automatic barge-in;
- voice biometrics;
- voice-only authorization of critical operations;
- general execution-risk engine / critical side-effect approval (TB-06);
- mandatory multi-provider voice fallback;
- permanent raw-audio retention.

## Product Done decision

The planned TB-03 functional vertical was implemented and validated end-to-end:

`voice → STT → canonical Conversation → normal Core policy/memory → spoken confirmation → TTS`

Focused automated tests passed, the owner reported the final full regression and production frontend build passed, and the real Windows voice smokes passed.

**TB-03 = PRODUCT DONE.**

No claim is made that TB-04 or later slices are implemented by this completion record.

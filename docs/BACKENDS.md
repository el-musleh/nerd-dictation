# Backends

nerd-dictation supports three English transcription backends plus native
Arabic Whisper. Selection is centralized in `dictate-start` and validated
against `backends.py`.

| Engine | Key | How it runs | Best for |
|--------|-----|-------------|----------|
| VOSK | `VOSK` | Kaldi model via `nerd-dictation --input VADPIPE` (optionally Silero-VAD-gated) | Lowest latency, offline, large English model |
| WHISPER | `WHISPER` | faster-whisper (small.en) with VAD + artifact filtering | Accuracy, punctuation, subtitles |
| WLK | `WLK` | WhisperLiveKit real-time streaming server + `wlk-daemon.py` | Real-time streaming with best artifact resistance |

Arabic always uses faster-whisper (small) — it is the most accurate path for
Arabic and is independent of `ENGLISH_ENGINE`.

## WLK backend details

`dictate-start` launches `wlk-daemon.py`, which:
1. Starts the WhisperLiveKit server (`wlk serve --pcm-input`) on 127.0.0.1:8000.
2. Streams mic audio (parec → PCM s16le/16k) over a WebSocket.
3. Types only the *committed* (stable) text delta via xdotool.
4. Touches `~/.cache/nerd-dictation/wlk-ready` once the server is up.

`dictate-start` waits up to `WLK_READY_TIMEOUT` seconds for that file; if it
never appears (server failed to start), it **falls back to VOSK** automatically
so dictation never silently dies.

### Configurable WLK knobs
- `WLK_MODEL` — model size (tiny/base/small). Use tiny/base on CPU.
- `WLK_LANG` — fixed language, or `AUTO_LANG=on` for per-stream detection.
- `WLK_CHUNK` — seconds per audio chunk (0.1 lowest latency … 0.5).
- `WLK_POLICY` — `localagreement` (accurate) | `simulstreaming` (low latency).
- `AUDIO_DEVICE` — PulseAudio source (also applies to VOSK+VAD capture).

## VOSK improvements
- **VAD gate (B1/B2):** `VAD_GATE=on` pipes `parec | vad_gate.py | nerd-dictation --input VADPIPE`, dropping non-speech (breath/click) before VOSK sees it. Tune with `VAD_THRESHOLD` / `VAD_MIN_SILENCE_MS`.
- **Punctuation (D4):** `PUNCTUATE=on` restores caps/punctuation on exported transcripts (requires `pip install punctuators`).

## Export & output (E1/E2)
`WHISPER_EXPORT_PATH` + `OUTPUT_FORMAT` (srt|vtt|json|text) write each session's
transcript. `AUTOSAVE_PATH` appends every finalized utterance to a running log.
`E5`/`E4`: the last utterance is tracked in `LAST_UTTERANCE_FILE` for "Undo Last".

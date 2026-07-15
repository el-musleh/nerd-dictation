# Architecture

```
dictate-start  (launcher: layout → engine, config validation, fallbacks)
   │
   ├─ ENGLISH_ENGINE=VOSK
   │     └─ nerd-dictation begin --input VADPIPE   (optional: parec | vad_gate.py |)
   │
   ├─ ENGLISH_ENGINE=WHISPER  ─────────────┐
   │     └─ nerd-dictation begin --engine WHISPER
   │                                         │
   ├─ ENGLISH_ENGINE=WLK                      │  (Arabic always uses WHISPER)
   │     └─ wlk-daemon.py                     │
   │           ├─ wlk serve (WS server)       │
   │           └─ parec → WS → type delta     │
   │                                          ▼
   └─ whisper-daemon.py  (persistent faster-whisper server, ipc mode)
         ├─ VAD + artifact filtering (filters.py)
         ├─ export_subs.py (srt/vtt/json/text)
         ├─ punctuate.py (caps/punctuation, D4)
         └─ autosave / last-utterance tracking (E5/E4)

Shared modules:
  backends.py     — canonical engine registry + validation (C1)
  filters.py      — unified low-confidence / artifact filtering (B3)
  vad_gate.py     — Silero VAD capture filter (B1/B2)
  export_subs.py  — subtitle / structured output (E1/E2)
  punctuate.py    — punctuation restoration (D4)
  lib_common.sh   — bash helpers (resolve_whisper_model, C6)
  validate_config.sh — config sanity check (G8)

voice-controller/  — STT-only tray (start/stop/settings/undo-last)
```

## Control flow
1. `dictate-start` detects keyboard layout (xkblayout-state) → English vs Arabic.
2. English engine chosen by `ENGLISH_ENGINE` (validated against `backends.py`).
3. WLK path: if the server fails to come up within `WLK_READY_TIMEOUT`, fall
   back to VOSK automatically (A1).
4. Each backend writes transcripts via the shared export/filter/punctuate layer;
   autosave and last-utterance tracking feed the tray's "Undo Last".

## Config (single source of truth)
`~/.config/nerd-dictation/config.sh` — every knob is config-gated; defaults
preserve the original VOSK/Arabic/WHISPER behavior. Validate with
`validate_config.sh`.

# Voice Controller (STT)

System-tray (pystray) controller for **Speech-to-Text / Dictation** on this
machine — `nerd-dictation` (`/home/steve/dev/stt/nerd-dictation/`).

It is a **pure controller**: it polls the dictation state file and shells out
to the existing bash scripts by absolute path. It does NOT reimplement any
dictation logic. The architecture mirrors `tts-daemon.py`.

> TTS (speak-aloud-linux) is handled separately by its own tray
> (`tts-daemon.py`); this controller is STT-only.

## Run

```bash
python3 /home/steve/dev/voice-controller/voice-controller.py
```

Requires `pystray` + `Pillow` (already present). Auto-started on login
via `~/.config/autostart/voice-controller.desktop` (see below).

## Tray behavior

- **Icon**: a red microphone. Blue when idle, red "recording" glyph when
  dictation is active (`~/.dictate-state` alive).
- **Right-click menu**: Start Dictation (Super+H), Stop Dictation
  (Shift+Super+H), Quit.
- Single instance enforced via `/tmp/voice-controller.lock`.

## Keyboard shortcuts

Wired via Cinnamon custom keybindings (re-apply through System Settings →
Keyboard → Custom Shorcuts if they stop firing):

| Action           | Shortcut             | Script                                       |
|-----------------|---------------------|----------------------------------------------|
| Start dictation | `Super+H` (Win+H)   | `/home/steve/dev/stt/nerd-dictation/dictate-start`  |
| Stop dictation  | `Shift+Super+H`      | `/home/steve/dev/stt/nerd-dictation/dictate-stop`   |

> Note: for progressive typing to land in the right place, stop dictation
> (`Shift+Super+H` or tray Stop) while the target text field is focused.

## State file (read-only here)

- STT: `~/.dictate-state` (active iff file exists + PID alive)

## Replacing the standalone tts-daemon tray

The old `tts-daemon` auto-started its own tray. To avoid a double icon,
its autostart is disabled (the TTS bash scripts still do the real work):

```
~/.config/autostart/tts-daemon.desktop  ->  tts-daemon.desktop.disabled
```

To restore it: rename back and restart.

## Logs

`~/.local/share/voice-controller/controller.log` (rotated, 1 MB).

## Layout

```
voice-controller/
├── voice-controller.py   # the app (single file)
├── state.py              # pure STT state parser (+ tests)
├── icons.py              # PIL status icons (+ tests)
├── menu.py               # STT menu builder + shell-out (+ tests)
├── config.py             # (legacy) load/save last mode (+ tests)
├── switch.py             # (legacy) mode-switch helper (+ tests)
├── tests/                # pytest suite
└── README.md
```

> `config.py` / `switch.py` are retained for compatibility but unused
> now that the controller is STT-only.

## Reducing non-speech artifacts (breath / clicks / movement)

English dictation now defaults to **Whisper `small.en` with Silero VAD**
(`vad_filter=True` in `whisper-daemon.py`). VAD drops non-speech frames
before decoding, which removes most breath/click/movement text.

- Tune strictness in `whisper-daemon.py` `vad_parameters`:
  raise `threshold` (0.5 → stricter), increase `min_silence_duration_ms`,
  raise `min_speech_duration_ms` to ignore blips.
- A post-filter in `whisper-daemon.py` also drops sub-0.3s / single-character
  segments (residual artifacts).
- For lowest latency, set `ENGLISH_ENGINE=VOSK` in
  `~/.config/nerd-dictation/config.sh` (no VAD — more artifacts, faster).
  Edit it via the tray **STT Settings** button (opens `stt-settings.sh`).
- Hardware still matters: a cardioid/headset mic ~5cm from the mouth plus a
  pop filter removes breath energy at the source — software can't.

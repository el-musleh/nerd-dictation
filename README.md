# nerd-dictation (STT workspace)

Fork of [ideasman42/nerd-dictation](https://github.com/ideasman42/nerd-dictation)
with local customizations for English (VOSK + Whisper) and Arabic (Whisper)
dictation, plus the supporting tray controller and keyboard-layout tool,
consolidated into a single repo.

## Layout

```
nerd-dictation/
├── nerd-dictation          # the engine (upstream + custom dictate-start)
├── dictate-start           # layout-aware launcher (EN → VOSK/WhISPER, AR → Whisper)
├── dictate-stop
├── whisper-daemon.py       # persistent faster-whisper server (VAD-filtered)
├── stt-settings.sh         # yad settings dialog (edits ~/.config/nerd-dictation/config.sh)
├── voice-controller/       # pystray tray (STT-only): Start/Stop/Show Settings
├── xkblayout-state/        # source of the xkblayout-state keyboard-layout binary
│                            # (binary installed to /usr/local/bin/xkblayout-state)
├── docs/auto-switch-reference/  # archived docs from the old auto-switch project
│                            # (its EN/AR logic is now inline in dictate-start)
└── model/                  # VOSK model + grammar (gitignored)
```

## History / consolidation

This repo now also contains the `voice-controller` tray and the
`xkblayout-state` source (moved in from sibling folders) so the whole STT
workspace is one clone. The old `nerd-dictation-auto-switch-languages` project
was **deleted** — its language-switching logic was already absorbed into
`dictate-start`; its documentation is kept under
`docs/auto-switch-reference/` for reference.

`~/.config/nerd-dictation/config.sh` — engine switches:
`ENGLISH_ENGINE` (VOSK|WHISPER|WLK), `VOSK_TIMEOUT`, `WHISPER_DAEMON_MODE`
(warm-cache|ipc), `ENGLISH_WHISPER_MODEL`, `ARABIC_WHISPER_MODEL`,
`WLK_MODEL` (tiny/base/small — use tiny/base on CPU), `WLK_LANG`.

Edit it via the tray **Show Settings** button, or directly.

## English backends

- `VOSK` — fast, no VAD (more artifacts from breath/click).
- `WHISPER` — faster-whisper whole-clip + VAD (current default).
- `WLK` — **WhisperLiveKit** real-time streaming + Silero VAD. Best artifact
  resistance (incremental streaming, VAD-gated). On this CPU-only box use
  `WLK_MODEL=tiny` or `base`; `small` is slower. Set `ENGLISH_ENGINE=WLK`.
  Implemented in `wlk-daemon.py` (launches `wlk serve --pcm-input`, streams
  mic via parec, types committed text with xdotool).

## Evaluated-but-not-adopted (sibling folders under /home/steve/dev/stt/)

- `whisper_streaming/` — reference only. Original 2023 LocalAgreement research
  repo; its own README marks it outdated. WhisperLiveKit is its successor.
- `WhisperS2T-transcriber/` — batch/file GUI transcriber. Not real-time; keep
  as a standalone bulk-transcription tool, not wired into live dictation.

## Run

```bash
# dictation (or use the tray / Super+H)
./dictate-start
./dictate-stop

# tray controller (autostarted via ~/.config/autostart/voice-controller.desktop)
python3 voice-controller/voice-controller.py
```

## Notes

- `xkblayout-state` is vendored here (its upstream is
  `nonpop/xkblayout-state`). Rebuild + install the binary with the Makefile,
  then copy `xkblayout-state` to `/usr/local/bin/`.
- TTS (speak-aloud-linux) is a SEPARATE project at `/home/steve/dev/tts/` and
  is intentionally not part of this repo.

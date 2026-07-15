# nerd-dictation-auto-switch-languages

**Smart Voice Dictation on Linux: Automatically Detect Keyboard Layout**

A wrapper for [nerd-dictation](https://github.com/ideasman42/nerd-dictation) that automatically detects your current keyboard layout and uses the appropriate speech-to-text model. No need to manually switch dictation modes — it figures out whether you're typing in English, Arabic, or any other supported language.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-green.svg)
![Desktop](https://img.shields.io/badge/desktop-Cinnamon%20%7C%20GNOME%20%7C%20KDE-orange.svg)

---

## Features

- **🎯 Auto-Detection**: Automatically detects your keyboard layout and selects the correct speech model
- **⚡ Fast**: Press a single shortcut to start dictation in any language
- **🔔 Notifications**: Desktop notifications show which language is active
- **⏱️ Auto-Timeout**: Configurable silence timeout (default: 30 seconds)
- **🛠️ Extensible**: Easy to add support for new languages
- **📝 Detailed Logging**: Verbose mode for debugging

---

## Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Linux | Any | Operating system |
| Python | 3.6+ | nerd-dictation runtime |
| xkblayout-state | Latest | Keyboard layout detection |
| zenity | Latest | GUI dialogs |
| vosk | Latest | Speech recognition engine |
| nerd-dictation | Latest | Base dictation tool |

---

## Quick Start

### 1. Run the Setup Script

```bash
cd ~/Desktop/nerd-dictation-auto-switch-languages/scripts
chmod +x setup.sh
./setup.sh
```

### 2. Download Language Models

```bash
./install-models.sh
```

### 3. Set Up Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Super+H` | Start dictation (auto-detects language) |
| `Super+Shift+H` | Stop dictation |

---

## Usage

### Basic Commands

```bash
# Start dictation (detects language automatically)
./dictate-start

# Start with verbose logging
./dictate-start --verbose

# Stop dictation
./dictate-stop
```

### How It Works

1. Press `Super+H` to start dictation
2. The script detects your current keyboard layout
3. Launches the appropriate VOSK model (English, Arabic, etc.)
4. Speak — your words appear on screen
5. Press `Super+Shift+H` to stop

---

## Supported Languages

| Layout | Language | Engine (default) | Switchable to |
|--------|----------|------------------|---------------|
| `us`  | English  | VOSK large (0.22) + grammar | Whisper `small.en` via `ENGLISH_ENGINE=WHISPER` |
| `ara` | Arabic   | Whisper `small` | — |

Whisper serving path for any Whisper run is switchable:
`WHISPER_DAEMON_MODE=warm-cache` (default) or `=ipc` (Unix-socket daemon).

> **Note**: Only `us` and `ara` are wired into `dictate-start`. Other VOSK models
> (de, fr, es, ru, zh) are downloadable via `install-models.sh` but need a `case`
> branch added to `dictate-start` + a model dir to enable.

---

## Runtime Switches

All switches live in `~/.config/nerd-dictation/config.sh` (env vars override per-run):

| Variable | Values | Effect |
|----------|--------|--------|
| `ENGLISH_ENGINE` | `VOSK` (default) \| `WHISPER` | English uses VOSK-large+grammar, or Whisper `small.en` |
| `WHISPER_DAEMON_MODE` | `warm-cache` (default) \| `ipc` | Client loads model, or sends audio to whisper-daemon |
| `ENGLISH_WHISPER_MODEL` | `small.en` | Model for Whisper-English |
| `ARABIC_WHISPER_MODEL` | `small` | Model for Whisper-Arabic |
| `WHISPER_SOCKET` | path | Socket used in ipc mode |

Override per-run with env vars, e.g.:
`ENGLISH_ENGINE=WHISPER WHISPER_DAEMON_MODE=ipc ~/dev/stt/nerd-dictation/dictate-start`

The `whisper-daemon.service` (systemd --user) preloads `small` + `small.en` at
login so Arabic (and Whisper-English) start instantly. In `ipc` mode the daemon
does the transcription, so the client process never loads a model.

---

## Project Structure

```
nerd-dictation-auto-switch-languages/
├── README.md              # This file
├── docs/                 # Detailed documentation
│   ├── 01-installation.md
│   ├── 02-models.md
│   ├── 03-configuration.md
│   ├── 04-scripts.md
│   ├── 05-desktop-integration.md
│   ├── 06-advanced.md
│   └── 07-troubleshooting.md
├── scripts/              # Executable scripts
│   ├── setup.sh          # One-command installation
│   ├── install-models.sh  # Model download helper
│   ├── dictate-start     # Smart start script
│   └── dictate-stop      # Smart stop script
├── assets/               # Images and assets
└── blog/                # Blog post draft
```

---

## Documentation

- [Installation Guide](docs/01-installation.md) — Install all prerequisites
- [Downloading Models](docs/02-models.md) — Get speech models for your languages
- [Keyboard Configuration](docs/03-configuration.md) — Set up multi-language keyboards
- [Script Reference](docs/04-scripts.md) — Understand how the scripts work
- [Desktop Integration](docs/05-desktop-integration.md) — Configure shortcuts
- [Advanced Options](docs/06-advanced.md) — Verbose mode, custom timeouts
- [Troubleshooting](docs/07-troubleshooting.md) — Fix common issues

---

## Contributing

Contributions welcome! Please read the documentation and submit a pull request.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [nerd-dictation](https://github.com/ideasman42/nerd-dictation) by ideasman42
- [VOSK](https://alphacephei.com/vosk) by Alpha Cephei
- [xkblayout-state](https://github.com/nonpop/xkblayout-state) by nonpop

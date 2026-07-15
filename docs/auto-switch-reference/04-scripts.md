# Script Reference

Detailed documentation of the nerd-dictation-auto-switch-languages scripts.

---

## Overview

nerd-dictation-auto-switch-languages consists of two main scripts:

| Script | Purpose | Location |
|--------|---------|----------|
| `dictate-start` | Start dictation, auto-detect language | `~/nerd-dictation/` |
| `dictate-stop` | Stop dictation, type the result | `~/nerd-dictation/` |

---

## dictate-start

Main script that starts dictation and automatically detects the keyboard layout.

### Usage

```bash
./dictate-start [OPTIONS]

OPTIONS:
  --verbose, -v    Enable verbose logging to /tmp/dictate-start.log
  --help, -h       Show this help message
```

### Examples

```bash
# Basic usage (auto-detect language)
./dictate-start

# With verbose logging
./dictate-start --verbose

# Short form
./dictate-start -v
```

### How It Works

```
┌─────────────────────────────────────┐
│  1. Parse Arguments                 │
│     Check for --verbose flag         │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  2. Check Prerequisites              │
│     - nerd-dictation exists?         │
│     - Already running?               │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  3. Detect Keyboard Layout           │
│     xkblayout-state print "%s"       │
│     Returns: us, ara, de, etc.       │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  4. Map Layout to Model             │
│     us  → ~/.config/nerd-dictation/model/       │
│     ara → ~/.config/nerd-dictation/model-ar/    │
│     de  → (unsupported)             │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  5. Validate Model                  │
│     - Directory exists?              │
│     - Files present?                │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  6. Start nerd-dictation            │
│     With --timeout=30               │
│     Run in background               │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  7. Save State & Notify             │
│     Write to ~/.dictate-state        │
│     Show notify-send popup          │
└─────────────────────────────────────┘
```

### Source Code

```bash
#!/bin/bash
#
# Smart Dictation Starter
# Detects keyboard layout using xkblayout-state
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NERD_DICTATION="$SCRIPT_DIR/nerd-dictation"
STATE_FILE="$HOME/.dictate-state"
MODEL_BASE="$HOME/.config/nerd-dictation"
TIMEOUT=30

# Parse arguments
VERBOSE=false
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    VERBOSE=true
    exec > >(tee /tmp/dictate-start.log) 2>&1
fi

# ... (rest of script)
```

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEOUT` | 30 | Seconds of silence before auto-stop |
| `STATE_FILE` | `~/.dictate-state` | File tracking active dictation |
| `MODEL_BASE` | `~/.config/nerd-dictation` | Base model directory |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - dictation started |
| 1 | Error - check output for details |

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `nerd-dictation not found` | Script not installed | Reinstall nerd-dictation |
| `Dictation already running` | Previous dictation active | Run dictate-stop first |
| `Unsupported keyboard layout` | Layout not configured | Add layout to script |
| `Model not installed` | Model folder missing | Download model |

---

## dictate-stop

Script to stop active dictation and type the transcribed text.

### Usage

```bash
./dictate-stop
```

No arguments required.

### How It Works

```
┌─────────────────────────────────────┐
│  1. Check State File                │
│     ~/.dictate-state exists?        │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  2. Read Language Info              │
│     - PID of dictation process       │
│     - Language code (us, ara)        │
│     - Language name (English, etc.)  │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  3. Kill Process                    │
│     Kill the begin process           │
│     Also kill any orphan processes   │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  4. Run nerd-dictation end          │
│     Types the transcribed text       │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  5. Clean Up & Notify               │
│     Remove state file                │
│     Show notification               │
└─────────────────────────────────────┘
```

### Source Code

```bash
#!/bin/bash
#
# Smart Dictation Stopper
# Reads state file and stops the active dictation
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NERD_DICTATION="$SCRIPT_DIR/nerd-dictation"
STATE_FILE="$HOME/.dictate-state"

# Check if state file exists
if [ ! -f "$STATE_FILE" ]; then
    pkill -f "nerd-dictation" 2>/dev/null
    zenity --info --title="Dictation" --text="No active dictation found."
    exit 0
fi

# Read state
LANG=$(grep "^LANG:" "$STATE_FILE" 2>/dev/null | cut -d: -f2)
LANG_NAME=$(grep "^LANG_NAME:" "$STATE_FILE" 2>/dev/null | cut -d: -f2)

# ... (rest of script)
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - dictation stopped |
| 1 | Error or no active dictation |

---

## State File Format

The `~/.dictate-state` file tracks the active dictation session:

```
PID:12345
LANG:us
LANG_NAME:English
TIME:1700000000
```

| Field | Description |
|-------|-------------|
| `PID` | Process ID of the dictation process |
| `LANG` | Keyboard layout code (us, ara, de) |
| `LANG_NAME` | Human-readable language name |
| `TIME` | Unix timestamp when started |

---

## Log Files

### dictate-start Log

Location: `/tmp/dictate-start.log`

Created only when using `--verbose` flag.

```bash
# Enable verbose logging
./dictate-start --verbose

# View log
cat /tmp/dictate-start.log
```

### nerd-dictation Log

Location: `/tmp/nerd-dictation.log`

Created by nerd-dictation itself.

```bash
tail -f /tmp/nerd-dictation.log
```

---

## Customization

### Change Timeout

Edit `dictate-start` and change:

```bash
TIMEOUT=30  # Change to your preferred seconds
```

### Add New Language

Edit `dictate-start` and add:

```bash
    fr)
        MODEL_DIR="$MODEL_BASE/model-fr"
        LANG_NAME="French"
        LANG_CODE="fr"
        ;;
```

### Change Notification Style

Modify the `notify-send` command:

```bash
# Current (simple notification)
notify-send "Dictation Started" "$LANG_NAME dictation is now listening..."

# More detailed
notify-send "🎤 Dictation" "$LANG_NAME dictation is now listening..." \
    --icon=microphone \
    --app-name="nerd-dictation" \
    --urgency=normal
```

---

## Next Steps

- [Desktop Integration](05-desktop-integration.md) — Set up keyboard shortcuts
- [Advanced Options](06-advanced.md) — More customization options

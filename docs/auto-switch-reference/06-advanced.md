# Advanced Options

Customize nerd-dictation-auto-switch-languages for your specific needs.

---

## Verbose Mode

Enable detailed logging for debugging.

### Usage

```bash
./dictate-start --verbose
# or
./dictate-start -v
```

### What It Logs

```
[15:30:00] === Verbose mode enabled ===
[15:30:01] Detected layout: us
[15:30:01] Starting English dictation with model: /home/user/.config/nerd-dictation/model
[15:30:02] Started English dictation (PID: 12345)
```

### Log Location

- `/tmp/dictate-start.log` — dictate-start logs
- `/tmp/nerd-dictation.log` — nerd-dictation logs

### When to Use

- Debugging layout detection issues
- Checking which model is being used
- Investigating startup problems

---

## Custom Timeout

Change how long dictation waits for silence before auto-stopping.

### Default: 30 seconds

### Change Timeout

Edit `~/nerd-dictation/dictate-start`:

```bash
# Line 9
TIMEOUT=30  # Change to desired seconds
```

### Timeout Options

| Timeout | Use Case |
|---------|----------|
| 5 seconds | Quick notes |
| 30 seconds | Default, balanced |
| 60 seconds | Long dictation |
| 0 seconds | Manual stop only (no auto-timeout) |

### Set to Manual-Only

```bash
TIMEOUT=0
```

With `TIMEOUT=0`, dictation runs indefinitely until you press the stop shortcut.

---

## Custom Model Paths

Change where models are stored.

### Default Location

```
~/.config/nerd-dictation/
├── model/        # English
├── model-ar/     # Arabic
└── model-de/     # German
```

### Change Base Path

Edit `~/nerd-dictation/dictate-start`:

```bash
# Line 8
MODEL_BASE="$HOME/.config/nerd-dictation"
```

### Example: Different Location Per Language

```bash
case "$CURRENT_LAYOUT" in
    us)
        MODEL_DIR="$HOME/.models/english"
        ;;
    ara)
        MODEL_DIR="$HOME/.models/arabic"
        ;;
esac
```

---

## Custom Notifications

Modify notification appearance.

### Current Format

```bash
notify-send "Dictation Started" "$LANG_NAME dictation is now listening..."
```

### Enhanced Notifications

```bash
# With icon and urgency
notify-send "🎤 Dictation" "$LANG_NAME dictation is now listening..." \
    --icon=microphone \
    --urgency=normal \
    --app-name="nerd-dictation"

# With expire time (milliseconds)
notify-send "Dictation Started" "English is listening..." \
    --expire-time=3000
```

### Notification Icons

| Icon | Description |
|------|-------------|
| `microphone` | Recording indicator |
| `dialog-information` | Info message |
| `dialog-error` | Error message |
| `dialog-warning` | Warning message |

---

## Adding New Languages

### Step 1: Add Model

Download and install the model (see [Models Guide](02-models.md)):

```bash
mkdir -p ~/.config/nerd-dictation/model-fr
# Extract French model to model-fr/
```

### Step 2: Update Script

Edit `~/nerd-dictation/dictate-start`:

```bash
case "$CURRENT_LAYOUT" in
    us)
        MODEL_DIR="$MODEL_BASE/model"
        LANG_NAME="English"
        LANG_CODE="us"
        ;;
    ara)
        MODEL_DIR="$MODEL_BASE/model-ar"
        LANG_NAME="Arabic"
        LANG_CODE="ara"
        ;;
    # ADD NEW LANGUAGE HERE:
    fr)
        MODEL_DIR="$MODEL_BASE/model-fr"
        LANG_NAME="French"
        LANG_CODE="fr"
        ;;
    de)
        MODEL_DIR="$MODEL_BASE/model-de"
        LANG_NAME="German"
        LANG_CODE="de"
        ;;
    *)
        # Unsupported layout handling
        ;;
esac
```

### Step 3: Update dictate-stop

Edit `~/nerd-dictation/dictate-stop`:

```bash
case "$LANG" in
    us) LANG_NAME="English" ;;
    ara) LANG_NAME="Arabic" ;;
    fr) LANG_NAME="French" ;;    # ADD THIS
    de) LANG_NAME="German" ;;
    *) LANG_NAME="$LANG" ;;
esac
```

### Step 4: Test

```bash
setxkbmap fr  # Switch to French layout
./dictate-start  # Should start French dictation
```

---

## Error Handling Customization

### Change Error Popup Style

Edit the `zenity` commands in `dictate-start`:

```bash
# Current (simple error)
zenity --error --title="Error" --text="Message"

# With more details
zenity --error \
    --title="Dictation Error" \
    --text="Detailed error message here" \
    --width=400 \
    --height=200
```

### Disable Error Popups

To silently fail without popups:

```bash
# Comment out zenity lines
# zenity --error --title="Error" --text="..."

# Replace with log-only
echo "ERROR: Unsupported layout: $CURRENT_LAYOUT" >> /tmp/dictate-start.log
```

---

## Running in Different Modes

### Dry Run (Test Layout Detection)

```bash
# Just detect and print layout, don't start dictation
xkblayout-state print "%s"
```

### Test Specific Language

```bash
# Force English model regardless of layout
MODEL_DIR="$HOME/.config/nerd-dictation/model" ./dictate-start
```

### Debug Network Issues

If using network models:

```bash
curl -I https://alphacephei.com/vosk/models
```

---

## Integration with Other Tools

### With Clipboard Managers

Modify `dictate-stop` to copy text to clipboard:

```bash
# Get transcribed text first
TEXT=$("$NERD_DICTATION" end --output=STDOUT 2>/dev/null)
echo "$TEXT" | xclip -selection clipboard

# Then show notification
notify-send "Copied!" "Text copied to clipboard"
```

### With Text Expansion

Combine with text expanders like `espanso`:

1. Dictate text
2. Use trigger phrases
3. Expand to full commands

---

## Performance Tuning

### Fast Startup

Use small models for quicker loading:

| Model Type | Size | Load Time |
|------------|------|-----------|
| Small | ~50 MB | ~2 seconds |
| Large | ~2 GB | ~15 seconds |

### Memory Optimization

Run only one dictation session at a time. The script handles this automatically.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOME` | (system) | User home directory |
| `XAUTHORITY` | (system) | X11 display |
| `DISPLAY` | :0 | X11 display |

Normally不需要更改这些。

---

## Next Steps

- [Troubleshooting](07-troubleshooting.md) — Common issues and solutions
- [Main README](../README.md) — Project overview

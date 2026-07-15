# Keyboard Layout Configuration

Learn how to set up and manage multiple keyboard layouts for seamless language switching.

---

## Understanding Keyboard Layouts

nerd-dictation-auto-switch-languages uses keyboard layout codes to determine which language model to use:

| Code | Language | Example |
|------|----------|---------|
| `us` | English (US) | QWERTY |
| `ara` | Arabic | Arabic |
| `de` | German | QWERTZ |
| `fr` | French | AZERTY |

---

## Configuring Layouts in Cinnamon (Linux Mint)

### Step 1: Open Keyboard Settings

1. Click **Menu** → **System Settings**
2. Select **Keyboard**

### Step 2: Add Layouts

1. Go to **Layouts** tab
2. Click **Add** button
3. Search for your language (e.g., "Arabic", "German")
4. Select the variant (e.g., "Arabic (OLPC)", "German")
5. Click **Add**

### Step 3: Arrange Layouts

The order of layouts matters:
- First layout = index 0
- Second layout = index 1
- Third layout = index 2
- etc.

**Drag to reorder** if needed.

### Step 4: Configure Switching

1. Go to **Options**
2. Find **Key(s) to change layout**
3. Choose your preferred shortcut (e.g., `Super+Space`)

---

## Configuring Layouts in GNOME

### Step 1: Open Settings

1. Click **Activities** → **Settings**
2. Select **Keyboard**

### Step 2: Add Layouts

1. Go to **Input Sources**
2. Click **+** to add
3. Search and select your language
4. Repeat for all needed languages

### Step 3: Set Switching Shortcut

1. Click **Input Sources** settings (gear icon)
2. Find **Switch to next source** option
3. Set your preferred shortcut

---

## Configuring Layouts in KDE

### Step 1: Open System Settings

1. Click **K** menu → **System Settings**
2. Select **Input Devices** → **Keyboard**

### Step 2: Add Layouts

1. Go to **Layouts** tab
2. Click **Add**
3. Select language and variant
4. Click **OK**

### Step 3: Configure Switching

1. Check **Switching to next layout** checkbox
2. Set shortcut key combination

---

## Verifying Your Configuration

### Check Current Layout

```bash
xkblayout-state print "%s(%e)"
```

**Output examples:**
```
us(us)%        # English
ara(ara)%      # Arabic
de(de)%        # German
```

### List All Layouts

```bash
setxkbmap -query
```

**Output:**
```
rules:      evdev
model:      pc105
layout:     us,ara,de
variant:    ,,
options:    grp:super_space_toggle
```

---

## Layout Detection in nerd-dictation-auto-switch-languages

The script detects layouts using `xkblayout-state`:

```bash
# Get current layout code
CURRENT_LAYOUT=$(xkblayout-state print "%s")

# Result: "us", "ara", "de", etc.
```

---

## Adding Your Keyboard Layout Code

nerd-dictation-auto-switch-languages uses these layout codes by default:

| Your Layout | Code | Engine | Model Path |
|-------------|------|--------|-----------|
| English (US) | `us` | VOSK | `~/.config/nerd-dictation/model/` |
| Arabic | `ara` | Whisper | Auto-downloaded to `~/.cache/huggingface/hub/` |

### Adding a New VOSK Language

1. Download a VOSK model for your language (see [Language Models](02-models.md)).
2. Place it in `~/.config/nerd-dictation/model-XX/` (where `XX` is your language code).
3. Edit `~/nerd-dictation/dictate-start` and add a case:

```bash
case "$CURRENT_LAYOUT" in
    us)
        MODEL_DIR="$MODEL_BASE/model"
        LANG_NAME="English"
        LANG_CODE="us"
        ;;
    ara)
        LANG_NAME="Arabic"
        LANG_CODE="ara"
        USE_WHISPER=true
        WHISPER_MODEL="small"
        WHISPER_LANG="ar"
        WHISPER_TOOL="CLIPBOARD"
        ;;
    # ADD YOUR NEW LAYOUT HERE:
    fr)
        MODEL_DIR="$MODEL_BASE/model-fr"
        LANG_NAME="French"
        LANG_CODE="fr"
        ;;
    *)
        # Unsupported layout handling
        ;;
esac
```

> **Note**: Arabic uses Whisper (`USE_WHISPER=true`), not a VOSK model directory. Other languages use VOSK with a `MODEL_DIR` path.

---

## Testing Layout Detection

### Manual Test

```bash
# Switch to a layout (example: Arabic)
setxkbmap ara

# Verify detection
xkblayout-state print "%s"
# Should output: ara

# Run dictate-start
~/nerd-dictation/dictate-start
# Should start Arabic dictation
```

### Script Test

```bash
cd ~/nerd-dictation
./dictate-start --verbose
cat /tmp/dictate-start.log
```

---

## Troubleshooting Layout Issues

### Layout Not Detected

**Symptom**: `Could not detect keyboard layout` error

**Solution**:
1. Verify xkblayout-state is installed:
   ```bash
   xkblayout-state print "%s"
   ```

2. Reinstall if needed:
   ```bash
   git clone https://github.com/nonpop/xkblayout-state.git
   cd xkblayout-state
   make
   sudo make install
   ```

### Wrong Layout Detected

**Symptom**: Wrong language model starts

**Solution**:
1. Check actual keyboard layout:
   ```bash
   xkblayout-state print "%s(%e)"
   ```

2. Ensure you're using the layout you think you are

3. Check that the correct model exists:
   ```bash
   ls ~/.config/nerd-dictation/
   ```

---

## Next Steps

- [Set Up Desktop Integration](05-desktop-integration.md) — Configure keyboard shortcuts
- [Script Reference](04-scripts.md) — Understand how the scripts work

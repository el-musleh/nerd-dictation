# Desktop Integration

Set up keyboard shortcuts for seamless voice dictation on your Linux desktop.

---

## Overview

After installing nerd-dictation-auto-switch-languages, configure keyboard shortcuts for:

| Shortcut | Action | Script |
|----------|--------|--------|
| `Super+H` | Start dictation | `dictate-start` |
| `Super+Shift+H` | Stop dictation | `dictate-stop` |

> **Why Super+H?**
> - `Super` = Windows/Command key
> - `H` = "Hear" / "Hire" (voice)
> - Similar to Windows' built-in voice typing (`Win+H`)

---

## Cinnamon (Linux Mint)

### Step 1: Open Keyboard Settings

1. Click **Menu** → **System Settings**
2. Select **Keyboard**

### Step 2: Go to Shortcuts

1. Click **Shortcuts** tab
2. Select **Custom Shortcuts** in the left panel

### Step 3: Add Start Shortcut

1. Click the **+** button (Add Custom Shortcut)
2. Fill in:
   - **Name**: `Start Dictation`
   - **Command**: `/home/YOUR_USERNAME/nerd-dictation/dictate-start`
   - **Shortcut**: Click "Unassigned" then press `Super+H`
3. Click **Add**

### Step 4: Add Stop Shortcut

1. Click the **+** button again
2. Fill in:
   - **Name**: `Stop Dictation`
   - **Command**: `/home/YOUR_USERNAME/nerd-dictation/dictate-stop`
   - **Shortcut**: Click "Unassigned" then press `Super+Shift+H`
3. Click **Add**

### Step 5: Verify

1. Press `Super+H` — you should see a notification
2. Speak a few words
3. Press `Super+Shift+H` — text should appear

---

## GNOME

### Step 1: Open Settings

1. Click **Activities** → **Settings**
2. Select **Keyboard** (or **Keyboard Shortcuts**)

### Step 2: Add Custom Shortcuts

1. Scroll down and click **View and Customize Shortcuts**
2. Click **Custom Shortcuts** at the bottom
3. Click the **+** button

### Step 3: Configure Shortcuts

**For Start:**
- Name: `Start Dictation`
- Command: `/home/YOUR_USERNAME/nerd-dictation/dictate-start`
- Click **Set Shortcut** → Press `Super+H`

**For Stop:**
- Name: `Stop Dictation`
- Command: `/home/YOUR_USERNAME/nerd-dictation/dictate-stop`
- Click **Set Shortcut** → Press `Super+Shift+H`

---

## KDE Plasma

### Step 1: Open System Settings

1. Click **K** menu → **System Settings**
2. Search for "shortcuts" or select **Shortcuts**

### Step 2: Create Custom Shortcut

1. Go to **Custom Shortcuts** section
2. Click **Edit** → **New** → **Global Shortcut** → **Command/URL**

### Step 3: Configure

**Start Dictation:**
- Trigger: Press `Super+H`
- Action: `/home/YOUR_USERNAME/nerd-dictation/dictate-start`

**Stop Dictation:**
- Trigger: Press `Super+Shift+H`
- Action: `/home/YOUR_USERNAME/nerd-dictation/dictate-stop`

---

## XFCE

### Step 1: Open Keyboard Settings

1. Click **Menu** → **Settings** → **Keyboard**
2. Go to **Application Shortcuts** tab

### Step 2: Add Shortcuts

1. Click **Add**
2. Enter command: `/home/YOUR_USERNAME/nerd-dictation/dictate-start`
3. Press `Super+H` when prompted
4. Repeat for stop: `/home/YOUR_USERNAME/nerd-dictation/dictate-stop`

---

## i3 / Sway (Tiling Window Managers)

Add to your config file (`~/.config/i3/config` or `~/.config/sway/config`):

```bash
# Start Dictation
bindsym $mod+h exec /home/YOUR_USERNAME/nerd-dictation/dictate-start

# Stop Dictation
bindsym $mod+Shift+h exec /home/YOUR_USERNAME/nerd-dictation/dictate-stop
```

Reload config:
```bash
# i3
bindsym $mod+Shift+c reload

# Sway
swaymsg reload
```

---

## Troubleshooting

### Shortcut Not Working

**Check 1: Path is correct**
```bash
ls ~/nerd-dictation/dictate-start
```

**Check 2: Script is executable**
```bash
ls -la ~/nerd-dictation/dictate-start
# Should show: -rwxr-xr-x
```

**Check 3: Test manually**
```bash
~/nerd-dictation/dictate-start
```

### Shortcut Conflicts

If `Super+H` doesn't work, it might be taken:

1. Check **System Settings → Keyboard → Shortcuts**
2. Search for "H" to find conflicts
3. Free up the shortcut or choose another

**Alternative shortcuts:**
- `Super+D` (Dictation)
- `Ctrl+Alt+D` (Dictation)
- `F4`

### Notification Not Showing

Make sure `notify-osd` or `libnotify` is installed:

```bash
sudo apt install libnotify-bin
```

Test notifications:
```bash
notify-send "Test" "Hello from nerd-dictation-auto-switch-languages!"
```

---

## Advanced: Multiple Desktop Environments

If you use multiple desktop environments, create a wrapper script:

```bash
#!/bin/bash
# ~/bin/dictate-start-wrapper.sh

# Get the actual script location
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Run from nerd-dictation directory
cd "$PARENT_DIR"
./dictate-start "$@"
```

Then use this wrapper in shortcuts.

---

## Testing Your Setup

### Test Sequence

1. **Start English Dictation**
   ```bash
   # Set English layout
   setxkbmap us
   
   # Start dictation
   ~/nerd-dictation/dictate-start
   
   # You should see: "English dictation is now listening..."
   ```

2. **Start Arabic Dictation**
   ```bash
   # Set Arabic layout
   setxkbmap ara
   
   # Start dictation
   ~/nerd-dictation/dictate-start
   
   # You should see: "Arabic dictation is now listening..."
   ```

3. **Stop Dictation**
   ```bash
   ~/nerd-dictation/dictate-stop
   
   # You should see: "English/Arabic dictation complete."
   ```

4. **Test Keyboard Shortcuts**
   - Press `Super+H` → Dictation starts
   - Press `Super+Shift+H` → Dictation stops

---

## Next Steps

- [Advanced Options](06-advanced.md) — Verbose mode, custom timeouts
- [Troubleshooting](07-troubleshooting.md) — Fix common issues

# Installation Guide

Complete step-by-step installation for nerd-dictation-auto-switch-languages.

---

## Quickest Install

Run the automated setup script — it handles everything:

```bash
cd ~/Desktop/nerd-dictation-auto-switch-languages/scripts
chmod +x setup.sh
./setup.sh
```

Then skip to [Step 7: Set Up Keyboard Shortcuts](#step-7-set-up-keyboard-shortcuts).

---

## Manual Installation

### Prerequisites

- **Linux OS** (Ubuntu, Debian, Linux Mint, Fedora, Arch)
- **Python 3.8+**
- **X11 display server** (Wayland requires extra config — see [Troubleshooting](07-troubleshooting.md))
- **Internet connection** for first-time model downloads
- **Microphone**

---

### Step 1: Install System Dependencies

#### Ubuntu / Debian / Linux Mint

```bash
sudo apt update
sudo apt install -y \
    python3-pip \
    xdotool \
    xsel \
    x11-utils \
    zenity \
    libnotify-bin \
    pulseaudio-utils \
    wget \
    unzip \
    git
```

#### Fedora

```bash
sudo dnf install -y \
    python3-pip \
    xdotool \
    xsel \
    xprop \
    zenity \
    libnotify \
    pulseaudio-utils \
    wget \
    unzip \
    git
```

#### Arch / Manjaro

```bash
sudo pacman -S --noconfirm \
    python-pip \
    xdotool \
    xsel \
    xorg-xprop \
    zenity \
    libnotify \
    pulseaudio \
    wget \
    unzip \
    git
```

**Why each package:**
| Package | Purpose |
|---------|---------|
| `xdotool` | Simulate keystrokes (English output, backspace, paste shortcut) |
| `xsel` | Clipboard tool for Arabic RTL-safe paste |
| `x11-utils` / `xorg-xprop` | Provides `xprop` — detects if active window is a terminal |
| `pulseaudio-utils` | Provides `parec` for audio recording |
| `zenity` | GUI error dialogs |
| `libnotify-bin` | Desktop notifications |

---

### Step 2: Install xkblayout-state

Detects the active keyboard layout so the correct engine starts.

```bash
git clone https://github.com/nonpop/xkblayout-state.git
cd xkblayout-state
make
sudo make install
cd ..
```

Verify:
```bash
xkblayout-state print "%s"
# Should output: us (or your current layout)
```

---

### Step 3: Install Python Packages

```bash
pip3 install vosk numpy faster-whisper --break-system-packages
```

> If you get an "externally managed environment" error without `--break-system-packages`, use a virtual environment instead:
> ```bash
> python3 -m venv ~/dictation-venv
> ~/dictation-venv/bin/pip install vosk numpy faster-whisper
> ```

---

### Step 4: Install the Patched nerd-dictation

This repo ships a patched version of nerd-dictation that adds Whisper support, clipboard output, and terminal-aware paste. **Do not clone the upstream version** — it lacks these features.

```bash
mkdir -p ~/nerd-dictation
cp ~/Desktop/nerd-dictation-auto-switch-languages/scripts/nerd-dictation ~/nerd-dictation/
chmod +x ~/nerd-dictation/nerd-dictation
```

---

### Step 5: Install dictate-start and dictate-stop

```bash
cp ~/Desktop/nerd-dictation-auto-switch-languages/scripts/dictate-start ~/nerd-dictation/
cp ~/Desktop/nerd-dictation-auto-switch-languages/scripts/dictate-stop  ~/nerd-dictation/
chmod +x ~/nerd-dictation/dictate-start ~/nerd-dictation/dictate-stop
```

---

### Step 6: Download the English VOSK Model

Arabic uses Whisper (auto-downloaded on first use). English needs a VOSK model:

```bash
mkdir -p ~/.config/nerd-dictation
cd ~/.config/nerd-dictation
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
rm vosk-model-small-en-us-0.15.zip
```

---

### Step 7: Set Up Keyboard Shortcuts

See [Desktop Integration Guide](05-desktop-integration.md) for detailed instructions.

| Name | Command | Suggested Shortcut |
|------|---------|-------------------|
| Start Dictation | `~/nerd-dictation/dictate-start` | `Super+H` |
| Stop Dictation | `~/nerd-dictation/dictate-stop` | `Super+Shift+H` |

**Cinnamon / Linux Mint**: System Settings → Keyboard → Shortcuts → Custom Shortcuts  
**GNOME**: Settings → Keyboard → Custom Shortcuts  
**KDE**: System Settings → Shortcuts → Custom Shortcuts

---

## Verification

```bash
# Test English (switch to English layout first)
setxkbmap us
~/nerd-dictation/dictate-start
# Expected: "Dictation Started" notification

# Stop it
~/nerd-dictation/dictate-stop

# Test Arabic (switch to Arabic layout)
setxkbmap ara
~/nerd-dictation/dictate-start
# Expected: "Dictation Loading" then "Dictation Ready" notification — speak after the second one
```

---

## Next Steps

- [Language Models](02-models.md) — Model sizes, accuracy, GPU acceleration
- [Configuration](03-configuration.md) — Adding keyboard layouts
- [Desktop Integration](05-desktop-integration.md) — Keyboard shortcut setup
- [Troubleshooting](07-troubleshooting.md) — Common issues and fixes

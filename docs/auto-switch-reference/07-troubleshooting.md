# Troubleshooting

Solutions to common issues with nerd-dictation-auto-switch-languages.

---

## Quick Diagnostics

```bash
# Check keyboard layout detection
xkblayout-state print "%s"

# Verify scripts are executable
ls -la ~/nerd-dictation/dictate-*

# Check English model exists
ls ~/.config/nerd-dictation/model/

# View Arabic session log (transcription output, errors)
cat /tmp/nerd-dictation-ar.log

# View English session log (verbose mode)
cat /tmp/dictate-start.log
```

---

## Arabic Dictation Issues

### Issue: Arabic text not appearing after speaking

**Step 1 — Check the log:**
```bash
cat /tmp/nerd-dictation-ar.log
```

Look for one of these lines:

| Log line | Meaning |
|----------|---------|
| `Loading Whisper model...` | Model is loading — wait for "Dictation Ready" notification before speaking |
| `Transcribing X.X seconds of audio...` | Recording captured audio, transcription running |
| `Transcribed: 'some text'` | Transcription worked — if text didn't appear, it's an output issue |
| `Transcribed: ''` | No speech detected — microphone issue or spoke before "Ready" notification |
| `No text found in the audio` | Empty transcription, no text to output |

**Step 2 — If `Transcribed:` shows text but nothing appeared:**

The text was recognised but the paste step failed. Common causes:

- **Wrong paste shortcut for your app**: Arabic uses clipboard paste (`Ctrl+V` for GUI apps, `Ctrl+Shift+V` for terminals). The script auto-detects this, but if the detection fails, paste manually: the transcribed text is in your clipboard.
- **Focus changed during transcription**: Transcription takes 2–5 seconds. Make sure you're focused on the target window when you hear the "Dictation Stopped" notification.

**Step 3 — If `Transcribed:` shows `''` (empty):**

The microphone captured audio but Whisper found no speech. Check:
```bash
# Is your microphone working?
arecord -d 3 /tmp/test.wav && aplay /tmp/test.wav

# Did you speak AFTER "Dictation Ready" notification?
# "Dictation Loading" means the model is still loading — speech is not recorded yet.
```

---

### Issue: "Dictation Loading" notification but never "Dictation Ready"

**Cause**: The Whisper model is downloading for the first time (first Arabic dictation ever).

**What to do**: Wait. The `small` model (~244 MB) downloads once and is cached. Subsequent sessions load in 2–5 seconds.

**To pre-download manually:**
```bash
python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

---

### Issue: `faster-whisper` not installed

**Symptom**: Log shows `faster-whisper is required for the Whisper engine`

**Fix:**
```bash
pip3 install faster-whisper --break-system-packages
```

---

### Issue: `xsel` not installed (clipboard paste fails)

**Symptom**: Log shows `xsel failed to set clipboard`

**Fix:**
```bash
sudo apt install xsel        # Ubuntu/Debian
sudo dnf install xsel        # Fedora
sudo pacman -S xsel          # Arch
```

---

## English Dictation Issues

### Issue: "nerd-dictation not found"

**Symptom**: Error popup: "nerd-dictation not found at: /home/..."

**Fix:**
```bash
# Check the script exists
ls ~/nerd-dictation/nerd-dictation

# If missing, re-run setup
cd ~/Desktop/nerd-dictation-auto-switch-languages/scripts
./setup.sh
```

---

### Issue: "Model not installed" for English

**Symptom**: Error popup about English model missing

**Fix:**
```bash
mkdir -p ~/.config/nerd-dictation
cd ~/.config/nerd-dictation
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
```

---

### Issue: English dictation produces no text

**Symptom**: Dictation starts and stops but nothing is typed

**Check:**
```bash
# Test xdotool
xdotool type "hello"

# Check for Wayland (xdotool doesn't work on Wayland)
echo $XDG_SESSION_TYPE
# If "wayland": add --simulate-input-tool WTYPE to the VOSK start command in dictate-start
```

---

## Common Issues (Both Languages)

### Issue: "Could not detect keyboard layout"

**Fix:**
```bash
# Test detection
xkblayout-state print "%s"

# If missing, install
git clone https://github.com/nonpop/xkblayout-state.git
cd xkblayout-state && make && sudo make install
```

---

### Issue: "Dictation already running"

**Fix:**
```bash
pkill -f nerd-dictation
rm -f ~/.dictate-state
~/nerd-dictation/dictate-start
```

---

### Issue: Script works in terminal but not from keyboard shortcut

**Cause**: Environment variables (like `DISPLAY`) may not be set when the shortcut runs.

**Fix**: Set the shortcut command explicitly:
```
bash -c "DISPLAY=:0 ~/nerd-dictation/dictate-start"
```

---

## Debug Mode

Run `dictate-start` with `--verbose` to see detailed output:

```bash
~/nerd-dictation/dictate-start --verbose
# Logs written to /tmp/dictate-start.log

# In another terminal:
tail -f /tmp/dictate-start.log

# For Arabic:
tail -f /tmp/nerd-dictation-ar.log
```

---

## Collect Debug Info

```bash
cat << 'EOF' > ~/debug-dictation.sh
#!/bin/bash
echo "=== nerd-dictation-auto-switch-languages Debug Info ==="
echo ""
echo "OS:"; cat /etc/os-release | grep PRETTY_NAME
echo ""
echo "Python:"; python3 --version
echo ""
echo "Keyboard layout:"; xkblayout-state print "%s(%e)" 2>/dev/null || echo "xkblayout-state not found"
echo ""
echo "Tools:"
for t in xdotool xsel xkblayout-state parec notify-send zenity; do
    which $t 2>/dev/null && echo "  $t: OK" || echo "  $t: MISSING"
done
echo ""
echo "Python packages:"
python3 -c "import vosk; print('  vosk: OK')" 2>/dev/null || echo "  vosk: MISSING"
python3 -c "import faster_whisper; print('  faster-whisper: OK')" 2>/dev/null || echo "  faster-whisper: MISSING"
echo ""
echo "Models (VOSK):"
ls -la ~/.config/nerd-dictation/ 2>/dev/null || echo "  No models directory"
echo ""
echo "Scripts:"
ls -la ~/nerd-dictation/dictate-* 2>/dev/null || echo "  Scripts not found"
echo ""
echo "Arabic session log (last 20 lines):"
tail -20 /tmp/nerd-dictation-ar.log 2>/dev/null || echo "  No Arabic log yet"
EOF
chmod +x ~/debug-dictation.sh
~/debug-dictation.sh
```

---

## FAQ

### Q: Do I need a VOSK model for Arabic?

**A**: No. Arabic uses Whisper (`faster-whisper` Python package). No model directory is needed for Arabic — the model downloads automatically on first use.

### Q: Why does Arabic show two notifications?

**A**: The first ("Dictation Loading") fires when the script starts. The second ("Dictation Ready") fires from Python after the Whisper model is loaded and the microphone is open. **Only speak after the second notification.**

### Q: Can I paste Arabic into a terminal?

**A**: Yes. The script automatically detects terminal windows and uses `Ctrl+Shift+V` (terminal paste) instead of `Ctrl+V` (GUI paste).

### Q: Can I use a larger Whisper model for better accuracy?

**A**: Yes. Edit `WHISPER_MODEL="small"` in `scripts/dictate-start` and change it to `medium` or `large-v3`. Larger models are slower on CPU but significantly more accurate.

### Q: Can I use a GPU to speed up Arabic transcription?

**A**: Yes. Change `--whisper-device cpu` to `--whisper-device cuda` in `dictate-start`. Requires an NVIDIA GPU and CUDA drivers.

### Q: Can I use this offline?

**A**: Yes — once the Whisper model is downloaded and cached, everything runs offline. English VOSK is always offline.

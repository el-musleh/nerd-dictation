#!/bin/bash
# A1 integration test: WLK fails to start -> dictate-start falls back to VOSK.
# Headless: we don't need a mic; we only assert the fallback trigger.
set -u
cd /home/steve/dev/stt/nerd-dictation
export ENGLISH_ENGINE=WLK
export WLK_MODEL=__nonexistent_model__
export WLK_READY_TIMEOUT=3
export WLK_LANG=en
rm -f "$HOME/.cache/nerd-dictation/wlk-ready"
rm -f "$HOME/.dictate-state"

./dictate-start >/dev/null 2>&1
# Wait past the ready timeout (3s) plus slack.
sleep 6

echo "=== assertions ==="
FELL_BACK=$(grep -c "falling back to VOSK" /tmp/nerd-dictation-en.log 2>/dev/null || echo 0)
echo "fallback log lines: $FELL_BACK"
WLK_STILL_UP=$(pgrep -f "wlk-daemon.py" | grep -v $$ | wc -l)
echo "wlk-daemon still running: $WLK_STILL_UP"
READY_FILE=$( [ -f "$HOME/.cache/nerd-dictation/wlk-ready" ] && echo yes || echo no )
echo "wlk-ready file present: $READY_FILE"

if [ "$FELL_BACK" -ge 1 ] && [ "$WLK_STILL_UP" -eq 0 ] && [ "$READY_FILE" = "no" ]; then
    echo "A1_FALLBACK_OK"
else
    echo "A1_FALLBACK_FAIL"
fi

# Cleanup whatever got launched
./dictate-stop >/dev/null 2>&1
sleep 1
echo "=== done ==="

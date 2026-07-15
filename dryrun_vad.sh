#!/bin/bash
# Dry-run the VAD-gated VOSK pipeline using the 16k fixture as a fake microphone.
set -e
cd /home/steve/dev/stt/nerd-dictation
MODEL="$HOME/.config/nerd-dictation/vosk-model-en-us-0.22"
ffmpeg -loglevel error -i tests/fixtures/sample-en.wav -ar 16000 -ac 1 -f s16le - 2>/dev/null \
  | python3 vad_gate.py 2>/dev/null \
  | python3 nerd-dictation begin --vosk-model-dir="$MODEL" --input VADPIPE --timeout=5 --verbose 1 2>&1 | head -8
echo "DRYRUN_DONE"

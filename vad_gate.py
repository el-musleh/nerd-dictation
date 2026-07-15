#!/usr/bin/env python3
"""vad_gate.py — Silero VAD gate for nerd-dictation audio capture.

Reads raw PCM s16le mono at SAMPLE_RATE from stdin, runs Silero VAD, and
writes ONLY speech frames to stdout (with small padding around speech).
Silence (breath, clicks, ambient noise below threshold) is dropped, which
removes the non-speech artifacts that VOSK would otherwise transcribe.

Usage (piped capture):
    parec --format=s16le --rate=16000 --channels=1 | vad_gate.py | nerd-dictation ...

Designed to be a drop-in capture filter: same byte format on both ends.
"""
import argparse
import os
import sys

import numpy as np

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512          # 32 ms @ 16 kHz (Silero's expected window)
PAD_SAMPLES = 512            # keep a little audio around speech edges
THRESHOLD = float(os.environ.get("VAD_THRESHOLD", "0.5"))        # speech-prob threshold
MIN_SILENCE_MS = float(os.environ.get("VAD_MIN_SILENCE_MS", "300"))  # hangover before cut


def load_vad():
    """Load the Silero VAD model (cached after first fetch)."""
    import torch
    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        trust_repo=True,
    )
    model.eval()
    return model


def vad_filter_pcm(pcm: bytes, model, threshold: float = THRESHOLD,
                   pad_samples: int = PAD_SAMPLES,
                   min_silence_ms: float = MIN_SILENCE_MS) -> bytes:
    """Drop non-speech frames from raw s16le PCM; return filtered bytes.

    `min_silence_ms` adds a hangover: once speech ends, keep a little tail so
    word endings aren't clipped (mirrors WhisperLiveKit's min_silence_duration).
    """
    import torch
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    n = len(audio)
    hangover_frames = max(1, int((min_silence_ms / 1000.0) * SAMPLE_RATE / FRAME_SAMPLES))
    out = []
    speaking = False
    hangover = 0
    i = 0
    while i + FRAME_SAMPLES <= n:
        window = audio[i:i + FRAME_SAMPLES]
        with torch.no_grad():
            prob = float(model(torch.from_numpy(window), SAMPLE_RATE).item())
        is_speech = prob >= threshold
        if is_speech:
            start = max(i - pad_samples, 0)
            if start < i and not speaking:
                out.append(audio[start:i])
            out.append(window)
            speaking = True
            hangover = hangover_frames
        else:
            if speaking:
                # Keep a tail (hangover) after speech ends before cutting.
                out.append(window)
                hangover -= 1
                if hangover <= 0:
                    speaking = False
            # else: pure silence -> dropped
        i += FRAME_SAMPLES
    if i < n:
        out.append(audio[i:])
    if not out:
        return b""
    filtered = np.concatenate(out)
    return (filtered * 32768.0).clip(-32768, 32767).astype(np.int16).tobytes()


def main():
    ap = argparse.ArgumentParser(description="Silero VAD gate (stdin PCM -> stdout PCM)")
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--min-silence-ms", type=float, default=MIN_SILENCE_MS)
    ap.add_argument("--sample-rate", type=int, default=SAMPLE_RATE)
    args = ap.parse_args()

    model = load_vad()
    data = sys.stdin.buffer.read()
    out = vad_filter_pcm(data, model, threshold=args.threshold,
                         min_silence_ms=args.min_silence_ms)
    sys.stdout.buffer.write(out)


if __name__ == "__main__":
    main()

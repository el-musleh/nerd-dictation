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
import sys

import numpy as np

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512          # 32 ms @ 16 kHz (Silero's expected window)
PAD_SAMPLES = 512            # keep a little audio around speech edges
THRESHOLD = 0.5             # Silero speech probability threshold


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
                   pad_samples: int = PAD_SAMPLES) -> bytes:
    """Drop non-speech frames from raw s16le PCM; return filtered bytes."""
    import torch
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    n = len(audio)
    out = []
    speaking = False
    pad_left = 0
    i = 0
    while i + FRAME_SAMPLES <= n:
        window = audio[i:i + FRAME_SAMPLES]
        # Silero expects a 1D float32 tensor; get speech probability.
        with torch.no_grad():
            prob = float(model(torch.from_numpy(window), SAMPLE_RATE).item())
        is_speech = prob >= threshold
        if is_speech:
            # Include padding before this frame (already-emitted or not).
            start = max(i - pad_samples, 0)
            if start < i and not speaking:
                out.append(audio[start:i])
            out.append(window)
            speaking = True
        else:
            if speaking:
                # Keep a little tail after speech ends.
                out.append(audio[i:i + pad_samples])
                speaking = False
        i += FRAME_SAMPLES
    # Flush remainder
    if i < n:
        out.append(audio[i:])
    if not out:
        return b""
    filtered = np.concatenate(out)
    return (filtered * 32768.0).clip(-32768, 32767).astype(np.int16).tobytes()


def main():
    ap = argparse.ArgumentParser(description="Silero VAD gate (stdin PCM -> stdout PCM)")
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--sample-rate", type=int, default=SAMPLE_RATE)
    args = ap.parse_args()

    model = load_vad()
    data = sys.stdin.buffer.read()
    out = vad_filter_pcm(data, model, threshold=args.threshold)
    sys.stdout.buffer.write(out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""bench.py — CPU latency benchmark for the WHISPER backend.

Measures model load time and full-clip transcription latency on a fixed
fixture, for a given model + compute_type. Helps pick the right model for
this machine (CPU-only) before promoting a slow default.

Usage:
    bench.py                         # default: small.en / int8
    bench.py --model base.en --compute int8
    bench.py --model tiny.en --repeat 3
"""
import argparse
import os
import sys
import time

import numpy as np
import soundfile as sf

REPO = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "sample-en.wav")


def load_and_transcribe(model: str, compute_type: str, audio_int16: bytes):
    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    m = WhisperModel(model, device="cpu", compute_type=compute_type)
    t_load = time.perf_counter() - t0
    t1 = time.perf_counter()
    segments, _ = m.transcribe(
        np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0,
        language="en", vad_filter=True, condition_on_previous_text=False,
    )
    text = " ".join(s.text for s in segments).strip()
    t_transcribe = time.perf_counter() - t1
    return text, t_load, t_transcribe


def main():
    ap = argparse.ArgumentParser(description="WHISPER CPU latency benchmark")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--compute", default="int8")
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()

    audio, _ = sf.read(FIXTURE)
    audio_int16 = (np.clip(audio, -1, 1) * 32768).astype(np.int16).tobytes()

    loads, trans = [], []
    for i in range(max(1, args.repeat)):
        text, t_load, t_trans = load_and_transcribe(args.model, args.compute, audio_int16)
        loads.append(t_load)
        trans.append(t_trans)
        print(f"[{i+1}] load={t_load:.2f}s transcribe={t_trans:.2f}s  text={text[:60]!r}")

    print(f"\nModel={args.model} compute={args.compute} (CPU, n={len(loads)})")
    print(f"  load:        avg {sum(loads)/len(loads):.2f}s")
    print(f"  transcribe:   avg {sum(trans)/len(trans):.2f}s (clip ~{len(audio)/len(audio)*0:.0f}s)")


if __name__ == "__main__":
    main()

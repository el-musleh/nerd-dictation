import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pcm_bytes(samples_float32):
    return (np.asarray(samples_float32) * 32768.0).clip(-32768, 32767).astype(np.int16).tobytes()


def _load_gate():
    sys.path.insert(0, REPO)
    import vad_gate
    model = vad_gate.load_vad()
    return vad_gate, model


def test_vad_drops_silence():
    vad_gate, model = _load_gate()
    sr = vad_gate.SAMPLE_RATE
    # 2 seconds of pure silence (zeros)
    silence = np.zeros(sr * 2, dtype=np.float32)
    out = vad_gate.vad_filter_pcm(_pcm_bytes(silence), model)
    # Almost all silence should be dropped.
    assert len(out) < len(_pcm_bytes(silence)) * 0.2, "silence not dropped"


def test_vad_keeps_speech():
    vad_gate, model = _load_gate()
    # Real synthesized speech fixture, resampled to 16 kHz mono to match the
    # gate's expected rate (parec feeds 16 kHz in production).
    import subprocess, tempfile, wave
    wav_path = os.path.join(REPO, "tests", "fixtures", "sample-en.wav")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp16 = tf.name
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-ar", "16000", "-ac", "1",
         "-f", "s16le", tmp16],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    with open(tmp16, "rb") as f:
        raw = f.read()
    out = vad_gate.vad_filter_pcm(raw, model)
    os.unlink(tmp16)
    retained = len(out) / max(1, len(raw))
    assert retained > 0.5, f"speech under-retained: {retained:.2%}"


def test_vad_roundtrip_format():
    vad_gate, model = _load_gate()
    sr = vad_gate.SAMPLE_RATE
    sig = (0.5 * np.sin(2 * np.pi * 300 * np.arange(sr) / sr)).astype(np.float32)
    out = vad_gate.vad_filter_pcm(_pcm_bytes(sig), model)
    assert len(out) % 2 == 0
    assert len(out) > 0


def test_vad_threshold_env_override(monkeypatch):
    vad_gate, model = _load_gate()
    # Very high threshold -> almost everything dropped as non-speech.
    monkeypatch.setenv("VAD_THRESHOLD", "0.99")
    reload_module = _reload(vad_gate)
    sr = reload_module.SAMPLE_RATE
    sig = (0.5 * np.sin(2 * np.pi * 300 * np.arange(sr) / sr)).astype(np.float32)
    out = reload_module.vad_filter_pcm(_pcm_bytes(sig), model,
                                       threshold=0.99)
    # High threshold on a pure tone -> little retained.
    assert len(out) < len(_pcm_bytes(sig)) * 0.5


def _reload(module):
    import importlib
    return importlib.reload(module)


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
    silence = np.zeros(sr * 2, dtype=np.float32)
    out = vad_gate.vad_filter_pcm(_pcm_bytes(silence), model)
    assert len(out) < len(_pcm_bytes(silence)) * 0.2, "silence not dropped"


def test_vad_keeps_speech():
    vad_gate, model = _load_gate()
    import subprocess, tempfile
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
    monkeypatch.setenv("VAD_THRESHOLD", "0.99")
    reload_module = _reload(vad_gate)
    sr = reload_module.SAMPLE_RATE
    sig = (0.5 * np.sin(2 * np.pi * 300 * np.arange(sr) / sr)).astype(np.float32)
    out = reload_module.vad_filter_pcm(_pcm_bytes(sig), model, threshold=0.99)
    assert len(out) < len(_pcm_bytes(sig)) * 0.5


def _reload(module):
    import importlib
    return importlib.reload(module)


class _EnergyVAD:
    """Deterministic VAD: any non-zero (energy) window is speech."""

    def __call__(self, window, sr):
        import torch
        val = 1.0 if float(window.abs().max()) > 0.0 else 0.0
        return torch.tensor(val)


def test_vad_pads_both_edges():
    import vad_gate
    FRAME = vad_gate.FRAME_SAMPLES
    PAD = vad_gate.PAD_SAMPLES
    n_frames = 40
    audio = np.zeros(FRAME * n_frames, dtype=np.float32)
    # A single speech blip only in frame 10; everything else is silence.
    start = 10 * FRAME
    audio[start:start + FRAME] = 0.8
    out = vad_gate.vad_filter_pcm(_pcm_bytes(audio), _EnergyVAD())
    out_n = len(out) // 2
    assert out_n >= FRAME, "speech frame dropped"
    # Lead-in: should start before frame 10.
    assert out_n >= FRAME + PAD, "missing leading pad"
    # Trailing: should extend past frame 11 (PAD samples after speech end).
    assert out_n >= (11 * FRAME) + PAD, "missing trailing pad after speech end"

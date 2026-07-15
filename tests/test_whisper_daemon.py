import os
import sys
import numpy as np
import soundfile as sf
import importlib.util

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_wd():
    spec = importlib.util.spec_from_file_location("wd", os.path.join(REPO, "whisper-daemon.py"))
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    return wd


def _fixture_int16():
    audio, _ = sf.read(os.path.join(REPO, "tests", "fixtures", "sample-en.wav"))
    return (np.clip(audio, -1, 1) * 32768).astype(np.int16).tobytes()


def test_transcribe_runs_without_vad_kwarg_error(tmp_path):
    """Regression: vad_parameters must not include invalid kwargs (e.g.
    window_size_samples) or WHISPER dictation breaks entirely."""
    wd = _load_wd()
    os.environ["WHISPER_EXPORT_PATH"] = str(tmp_path / "out.srt")
    os.environ["OUTPUT_FORMAT"] = "srt"
    text = wd.transcribe("tiny.en", "en", "int8", _fixture_int16())
    assert isinstance(text, str)
    # Export file should exist (segments present).
    assert (tmp_path / "out.srt").exists()


def test_transcribe_no_export_when_path_unset():
    wd = _load_wd()
    os.environ.pop("WHISPER_EXPORT_PATH", None)
    text = wd.transcribe("tiny.en", "en", "int8", _fixture_int16())
    assert isinstance(text, str)

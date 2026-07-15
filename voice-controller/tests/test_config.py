import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import load_last_mode, save_last_mode


def test_load_missing_defaults_to_tts(tmp_path):
    assert load_last_mode(str(tmp_path / 'nope')) == 'TTS'


def test_load_invalid_defaults(tmp_path):
    p = tmp_path / 'm'
    p.write_text('GARBAGE')
    assert load_last_mode(str(p)) == 'TTS'


def test_load_valid_stt(tmp_path):
    p = tmp_path / 'm'
    p.write_text('STT')
    assert load_last_mode(str(p)) == 'STT'


def test_load_case_insensitive(tmp_path):
    p = tmp_path / 'm'
    p.write_text('stt\n')
    assert load_last_mode(str(p)) == 'STT'


def test_save_creates_dir_and_roundtrip(tmp_path):
    p = tmp_path / 'sub' / 'last-mode'
    save_last_mode(str(p), 'STT')
    assert p.read_text() == 'STT'
    assert load_last_mode(str(p)) == 'STT'


def test_save_rejects_bad_mode(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        save_last_mode(str(tmp_path / 'm'), 'XXX')

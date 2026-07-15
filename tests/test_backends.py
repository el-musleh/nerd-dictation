import os
import sys
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    sys.path.insert(0, REPO)
    import backends
    return backends


def test_known_backends_registered():
    b = _load()
    for name in ("VOSK", "WHISPER", "WLK"):
        assert name in b.BACKENDS, f"{name} missing from registry"


def test_is_valid_engine():
    b = _load()
    assert b.is_valid_engine("VOSK")
    assert b.is_valid_engine("WLK")
    assert not b.is_valid_engine("whisper")   # exact match; case-folding is in resolve
    assert not b.is_valid_engine("GARBAGE")


def test_resolve_english_backend_valid():
    b = _load()
    assert b.resolve_english_backend("WLK") == "WLK"
    assert b.resolve_english_backend("whisper") == "WHISPER"


def test_resolve_english_backend_invalid():
    b = _load()
    with pytest.raises(ValueError):
        b.resolve_english_backend("NOPE")


def test_cli_validate():
    b = _load()
    # valid
    r = subprocess.run([sys.executable, os.path.join(REPO, "backends.py"),
                        "validate", "WLK"], capture_output=True)
    assert r.returncode == 0
    # invalid
    r = subprocess.run([sys.executable, os.path.join(REPO, "backends.py"),
                        "validate", "BOGUS"], capture_output=True)
    assert r.returncode == 1


def test_cli_list():
    b = _load()
    r = subprocess.run([sys.executable, os.path.join(REPO, "backends.py"),
                        "list"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "VOSK" in r.stdout and "WHISPER" in r.stdout and "WLK" in r.stdout

import os
import sys
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    sys.path.insert(0, REPO)
    import punctuate
    return punctuate


def test_empty_returns_empty():
    b = _load()
    assert b.punctuate("") == ""
    assert b.punctuate("   ") == ""


def test_punctuate_english():
    b = _load()
    out = b.punctuate("hi how are you im doing well today")
    # Should add caps + punctuation (at least a capital start and a terminator).
    assert out[:1].isupper(), f"no capitalization: {out!r}"
    assert any(p in out for p in ".?!"), f"no punctuation: {out!r}"


def test_punctuate_unknown_graceful():
    b = _load()
    # Even if model download is slow/unavailable, it must not crash.
    out = b.punctuate("hello world this is a test")
    assert isinstance(out, str) and len(out) > 0


def test_cli():
    b = _load()
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "punctuate.py"), "hello how are you"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert r.stdout.strip()[:1].isupper()

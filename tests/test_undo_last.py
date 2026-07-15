import os
import sys
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    sys.path.insert(0, REPO)
    import undo_last
    return undo_last


def test_count_from_text(tmp_path, monkeypatch):
    f = tmp_path / "last"
    f.write_text("hello world")
    monkeypatch.setenv("LAST_UTTERANCE_FILE", str(f))
    b = _load()
    assert len(b.last_text()) == 11


def test_undo_sends_backspaces(tmp_path, monkeypatch):
    b = _load()
    calls = []
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: calls.append(a))
    n = b.undo(5)
    assert n == 5
    # xdotool key BackSpace BackSpace ... (5 times)
    cmd = calls[0][0]
    assert cmd[0] == "xdotool" and cmd[1] == "key"
    assert cmd.count("BackSpace") == 5


def test_undo_zero_noop():
    b = _load()
    assert b.undo(0) == 0

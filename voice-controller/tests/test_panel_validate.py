import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk

import popup


def test_run_validate_parses_errors(monkeypatch):
    bad = SimpleNamespace(returncode=1, stdout="",
                          stderr="[ERROR] VAD_GATE must be off|on (got 'maybe')\n")
    good = SimpleNamespace(returncode=0, stdout="OK\n", stderr="")
    seq = {"i": 0}

    def fake_run(*a, **k):
        seq["i"] += 1
        return bad if seq["i"] == 1 else good

    monkeypatch.setattr(subprocess_mod(), "run", fake_run)

    p = popup.PopupPanel.__new__(popup.PopupPanel)
    ok, errors = p._run_validate()
    assert ok is False
    assert any("VAD_GATE" in e for e in errors), errors
    ok2, _ = p._run_validate()
    assert ok2 is True


def test_update_validation_label_sets_markup(monkeypatch):
    good = SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    def fake_run(*a, **k):
        return good

    monkeypatch.setattr(subprocess_mod(), "run", fake_run)

    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._settings_status = Gtk.Label()
    p._update_validation_label()
    assert "config valid" in p._settings_status.get_label(), p._settings_status.get_label()


def subprocess_mod():
    import subprocess
    return subprocess

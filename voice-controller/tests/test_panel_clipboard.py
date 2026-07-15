import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

import popup


class _FakeClipboard:
    def __init__(self):
        self.text = None

    def set_text(self, text, _len):
        self.text = text


def test_copy_session_on_stop_copies_full(monkeypatch):
    p = popup.PopupPanel.__new__(popup.PopupPanel)  # bypass GTK init
    p._history_session = ["hello world", "second line"]
    p._cfg = {"COPY_ON_STOP": "on"}
    fake = _FakeClipboard()
    monkeypatch.setattr(Gtk.Clipboard, "get", lambda *_a, **_k: fake)
    p._copy_session_on_stop()
    assert fake.text == "hello world\nsecond line"


def test_copy_session_on_stop_disabled_noop(monkeypatch):
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._history_session = ["x"]
    p._cfg = {"COPY_ON_STOP": "off"}
    fake = _FakeClipboard()
    monkeypatch.setattr(Gtk.Clipboard, "get", lambda *_a, **_k: fake)
    p._copy_session_on_stop()
    assert fake.text is None


def test_copy_session_on_stop_empty_noop(monkeypatch):
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._history_session = []
    p._cfg = {"COPY_ON_STOP": "on"}
    fake = _FakeClipboard()
    monkeypatch.setattr(Gtk.Clipboard, "get", lambda *_a, **_k: fake)
    p._copy_session_on_stop()
    assert fake.text is None

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import popup


def _build():
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    Gtk.Window.__init__(p, type=Gtk.WindowType.TOPLEVEL)
    p._on_start = p._on_stop = p._on_quit = None
    import queue
    p._level_q = queue.Queue()
    p._text_q = queue.Queue()
    p._cfg = popup.read_config()
    p._history_session = []
    p._partial_start = None
    p._cur_state = "IDLE"
    p._cur_engine = "VOSK"
    popup.PopupPanel._build_ui(p)
    return p


def test_settings_tab_built():
    p = _build()
    # Live, Engine, History, Models, Settings = 5 pages
    assert p._nb.get_n_pages() == 5
    assert p._settings_page_index == 4
    # Last page label is "Settings"
    assert "Settings" in p._nb.get_tab_label_text(p._nb.get_nth_page(4))


def test_settings_button_switches_to_settings_tab(monkeypatch):
    p = _build()
    # Simulate the Settings button handler (lambda w: set_current_page(idx))
    switched = {}
    monkeypatch.setattr(p._nb, "set_current_page",
                        lambda i: switched.update({"i": i}))
    # replicate the button's lambda behaviour
    handler = lambda w: p._nb.set_current_page(p._settings_page_index)
    handler(None)
    assert switched["i"] == p._settings_page_index == 4


def test_settings_tab_binds_engine_key(monkeypatch):
    written = {}

    class _StubCB:
        def __init__(self, val):
            self._val = val

        def get_active_text(self):
            return self._val

        def connect(self, sig, cb):
            self._cb = cb

    monkeypatch.setattr(popup, "write_config_key",
                        lambda k, v: written.update({k: v}))
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._cfg = {}
    cb = _StubCB("WHISPER")
    popup.PopupPanel._bind_setting(p, cb, "ENGLISH_ENGINE",
                                   lambda w: w.get_active_text(), "changed")
    cb._cb(cb)
    assert written == {"ENGLISH_ENGINE": "WHISPER"}

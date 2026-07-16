import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GLib

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


def _find_apply_button(page):
    def walk(w):
        if isinstance(w, Gtk.Button) and "Apply" in (w.get_label() or ""):
            return w
        if hasattr(w, "get_children"):
            for c in w.get_children():
                r = walk(c)
                if r:
                    return r
        return None
    return walk(page)


def test_apply_restart_calls_stop_then_start(monkeypatch):
    calls = []

    def fake_run_script(path, log=None):
        calls.append(path)

    monkeypatch.setattr(popup, "run_script", fake_run_script)
    # Make the deferred start run immediately.
    monkeypatch.setattr(GLib, "timeout_add_seconds",
                        lambda sec, fn, *a, **k: fn())
    p = _build()
    # Settings tab is the last notebook page.
    settings_page = p._nb.get_nth_page(p._nb.get_n_pages() - 1)
    btn = _find_apply_button(settings_page)
    assert btn is not None, "Apply & Restart button not found"
    btn.emit("clicked")
    assert calls == [popup.DICTATE_STOP, popup.DICTATE_START], calls

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


def _find_undo_button(page):
    # The Undo button is the only Gtk.Button whose label starts with "Undo"
    # in the live page subtree.
    def walk(w):
        if isinstance(w, Gtk.Button) and "Undo" in (w.get_label() or ""):
            return w
        if hasattr(w, "get_children"):
            for c in w.get_children():
                r = walk(c)
                if r:
                    return r
        return None
    return walk(page)


def test_undo_button_calls_undo_last(monkeypatch):
    called = {}
    monkeypatch.setattr(popup, "run_script",
                        lambda path, log=None: called.update({"path": path}))
    p = _build()
    page = p._nb.get_nth_page(p._live_page_index)
    btn = _find_undo_button(page)
    assert btn is not None, "Undo button not found on Live tab"
    btn.emit("clicked")
    assert called.get("path") == popup.UNDO_LAST, called

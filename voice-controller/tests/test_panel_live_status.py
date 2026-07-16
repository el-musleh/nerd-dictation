import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
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


def test_live_status_widgets_exist():
    p = _build()
    assert hasattr(p, "_live_status"), "live status label missing"
    # legend present in the live page
    page = p._nb.get_nth_page(p._live_page_index)
    assert page is not None


def test_live_status_updates_on_dictating():
    p = _build()
    p._update_live_status("DICTATING", lang="en", engine="VOSK")
    assert "VOSK" in p._live_status.get_text()
    assert "streaming" in p._live_status.get_text()


def test_live_status_idle():
    p = _build()
    p._update_live_status("IDLE")
    assert p._live_status.get_text() == "● idle"

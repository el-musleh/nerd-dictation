import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import popup


def test_should_auto_show_vosk_on():
    assert popup.should_auto_show("VOSK", {}) is True


def test_should_auto_show_whisper_off():
    assert popup.should_auto_show("WHISPER", {}) is False


def test_should_auto_show_wlk_off():
    assert popup.should_auto_show("WLK", {}) is False


def test_should_auto_show_no_engine():
    assert popup.should_auto_show("", {}) is False


def test_should_auto_show_disabled():
    assert popup.should_auto_show("VOSK", {"AUTO_SHOW_ON_VOSK": "off"}) is False


def test_build_ui_wires_notebook_and_live_index():
    # Build the UI on the real display (DISPLAY=:0) without starting threads.
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    # GTK requires the GObject to be initialized before building UI.
    Gtk.Window.__init__(p, type=Gtk.WindowType.TOPLEVEL)
    p._on_start = p._on_stop = p._on_quit = None
    p._level_q = __import__("queue").Queue()
    p._text_q = __import__("queue").Queue()
    p._cfg = popup.read_config()
    p._history_session = []
    p._partial_start = None
    p._cur_state = "IDLE"
    p._cur_engine = "VOSK"
    popup.PopupPanel._build_ui(p)
    assert isinstance(p._nb, Gtk.Notebook)
    assert p._live_page_index == 0
    assert p._nb.get_n_pages() >= 4
    # Live tab is first page
    assert p._nb.get_nth_page(0) is not None

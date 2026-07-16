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


def test_active_model_badge(monkeypatch):
    monkeypatch.setattr(popup, "installed_models",
                        lambda: [("small.en", "/x/small.en", 100),
                                 ("base.en", "/x/base.en", 80)])
    p = _build()
    p._cfg["ENGLISH_WHISPER_MODEL"] = "small.en"
    p._refresh_models()

    def find_active_badge(w):
        if isinstance(w, Gtk.Label) and "active" in (w.get_label() or ""):
            return True
        if hasattr(w, "get_children"):
            for c in w.get_children():
                if find_active_badge(c):
                    return True
        return False

    assert find_active_badge(p._models_flow), "active badge not shown for small.en"


def test_active_model_names_parses_lang_models():
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._cfg = {"ENGLISH_WHISPER_MODEL": "small.en",
              "LANG_MODELS": "en:tiny.en,ar:small"}
    names = p._active_model_names()
    assert "small.en" in names
    assert "tiny.en" in names
    assert "small" in names

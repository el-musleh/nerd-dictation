import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk

import popup


def _new_panel(cfg=None):
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    Gtk.Window.__init__(p, type=Gtk.WindowType.TOPLEVEL)
    p._cfg = cfg if cfg is not None else {}
    return p


def test_save_geometry_writes_keys(monkeypatch):
    written = {}
    monkeypatch.setattr(popup, "write_config_key",
                        lambda k, v: written.update({k: v}))
    p = _new_panel({"PANEL_REMEMBER": "on"})
    p.move(40, 60)
    p.resize(420, 640)
    p._save_geometry()
    assert written.get("PANEL_X") == "40"
    assert written.get("PANEL_Y") == "60"
    assert written.get("PANEL_W") == "420"
    assert written.get("PANEL_H") == "640"
    assert "PANEL_VISIBLE" in written


def test_save_geometry_skipped_when_disabled(monkeypatch):
    written = {}
    monkeypatch.setattr(popup, "write_config_key",
                        lambda k, v: written.update({k: v}))
    p = _new_panel({"PANEL_REMEMBER": "off"})
    p._save_geometry()
    assert written == {}, written


def test_restore_geometry_applies(monkeypatch):
    p = _new_panel({"PANEL_REMEMBER": "on",
                    "PANEL_X": "10", "PANEL_Y": "20",
                    "PANEL_W": "300", "PANEL_H": "500"})
    p._restore_geometry()
    x, y = p.get_position()
    w, h = p.get_size()
    assert x == 10 and y == 20
    assert w == 300 and h == 500

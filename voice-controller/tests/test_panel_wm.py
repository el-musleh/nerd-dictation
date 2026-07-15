import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

import popup


def test_apply_window_hints_sets_wmclass():
    # set_wmclass has no introspectable getter in this GTK3 binding; verify
    # the helper calls it with the expected class via a stub window.
    calls = {}

    class _StubWin:
        def set_wmclass(self, name, cls):
            calls["name"] = name
            calls["cls"] = cls

        def set_type_hint(self, hint):
            calls["hint"] = hint

        def set_skip_taskbar_hint(self, val):
            calls["skip"] = val

    popup.apply_window_hints(_StubWin(), {})
    assert calls["name"] == "voice-controller"
    assert calls["cls"] == "VoiceController"


def test_apply_window_hints_skip_taskbar_default_off():
    w = Gtk.Window()
    popup.apply_window_hints(w, {})
    # Default PANEL_IN_TASKBAR is off -> skip_taskbar True (utility hint)
    assert w.get_skip_taskbar_hint() is True


def test_apply_window_hints_in_taskbar_on():
    w = Gtk.Window()
    popup.apply_window_hints(w, {"PANEL_IN_TASKBAR": "on"})
    assert w.get_skip_taskbar_hint() is False


def test_apply_window_hints_type_hint_utility():
    w = Gtk.Window()
    popup.apply_window_hints(w, {})
    assert w.get_type_hint() == Gdk.WindowTypeHint.UTILITY

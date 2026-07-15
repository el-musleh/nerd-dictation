import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import popup


def test_bind_setting_combobox_writes_key(monkeypatch):
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
    cb = _StubCB("float16")
    popup.PopupPanel._bind_setting(p, cb, "COMPUTE_TYPE",
                                   lambda w: w.get_active_text(), "changed")
    cb._cb(cb)  # simulate change
    assert written == {"COMPUTE_TYPE": "float16"}


def test_bind_setting_checkbutton_writes_key(monkeypatch):
    written = {}

    class _StubChk:
        def __init__(self, val):
            self._val = val

        def get_active(self):
            return self._val

        def connect(self, sig, cb):
            self._cb = cb

    monkeypatch.setattr(popup, "write_config_key",
                        lambda k, v: written.update({k: v}))
    p = popup.PopupPanel.__new__(popup.PopupPanel)
    p._cfg = {}
    chk = _StubChk(True)
    popup.PopupPanel._bind_setting(p, chk, "COPY_ON_STOP",
                                   lambda w: "on" if w.get_active() else "off",
                                   "toggled")
    chk._cb(chk)
    assert written == {"COPY_ON_STOP": "on"}

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from menu import build_menu, run_script


class _FakeCtl:
    mode = 'STT'


_NOOP = lambda icon=None, item=None: None
_HANDLER = {
    'on_stt_start': _NOOP,
    'on_stt_stop': _NOOP,
    'on_stt_settings': _NOOP,
}


def test_menu_has_start_stop_settings_quit():
    c = _FakeCtl()
    menu = build_menu(c, _HANDLER, _NOOP)
    labels = [getattr(i, 'text', None) for i in menu.items]
    # pystray stores text as a string or callable; normalize.
    texts = []
    for it in menu.items:
        t = it.text
        texts.append(t() if callable(t) else t)
    assert 'Start Dictation (Super+H)' in texts
    assert 'Stop Dictation (Shift+Super+H)' in texts
    assert 'Show Settings' in texts
    assert 'Quit' in texts


def test_run_script_calls_bash(monkeypatch, tmp_path):
    called = {}
    monkeypatch.setattr('menu.subprocess.Popen',
                        lambda args, **kw: called.setdefault('args', args))
    script = tmp_path / 'dictate-start'
    script.write_text('#!/bin/bash\n')
    run_script(str(script))
    assert called['args'] == ['bash', str(script)]

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from switch import set_mode


def _stops():
    return {'tts': lambda: None, 'stt': lambda: None}


def test_noop_same_mode():
    out = set_mode('TTS', 'TTS', False, False, _stops(), lambda m: None, lambda m: None)
    assert out == 'TTS'


def test_switch_tts_to_stt_stops_tts():
    calls = []
    stops = {'tts': lambda: calls.append('t'), 'stt': lambda: calls.append('s')}
    out = set_mode('STT', 'TTS', True, False, stops, lambda m: None, lambda m: None)
    assert out == 'STT' and calls == ['t']


def test_switch_stt_to_tts_stops_stt():
    calls = []
    stops = {'tts': lambda: calls.append('t'), 'stt': lambda: calls.append('s')}
    out = set_mode('TTS', 'STT', False, True, stops, lambda m: None, lambda m: None)
    assert out == 'TTS' and calls == ['s']


def test_switch_does_not_stop_if_inactive():
    calls = []
    saved = []
    stops = {'tts': lambda: calls.append('t'), 'stt': lambda: calls.append('s')}
    out = set_mode('STT', 'TTS', False, False, stops,
                   lambda m: saved.append(m), lambda m: None)
    assert out == 'STT' and calls == [] and saved == ['STT']


def test_switch_persists_and_refreshes():
    saved = []
    refreshed = []
    set_mode('STT', 'TTS', False, False, _stops(),
             lambda m: saved.append(m), lambda m: refreshed.append(m))
    assert saved == ['STT'] and refreshed == ['STT']


def test_invalid_mode_noop():
    out = set_mode('XXX', 'TTS', False, False, _stops(), lambda m: None, lambda m: None)
    assert out == 'TTS'

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import parse_tts_status, parse_dictate_state


def test_parse_tts_status_normal():
    assert parse_tts_status('PLAYING\n') == 'PLAYING'
    assert parse_tts_status('paused') == 'PAUSED'        # case-insensitive
    assert parse_tts_status('  GENERATING  ') == 'GENERATING'


def test_parse_tts_status_invalid():
    assert parse_tts_status('') == 'IDLE'
    assert parse_tts_status('GARBAGE') == 'IDLE'
    assert parse_tts_status(None) == 'IDLE'


def test_parse_dictate_active(tmp_path):
    f = tmp_path / 'dictate-state'
    f.write_text('PID:999999\nLANG:ara\n')
    assert parse_dictate_state(str(f), _pid_alive=lambda p: True) == 'DICTATING'


def test_parse_dictate_dead_pid(tmp_path):
    f = tmp_path / 'dictate-state'
    f.write_text('PID:999999\n')
    assert parse_dictate_state(str(f), _pid_alive=lambda p: False) == 'IDLE'


def test_parse_dictate_missing():
    assert parse_dictate_state('/nonexistent/path') == 'IDLE'

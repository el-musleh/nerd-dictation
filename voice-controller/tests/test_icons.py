import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from icons import icon_for


def test_icons_return_rgba():
    for s in ['IDLE', 'GENERATING', 'PLAYING', 'PAUSED', 'DICTATING']:
        img = icon_for(s)
        assert img.size == (64, 64)
        assert img.mode == 'RGBA'


def test_icon_for_unknown_defaults_to_idle():
    img = icon_for('NONSENSE')
    assert img.size == (64, 64) and img.mode == 'RGBA'


def test_speaker_icon_for_tts():
    from icons import icon_for_tts
    for s in ['IDLE', 'GENERATING', 'PLAYING', 'PAUSED']:
        img = icon_for_tts(s)
        assert img.size == (64, 64)
        assert img.mode == 'RGBA'


def test_speaker_icon_unknown_defaults():
    from icons import icon_for_tts
    img = icon_for_tts('NONSENSE')
    assert img.size == (64, 64) and img.mode == 'RGBA'

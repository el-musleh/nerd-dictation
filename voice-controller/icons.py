from PIL import Image, ImageDraw


def _base(fill):
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 62, 62], fill=fill)
    return img, d


def _icon_idle():
    """Blue circle — ready / idle."""
    img, d = _base((33, 150, 243, 255))
    return img


def _icon_generating():
    """Purple circle with white spinner arc."""
    img, d = _base((156, 39, 176, 255))
    d.pieslice([14, 14, 50, 50], start=0, end=270, fill=(255, 255, 255, 255))
    return img


def _icon_playing():
    """Green circle with white play triangle."""
    img, d = _base((76, 175, 80, 255))
    d.polygon([(24, 18), (24, 46), (44, 32)], fill=(255, 255, 255, 255))
    return img


def _icon_paused():
    """Orange circle with white pause bars."""
    img, d = _base((255, 87, 34, 255))
    d.rectangle([22, 18, 30, 46], fill=(255, 255, 255, 255))
    d.rectangle([34, 18, 42, 46], fill=(255, 255, 255, 255))
    return img


def _icon_dictating():
    """Red circle with simple white microphone — STT recording."""
    img, d = _base((229, 57, 53, 255))
    # mic body (rounded capsule)
    d.rounded_rectangle([26, 16, 38, 38], radius=6, fill=(255, 255, 255, 255))
    # mic stand
    d.line([32, 38, 32, 46], fill=(255, 255, 255, 255), width=3)
    d.arc([22, 40, 42, 54], start=20, end=160, fill=(255, 255, 255, 255), width=3)
    return img


# --- TTS (speaker) icons: reuse colors, swap glyph for a speaker ---
def _speaker_glyph(d, color=(255, 255, 255, 255)):
    """Draw a speaker triangle + waves into the current draw context."""
    d.polygon([(22, 26), (22, 38), (34, 32)], fill=color)      # cone
    d.rectangle([18, 27, 22, 37], fill=color)                  # magnet
    d.line([37, 24, 37, 40], fill=color, width=3)            # wave 1
    d.line([42, 20, 42, 44], fill=color, width=3)            # wave 2


def _icon_tts_idle():
    img, d = _base((33, 150, 243, 255))
    _speaker_glyph(d)
    return img


def _icon_tts_generating():
    img, d = _base((156, 39, 176, 255))
    _speaker_glyph(d)
    return img


def _icon_tts_playing():
    img, d = _base((76, 175, 80, 255))
    _speaker_glyph(d)
    return img


def _icon_tts_paused():
    img, d = _base((255, 87, 34, 255))
    _speaker_glyph(d)
    # pause bars on top of speaker
    d.rectangle([46, 26, 50, 38], fill=(255, 255, 255, 255))
    d.rectangle([52, 26, 56, 38], fill=(255, 255, 255, 255))
    return img


_ICONS = {
    'IDLE': _icon_idle,
    'GENERATING': _icon_generating,
    'PLAYING': _icon_playing,
    'PAUSED': _icon_paused,
    'DICTATING': _icon_dictating,
}

_TTS_ICONS = {
    'IDLE': _icon_tts_idle,
    'GENERATING': _icon_tts_generating,
    'PLAYING': _icon_tts_playing,
    'PAUSED': _icon_tts_paused,
}


def icon_for(state):
    return _ICONS.get(state, _icon_idle)()


def icon_for_tts(state):
    return _TTS_ICONS.get(state, _icon_tts_idle)()

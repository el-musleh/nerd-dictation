import os


def load_last_mode(path, default='TTS'):
    """Read persisted mode from `path`; return 'TTS'/'STT' or `default`.

    Tolerant of missing/invalid files (falls back to `default`).
    """
    try:
        with open(path) as f:
            v = f.read().strip().upper()
        return v if v in ('TTS', 'STT') else default
    except (OSError, ValueError):
        return default


def save_last_mode(path, mode):
    """Persist `mode` ('TTS'/'STT') to `path`, creating parent dirs."""
    if mode not in ('TTS', 'STT'):
        raise ValueError('mode must be TTS or STT')
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w') as f:
        f.write(mode)

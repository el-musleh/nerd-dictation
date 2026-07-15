def set_mode(mode, current, tts_active, stt_active, stops, save, refresh):
    """Switch active mode with mutual exclusivity.

    Stops the tool active in `current` mode (if any), persists the new mode,
    and refreshes the UI. Returns the new mode. No-op if invalid or unchanged.

    `stops` is a dict with 'tts'/'stt' zero-arg callables.
    `save(mode)` and `refresh(mode)` are callables.
    """
    if mode not in ('TTS', 'STT') or mode == current:
        return current
    if current == 'TTS' and tts_active:
        stops['tts']()
    elif current == 'STT' and stt_active:
        stops['stt']()
    save(mode)
    refresh(mode)
    return mode

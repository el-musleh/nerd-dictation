import subprocess
import os

# Absolute paths to the existing tools — the controller only shells out.
STT_DIR = '/home/steve/dev/stt/nerd-dictation'

import pystray


def build_menu_items(c, handlers):
    """Build the (static) STT-only menu item set.

    `c` exposes `.mode` (always 'STT' here, kept for call-site stability).
    `handlers` maps: on_stt_start, on_stt_stop, on_stt_settings.
    """
    items = {
        'Show Settings': pystray.MenuItem(
            'Show Settings', handlers['on_stt_settings']),
        'Start Dictation': pystray.MenuItem(
            'Start Dictation (Super+H)', handlers['on_stt_start']),
        'Stop Dictation': pystray.MenuItem(
            'Stop Dictation (Shift+Super+H)', handlers['on_stt_stop']),
        'Undo Last': pystray.MenuItem(
            'Undo Last Utterance',
            lambda *_: run_script(os.path.join(STT_DIR, 'undo_last.py'))),
    }
    return items


def build_menu(c, handlers, on_quit):
    items = build_menu_items(c, handlers)
    return pystray.Menu(
        items['Show Settings'],
        pystray.Menu.SEPARATOR,
        items['Start Dictation'],
        items['Stop Dictation'],
        items['Undo Last'],
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Quit', on_quit),
    )


def run_script(abs_path, log=None):
    """Shell out to an existing bash script by absolute path. Pure controller action."""
    if log:
        log.info('Run: %s', abs_path)
    try:
        subprocess.Popen(['bash', abs_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        if log:
            log.error('Failed to run %s: %s', abs_path, e)
        raise

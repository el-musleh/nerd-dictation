#!/usr/bin/env python3
"""
Voice Controller — system-tray + rich popup panel for nerd-dictation (STT).

Architecture:
  - pystray tray icon (blue=idle, red=dictating) runs in main thread.
  - 0.5s poll thread watches ~/.dictate-state and updates icon + popup.
  - popup.py provides the Tkinter floating control panel in its own thread.

Clicking the tray icon toggles the popup.
Right-click menu: Start / Stop / Show Panel / Quit.
"""

import fcntl
import logging
import logging.handlers
import os
import subprocess
import sys
import threading
import time

from icons import icon_for
from menu import build_menu, STT_DIR, run_script
import state as statemod
from popup import PopupPanel

import pystray

LOCK_FILE = '/tmp/voice-controller.lock'
LOG_DIR = os.path.expanduser('~/.local/share/voice-controller')
LOG_FILE = os.path.join(LOG_DIR, 'controller.log')
DICTATE_STATE_FILE = os.path.expanduser('~/.dictate-state')


def _setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger('voice-controller')
    if logger.handlers:
        return logger  # already configured (avoid duplicates)
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_048_576, backupCount=1)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


class VoiceController:
    def __init__(self):
        self.log = _setup_logging()
        self.mode = 'STT'
        self._state = None
        self._running = True
        self._lock_fd = None

        self._acquire_lock()
        self.log.info('Voice Controller started (PID %d)', os.getpid())

        # Build popup panel (spawns its own Tk thread)
        self._popup = PopupPanel(
            on_start=self._on_stt_start,
            on_stop=self._on_stt_stop,
            on_quit=self._on_quit_from_popup,
        )

        self._build_icon()
        self._start_poll()

    # ---- Lock --------------------------------------------------------------

    def _acquire_lock(self):
        try:
            fd = open(LOCK_FILE, 'w')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.write(str(os.getpid()))
            fd.flush()
            self._lock_fd = fd
        except (IOError, OSError):
            self.log.error('Already running — exiting')
            sys.exit(0)

    # ---- Actions -----------------------------------------------------------

    def _on_stt_start(self, icon=None, item=None):
        run_script(os.path.join(STT_DIR, 'dictate-start'), self.log)

    def _on_stt_stop(self, icon=None, item=None):
        run_script(os.path.join(STT_DIR, 'dictate-stop'), self.log)

    def _on_show_panel(self, icon=None, item=None):
        self._popup.toggle()

    def _on_quit_from_popup(self):
        """Called from popup's Quit button."""
        self._shutdown()

    # ---- Tray icon ---------------------------------------------------------

    def _build_icon(self):
        self._icon = pystray.Icon(
            'voice-controller',
            icon=icon_for('IDLE'),
            title='Voice Controller',
            menu=self._make_menu(),
        )
        # Left-click toggles popup (pystray default_action)
        self._icon.default_action = self._on_show_panel

    def _make_menu(self):
        return pystray.Menu(
            pystray.MenuItem('Show / Hide Panel',
                             self._on_show_panel, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Start Dictation  (Super+H)', self._on_stt_start),
            pystray.MenuItem('Stop Dictation   (⇧Super+H)', self._on_stt_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self._on_quit),
        )

    # ---- Polling -----------------------------------------------------------

    def _start_poll(self):
        def loop():
            while self._running:
                self._tick()
                time.sleep(0.5)
        threading.Thread(target=loop, daemon=True).start()

    def _tick(self):
        state_tuple = statemod.parse_dictate_state_full(DICTATE_STATE_FILE)
        state = state_tuple[0]
        lang = state_tuple[1] if len(state_tuple) > 1 else ""
        engine = state_tuple[2] if len(state_tuple) > 2 else ""

        if state != self._state:
            self._state = state
            self._apply_state(state, lang, engine)

        # Always push state to popup (lang/engine may change even if state doesn't)
        self._popup.update_state(state, lang, engine)

    def _apply_state(self, state, lang="", engine=""):
        self._icon.icon = icon_for(state)
        label = '●  Dictating' if state == 'DICTATING' else '○  Ready'
        self._icon.title = f'Voice Controller — {label}'
        self.log.info('State [STT]: %s  lang=%s  engine=%s', state, lang, engine)

    # ---- Quit --------------------------------------------------------------

    def _on_quit(self, icon, item):
        self._shutdown()

    def _shutdown(self):
        self.log.info('Quit requested')
        self._running = False
        if statemod.parse_dictate_state(DICTATE_STATE_FILE) == 'DICTATING':
            self._on_stt_stop()
        self._popup.destroy()
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
            except OSError:
                pass
        self._icon.stop()

    def run(self):
        self._icon.run()


def main():
    VoiceController().run()


if __name__ == '__main__':
    main()

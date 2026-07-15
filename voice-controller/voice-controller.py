#!/usr/bin/env python3
"""
Voice Controller — unified system-tray for TTS (speak-aloud-linux) and
STT (nerd-dictation) on this machine.

Pure controller: it polls each tool's native state file and shells out to the
existing bash scripts via absolute paths. It does NOT reimplement any
TTS/STT logic. Mirrors the architecture of tts-daemon.py.

Single-instance (lock), 0.5s poll thread, PIL-drawn status icons.

Run:  python3 voice-controller.py
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

import pystray

LOCK_FILE = '/tmp/voice-controller.lock'
LOG_DIR = os.path.expanduser('~/.local/share/voice-controller')
LOG_FILE = os.path.join(LOG_DIR, 'controller.log')
DICTATE_STATE_FILE = os.path.expanduser('~/.dictate-state')


def _setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger('voice-controller')
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_048_576, backupCount=1)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


class VoiceController:
    def __init__(self, mode=None):
        self.log = _setup_logging()
        # STT-only controller: always run in STT mode (red mic icon).
        self.mode = 'STT'
        self._state = None
        self._running = True
        self._lock_fd = None

        self._acquire_lock()
        self.log.info('Voice Controller started (PID %d), mode=%s', os.getpid(), self.mode)

        self._build_handlers()
        self._build_icon()
        self._start_poll()

    # ---- logging -------------------------------------------------------
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

    # ---- handlers (shell-out) ------------------------------------------
    def _build_handlers(self):
        self._handlers = {
            'on_stt_start': self._on_stt_start,
            'on_stt_stop': self._on_stt_stop,
            'on_stt_settings': self._on_stt_settings,
        }

    def _on_stt_start(self, icon=None, item=None):
        run_script(os.path.join(STT_DIR, 'dictate-start'), self.log)

    def _on_stt_stop(self, icon=None, item=None):
        run_script(os.path.join(STT_DIR, 'dictate-stop'), self.log)

    def _on_stt_settings(self, icon=None, item=None):
        # Guard against launching two settings dialogs.
        if subprocess.run(['pgrep', '-f', 'stt-settings.sh'],
                          capture_output=True).returncode == 0:
            return
        run_script(os.path.join(STT_DIR, 'stt-settings.sh'), self.log)

    # ---- icon / menu ---------------------------------------------------
    def _build_icon(self):
        self._icon = pystray.Icon(
            'voice-controller',
            icon=icon_for('IDLE'),
            title='Voice Controller — STT',
            menu=build_menu(self, self._handlers, self._on_quit),
        )

    # ---- polling -------------------------------------------------------
    def _start_poll(self):
        def loop():
            while self._running:
                self._tick()
                time.sleep(0.5)
        threading.Thread(target=loop, daemon=True).start()

    def _tick(self):
        # STT-only: poll the dictation state file.
        state = statemod.parse_dictate_state(DICTATE_STATE_FILE)
        if state != self._state:
            self._state = state
            self._apply_state(state)

    @staticmethod
    def _read_file(path):
        try:
            with open(path) as f:
                return f.read()
        except (FileNotFoundError, OSError):
            return ''

    def _apply_state(self, state):
        label = '●  Dictating' if state == 'DICTATING' else '○  Ready'
        self._refresh_title(label)
        self._icon.icon = icon_for(state)
        # Force the indicator to recreate the icon (same trick as tts-daemon).
        for fn in ('_hide', '_show'):
            if hasattr(self._icon, fn):
                getattr(self._icon, fn)()
        self.log.info('State [STT]: %s', state)

    def _last_label(self):
        if self._state is None:
            return None
        return '●  Dictating' if self._state == 'DICTATING' else '○  Ready'

    def _refresh_title(self, label):
        self._icon.title = f'Voice Controller — {label}'

    # ---- quit ----------------------------------------------------------
    def _on_quit(self, icon, item):
        self.log.info('Quit requested')
        self._running = False
        # Stop dictation if active.
        if statemod.parse_dictate_state(DICTATE_STATE_FILE) == 'DICTATING':
            self._on_stt_stop()
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
            except OSError:
                pass
        self._icon.stop()

    def run(self):
        self._icon.run()


def _setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger('voice-controller')
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_048_576, backupCount=1)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def main():
    VoiceController().run()


if __name__ == '__main__':
    main()

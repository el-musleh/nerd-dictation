import os


_VALID = {'IDLE', 'GENERATING', 'RETRYING', 'PLAYING', 'PAUSED'}


def parse_tts_status(text):
    """Normalize raw /tmp/tts-status content to a canonical state.

    Anything not in the known set (empty, garbage, wrong case) -> 'IDLE'.
    """
    s = (text or '').strip().upper()
    return s if s in _VALID else 'IDLE'


def parse_dictate_state(path, _pid_alive=None):
    """Return 'DICTATING' if ~/.dictate-state exists with a live PID, else 'IDLE'.

    `_pid_alive` is injectable for testing; defaults to os.kill(pid, 0).
    """
    alive = _pid_alive if _pid_alive is not None else _os_kill_alive
    try:
        data = {}
        with open(path) as fh:
            for line in fh:
                if ':' in line:
                    k, v = line.strip().split(':', 1)
                    data[k] = v
        pid = data.get('PID')
        if pid:
            return 'DICTATING' if alive(int(pid)) else 'IDLE'
    except (OSError, ValueError):
        pass
    return 'IDLE'


def _os_kill_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False

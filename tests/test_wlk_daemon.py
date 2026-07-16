import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WLK_DAEMON = os.path.join(REPO, "wlk-daemon.py")
WLK_VENV_PY = "/home/steve/dev/stt/WhisperLiveKit/.venv/bin/python"


def test_wlk_daemon_syntax():
    import py_compile
    py_compile.compile(WLK_DAEMON, doraise=True)


def test_whisperlivekit_importable():
    # WhisperLiveKit must be installed in its venv for the backend to work.
    out = subprocess.run(
        [WLK_VENV_PY, "-c", "import whisperlivekit; print('ok')"],
        capture_output=True, text=True,
    )
    assert "ok" in out.stdout, out.stderr


@pytest.mark.skipif(not os.path.exists(WLK_VENV_PY), reason="WLK venv not installed")
def test_wlk_daemon_launch_smoke():
    # Launch wlk-daemon.py briefly; it should start the WLK server and stay up
    # until killed. We don't feed mic audio (headless), just confirm it boots.
    proc = subprocess.Popen(
        [sys.executable, WLK_DAEMON, "--model", "tiny", "--language", "en"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # Give it time to start the server + connect.
        import time
        time.sleep(20)
        assert proc.poll() is None, "wlk-daemon exited early (see /tmp/wlk-server.log)"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def test_server_died_clears_ready_file(monkeypatch, tmp_path):
    # _server_died() must remove the ready file so a stale "WLK is up" flag
    # is never trusted after the server dies.
    import importlib.util

    spec = importlib.util.spec_from_file_location("wlk_daemon_mod", WLK_DAEMON)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ready = tmp_path / "wlk-ready"
    ready.write_text("")
    monkeypatch.setattr(mod, "WLK_READY_FILE", str(ready))
    # Prevent the real process exit during the test.
    monkeypatch.setattr(os, "_exit", lambda *_a, **_k: None)
    mod._server_died()
    assert not ready.exists(), "ready file should be removed on server death"


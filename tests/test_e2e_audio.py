"""End-to-end audio tests for nerd-dictation backends.

Validates the underlying engines headlessly (no microphone) using a
synthesized, known-text English fixture:
  tests/fixtures/sample-en.wav  (espeak-ng, "the quick brown fox ...")
  tests/fixtures/sample-en.txt  (ground-truth text)

Run:
  python3 -m pytest tests/test_e2e_audio.py -v
"""
import os
import subprocess
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_WAV = os.path.join(REPO, "tests", "fixtures", "sample-en.wav")
FIXTURE_TXT = os.path.join(REPO, "tests", "fixtures", "sample-en.txt")
WLK_VENV_PY = "/home/steve/dev/stt/WhisperLiveKit/.venv/bin/python"

EXPECTED_KEYWORDS = ["quick", "fox", "lazy", "test", "speech", "recognition"]


def _ground_truth() -> str:
    with open(FIXTURE_TXT) as f:
        return f.read().lower()


def test_fixture_present():
    assert os.path.exists(FIXTURE_WAV), "missing fixture wav"
    assert os.path.exists(FIXTURE_TXT), "missing fixture txt"


def test_whisper_backend_transcribes():
    """WHISPER backend (faster-whisper) — the current default English path."""
    from faster_whisper import WhisperModel

    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(FIXTURE_WAV, language="en")
    text = " ".join(s.text for s in segments).lower()
    assert info.language in ("en", "english", None)
    # Synthesized TTS is imperfect; assert most expected keywords survive.
    present = [k for k in EXPECTED_KEYWORDS if k in text]
    assert len(present) >= 4, f"only {present} of {EXPECTED_KEYWORDS} in: {text!r}"
    print(f"[WHISPER] {text!r}  keywords={present}")


@pytest.mark.skipif(not os.path.exists(WLK_VENV_PY), reason="WLK venv missing")
def test_wlk_backend_transcribes_via_rest():
    """WLK backend via its OpenAI-compatible REST API (mirrors wlk-daemon path).

    Skips if the 'tiny' model isn't already cached (first-run download can
    exceed the test timeout). One-time setup: `wlk pull tiny`.
    """
    import urllib.request

    # One-time model check: skip if not installed to avoid slow-download flakiness.
    models_out = subprocess.run(
        [WLK_VENV_PY, "-m", "whisperlivekit.cli", "models"],
        capture_output=True, text=True, timeout=30,
    )
    if "tiny" not in (models_out.stdout + models_out.stderr).lower():
        pytest.skip("WLK 'tiny' model not cached — run `wlk pull tiny` once")

    # Start WLK server in PCM-not-required file mode on an alternate port.
    port = 8011
    srv = subprocess.Popen(
        [WLK_VENV_PY, "-m", "whisperlivekit.cli", "serve",
         "--model", "tiny", "--host", "127.0.0.1", "--port", str(port)],
        stdout=open("/tmp/wlk-e2e.log", "w"), stderr=subprocess.STDOUT,
    )
    try:
        # Wait for server (poll REST endpoint).
        url = f"http://127.0.0.1:{port}/v1/audio/transcriptions"
        ready = False
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=2)
                ready = True
                break
            except Exception:
                time.sleep(1)
        assert ready, "WLK server did not start (see /tmp/wlk-e2e.log)"

        # POST the audio file like OpenAI's API.
        boundary = "----ndtestboundary"
        with open(FIXTURE_WAV, "rb") as f:
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="sample.wav"\r\n'
                f"Content-Type: audio/wav\r\n\r\n"
            ).encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=60).read().decode()
        import json
        data = json.loads(resp)
        text = (data.get("text") or "").lower()
        assert text, f"WLK returned empty text: {resp!r}"
        present = [k for k in EXPECTED_KEYWORDS if k in text]
        assert len(present) >= 3, f"only {present} in WLK output: {text!r}"
        print(f"[WLK] {text!r}  keywords={present}")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()

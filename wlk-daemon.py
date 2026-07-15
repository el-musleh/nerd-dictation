#!/usr/bin/env python3
"""wlk-daemon.py — English real-time dictation via WhisperLiveKit (WLK).

Launches the WhisperLiveKit server in PCM-input mode, streams microphone audio
(via parec, the same PulseAudio source nerd-dictation uses) over the WebSocket
API, and types the committed transcription text with xdotool — mirroring how
the VOSK/Whisper paths type.

Protocol (verified against whisperlivekit/test_client.py):
  - Audio: raw PCM s16le, 16kHz, mono, sent as WebSocket bytes.
  - Server must run with --pcm-input.
  - Client connects ws://host:port/asr?language=en, receives a config JSON,
    then streams PCM chunks, then sends b"" to signal end-of-audio.
  - Server replies JSON: {"lines":[{"text":...}], "buffer_transcription":...}.
    Committed text = " ".join(line["text"] for line in lines).

Run (typically invoked by dictate-start):
  wlk-daemon.py --model small --language en

Stop: dictate-stop sends SIGTERM / kills this process; we signal end-of-audio
and terminate the server.
"""
import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys

WLK_VENV_PYTHON = "/home/steve/dev/stt/WhisperLiveKit/.venv/bin/python"
WLK_SERVER_HOST = os.environ.get("WLK_HOST", "127.0.0.1")
WLK_SERVER_PORT = int(os.environ.get("WLK_PORT", "8000"))
# Touch when the WLK server is confirmed up; removed on exit. dictate-start
# watches this to decide whether to fall back to VOSK.
WLK_READY_FILE = os.path.expanduser("~/.cache/nerd-dictation/wlk-ready")
SAMPLE_RATE = 16000
# Seconds per PCM chunk sent to the WLK server. Smaller = lower latency,
# larger = less overhead. Tunable via WLK_CHUNK (0.1-0.5).
CHUNK_DURATION = float(os.environ.get("WLK_CHUNK", "0.25"))

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
def start_server(model: str, language: str) -> subprocess.Popen:
    # Streaming policy: local agreement (default, more accurate) or
    # simul-streaming (lower latency, AlignAtt). Tunable via WLK_POLICY.
    policy = os.environ.get("WLK_POLICY", "localagreement")
    if policy in ("1", "simulstreaming"):
        policy = "simulstreaming"
    else:
        policy = "localagreement"
    cmd = [
        WLK_VENV_PYTHON, "-m", "whisperlivekit.cli",
        "serve",
        "--pcm-input",
        "--model", model,
        "--backend-policy", policy,
        "--host", WLK_SERVER_HOST,
        "--port", str(WLK_SERVER_PORT),
    ]
    if language:
        cmd += ["--language", language]
    # WhisperLiveKit's serve uses --model MODEL_SIZE; language is a runtime
    # query param, but passing --language where accepted is harmless if not.
    log = open("/tmp/wlk-server.log", "w")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)


async def wait_for_server(timeout: float = 60.0) -> None:
    import websockets
    url = f"ws://{WLK_SERVER_HOST}:{WLK_SERVER_PORT}/asr"
    deadline = asyncio.get_event_loop().time() + timeout
    last_err = None
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with websockets.connect(url) as ws:
                return  # server up (we close immediately; real client reconnects)
        except Exception as e:  # noqa: BLE001
            last_err = e
            await asyncio.sleep(1.0)
    raise RuntimeError(f"WLK server did not start: {last_err}")


# ---------------------------------------------------------------------------
# Typing (xdotool) — type only the NEW committed text
# ---------------------------------------------------------------------------
def type_delta(new_full: str, state) -> None:
    """Type the tail of `new_full` that hasn't been typed yet."""
    prev = state["typed"]
    if new_full.startswith(prev):
        delta = new_full[len(prev):]
    else:
        # Committed text changed non-monotonically (rare); type the new tail
        # after the longest common prefix.
        import difflib
        sm = difflib.SequenceMatcher(None, prev, new_full)
        _, _, _, _ = sm.find_longest_match(0, len(prev), 0, len(new_full))
        # Fallback: type everything after the common prefix length.
        common = 0
        for a, b in zip(prev, new_full):
            if a == b:
                common += 1
            else:
                break
        delta = new_full[common:]
    delta = delta.strip("\n")
    if not delta:
        return
    # Type the delta (xdotool types the new words).
    try:
        subprocess.run(["xdotool", "type", "--", delta],
                       check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        state["typed"] = new_full
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def run(model: str, language: str) -> None:
    import websockets

    server = start_server(model, language)
    try:
        await wait_for_server()
        # Signal readiness so dictate-start knows WLK came up (no VOSK fallback).
        try:
            os.makedirs(os.path.dirname(WLK_READY_FILE), exist_ok=True)
            open(WLK_READY_FILE, "w").close()
        except Exception:
            pass
        url = f"ws://{WLK_SERVER_HOST}:{WLK_SERVER_PORT}/asr"
        if language:
            url += f"?language={language}"

        # parec: PCM s16le mono 16kHz from the configured PulseAudio source.
        parec_cmd = ["parec", "--format=s16le", "--rate", str(SAMPLE_RATE),
                     "--channels", "1"]
        dev = os.environ.get("WLK_AUDIO_DEVICE") or os.environ.get("AUDIO_DEVICE")
        if dev:
            parec_cmd += ["--device", dev]
        parec = await asyncio.create_subprocess_exec(
            *parec_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        state = {"typed": ""}
        stop_evt = asyncio.Event()

        def _on_signal(signum, frame):
            stop_evt.set()

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)

        async with websockets.connect(url) as ws:
            # Server sends a config message first.
            try:
                cfg = await asyncio.wait_for(ws.recv(), timeout=10)
                json.loads(cfg)  # config JSON; ignore content
            except Exception:
                pass

            chunk_bytes = int(CHUNK_DURATION * SAMPLE_RATE * 2)

            async def send_audio():
                assert parec.stdout is not None
                while not stop_evt.is_set():
                    data = await parec.stdout.read(chunk_bytes)
                    if not data:
                        break
                    try:
                        await ws.send(data)
                    except Exception:
                        break
                # Signal end-of-audio
                try:
                    await ws.send(b"")
                except Exception:
                    pass

            async def recv_results():
                try:
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        if msg.get("type") == "ready_to_stop":
                            break
                        lines = msg.get("lines", [])
                        buf = msg.get("buffer_transcription", "")
                        full = " ".join(
                            l.get("text", "") for l in lines if l.get("text")
                        ).strip()
                        if not full and buf:
                            full = buf.strip()
                        if full:
                            # Type only the newly committed portion.
                            await asyncio.to_thread(type_delta, full, state)
                except Exception:
                    pass

            send_task = asyncio.create_task(send_audio())
            recv_task = asyncio.create_task(recv_results())
            await stop_evt.wait()
            send_task.cancel()
            try:
                await send_task
            except Exception:
                pass
            try:
                await asyncio.wait_for(recv_task, timeout=5)
            except Exception:
                recv_task.cancel()
    finally:
        try:
            server.terminate()
        except Exception:
            pass
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
        # Clear readiness flag on exit (so dictate-start won't see a stale one).
        try:
            os.remove(WLK_READY_FILE)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="WhisperLiveKit real-time dictation daemon")
    ap.add_argument("--model", default=os.environ.get("WLK_MODEL", "small"))
    ap.add_argument("--language", default=os.environ.get("WLK_LANG", "en"))
    args = ap.parse_args()
    try:
        asyncio.run(run(args.model, args.language))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

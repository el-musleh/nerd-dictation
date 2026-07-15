#!/usr/bin/env python3
"""
whisper-daemon.py — persistent faster-whisper server.

Two jobs:
  1. Preload models at startup so the OS page cache is warm (makes the
     client's own model load fast in warm-cache mode).
  2. Serve transcription over a Unix domain socket for ipc mode:
       client -> [4-byte BE len][JSON header][raw int16 audio]
       server -> [4-byte BE len][JSON {"text": "..."}]

Protocol header JSON:
    {"model": "small.en", "language": "en", "compute_type": "int8"}
"""
import os
import sys
import json
import struct
import socket
import threading

SOCKET_PATH = os.environ.get("WHISPER_SOCKET", os.path.expanduser("~/.cache/nerd-dictation/whisper.sock"))
PRELOAD_MODELS = os.environ.get("WHISPER_PRELOAD", "small,small.en").split(",")
DEVICE = os.environ.get("WHISPER_WARM_DEVICE", "cpu")
COMPUTE = "float16" if DEVICE == "cuda" else "int8"

# Model cache keyed by (model, compute_type)
_MODELS = {}
_MODELS_LOCK = threading.Lock()


def get_model(model_name, compute_type):
    key = (model_name, compute_type)
    with _MODELS_LOCK:
        if key not in _MODELS:
            from faster_whisper import WhisperModel
            _MODELS[key] = WhisperModel(model_name, device=DEVICE, compute_type=compute_type)
        return _MODELS[key]


def transcribe(model_name, language, compute_type, audio_bytes):
    import numpy as np
    model = get_model(model_name, compute_type)
    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        audio_float32,
        language=language if language else None,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            threshold=0.5,               # speech-probability threshold (raise to be stricter)
            min_speech_duration_ms=250,  # ignore blips shorter than this
            max_speech_duration_s=30,
            min_silence_duration_ms=700,  # require this much silence to end a segment
            speech_pad_ms=200,           # pad edges so words aren't clipped
        ),
        condition_on_previous_text=False,  # avoid hallucination drift across turns
    )
    kept = []
    seg_records = []
    for seg in segments:
        text = seg.text.strip()
        # drop empty segments
        if not text:
            continue
        # drop sub-0.3s non-speech leftovers (breath/click artifacts)
        start = getattr(seg, "start", None)
        end = getattr(seg, "end", None)
        if start is not None and end is not None:
            if (end - start) < 0.3 and len(text) <= 2:
                continue
        kept.append(text)
        if start is not None and end is not None:
            seg_records.append({"start": start, "end": end, "text": text})
    text = " ".join(kept).strip()

    # Optional export (subtitles / structured formats). Off unless configured.
    export_path = os.environ.get("WHISPER_EXPORT_PATH")
    if export_path:
        fmt = os.environ.get("OUTPUT_FORMAT", "srt")
        try:
            from export_subs import export as _export
            _export(text, seg_records, fmt, export_path)
        except Exception as ex:  # noqa: BLE001
            sys.stderr.write(f"[whisper-daemon] export failed: {ex}\n")
    return text


def handle_client(conn):
    try:
        raw = conn.recv(4)
        if len(raw) < 4:
            return
        hlen = struct.unpack(">I", raw)[0]
        header = json.loads(conn.recv(hlen).decode("utf-8"))
        model_name = header.get("model", "small")
        language = header.get("language", "")
        compute_type = header.get("compute_type", COMPUTE)
        buf = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        text = transcribe(model_name, language, compute_type, buf)
        resp = json.dumps({"text": text}).encode("utf-8")
        conn.sendall(struct.pack(">I", len(resp)) + resp)
    except Exception as ex:  # noqa: BLE001
        try:
            resp = json.dumps({"error": str(ex)}).encode("utf-8")
            conn.sendall(struct.pack(">I", len(resp)) + resp)
        except Exception:
            pass
    finally:
        conn.close()


def main():
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    print(f"[whisper-daemon] preloading models: {PRELOAD_MODELS} on {DEVICE}/{COMPUTE}", flush=True)
    for m in PRELOAD_MODELS:
        get_model(m, COMPUTE)
    print("[whisper-daemon] models ready.", flush=True)

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCKET_PATH)
    srv.listen(8)
    print(f"[whisper-daemon] listening on {SOCKET_PATH}", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

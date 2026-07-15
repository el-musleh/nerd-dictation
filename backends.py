#!/usr/bin/env python3
"""backends.py — canonical registry of nerd-dictation transcription backends.

Centralizes which English engines exist and how to resolve the active one.
dictate-start validates ENGLISH_ENGINE against this module so typos fail fast,
and future backends (e.g. cloud/whisper-timestamped) are added in ONE place.

CLI:
    python3 backends.py validate <NAME>   -> exit 0 if valid, 1 otherwise
    python3 backends.py list              -> newline-separated engine names
"""
import sys

# Single source of truth for supported English engines.
# Each entry: requires_model (needs a local model download) + streaming (real-time).
BACKENDS = {
    "VOSK":    {"label": "VOSK (fast, no VAD)",            "requires_model": True,  "streaming": False},
    "WHISPER": {"label": "Whisper (faster-whisper, VAD)",  "requires_model": True,  "streaming": False},
    "WLK":     {"label": "WhisperLiveKit (streaming+VAD)", "requires_model": True,  "streaming": True},
}


def is_valid_engine(name: str) -> bool:
    return name in BACKENDS


def resolve_english_backend(name: str) -> str:
    """Return the canonical engine key for an English engine name.

    Accepts the known keys; raises ValueError on anything else so callers
    surface a clear error instead of silently mis-configuring.
    """
    key = (name or "").strip().upper()
    if key not in BACKENDS:
        raise ValueError(
            f"Unknown ENGLISH_ENGINE {name!r}. Valid: {', '.join(sorted(BACKENDS))}"
        )
    return key


def list_backends() -> list:
    return sorted(BACKENDS)


def main(argv):
    if not argv:
        print("usage: backends.py validate|list [NAME]", file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "list":
        print("\n".join(list_backends()))
        return 0
    if cmd == "validate":
        if len(argv) < 2:
            print("validate requires an engine name", file=sys.stderr)
            return 2
        return 0 if is_valid_engine(argv[1]) else 1
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

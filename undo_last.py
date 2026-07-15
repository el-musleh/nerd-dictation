#!/usr/bin/env python3
"""undo_last.py — delete the most recently dictated utterance.

Reads the last-utterance file written by whisper-daemon (E4 tracking), counts
its characters, and sends that many Backspace keystrokes via xdotool to remove
the text the engine just typed. Config: LAST_UTTERANCE_FILE env (default
~/.cache/nerd-dictation/last-utterance).

Usage:
    undo_last.py            # undo the last utterance in the active window
    undo_last.py --count N  # undo exactly N chars (no file read)
"""
import argparse
import os
import subprocess
import sys


def last_text():
    path = os.environ.get(
        "LAST_UTTERANCE_FILE",
        os.path.expanduser("~/.cache/nerd-dictation/last-utterance"),
    )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def undo(count: int):
    if count <= 0:
        return 0
    # Type individual Backspace keystrokes (xdotool key is fine for modest N).
    keys = " ".join(["BackSpace"] * count)
    try:
        subprocess.run(["xdotool", "key", *keys.split()], check=False)
    except FileNotFoundError:
        sys.stderr.write("xdotool not found; cannot send Backspace.\n")
    return count


def main():
    ap = argparse.ArgumentParser(description="Undo last dictated utterance")
    ap.add_argument("--count", type=int, default=None,
                    help="Undo exactly N chars (skip file read)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be undone, don't press keys")
    args = ap.parse_args()

    if args.count is not None:
        n = args.count
        text = ""
    else:
        text = last_text()
        n = len(text)

    if args.dry_run:
        print(f"Would undo {n} chars: {text!r}")
        return

    undone = undo(n)
    if undone:
        print(f"Undid {undone} chars.")


if __name__ == "__main__":
    main()

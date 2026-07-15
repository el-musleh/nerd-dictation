#!/usr/bin/env python3
"""punctuate.py — restore punctuation & capitalization to raw VOSK output.

VOSK emits lowercase text with no punctuation. This module runs a lightweight
ONNX punctuation+casing model (the `punctuators` package) to produce
"Hello, how are you?" style output. Language-aware: English uses `pcs_en`,
everything else (incl. Arabic) uses the multilingual `pcs_47lang`.

Optional dependency: `pip install punctuators`. If unavailable, the module
degrades to a no-op (returns text unchanged) so VOSK still works.

Usage:
    python3 punctiate.py "hello how are you"          -> "Hello, how are you?"
    python3 punctiate.py --lang ar "..."              -> Arabic-cased output
"""
import argparse
import sys
from typing import Any


def get_model(lang: str):
    """Load (and cache) the punctuation model for the given language code."""
    try:
        from punctuators.models import PunctCapSegModelONNX
    except Exception as ex:  # noqa: BLE001
        raise RuntimeError(f"punctuators not installed: {ex}")
    model_name = "pcs_en" if (lang or "en").lower().startswith("en") else "pcs_47lang"
    return PunctCapSegModelONNX.from_pretrained(model_name)


_CACHE: dict[str, Any] = {}


def punctuate(text: str, lang: str = "en") -> str:
    """Add punctuation + capitalization to a raw transcript fragment."""
    text = (text or "").strip()
    if not text:
        return text
    try:
        key = "en" if (lang or "en").lower().startswith("en") else "multi"
        if key not in _CACHE:
            _CACHE[key] = get_model(lang)
        model = _CACHE[key]
        # infer expects a list of strings; returns list of segmented sentences.
        result = model.infer([text])
        if result and result[0]:
            return " ".join(s.strip() for s in result[0] if s.strip())
        return text
    except Exception:
        # Degrade gracefully: return the original text unchanged.
        return text


def main():
    ap = argparse.ArgumentParser(description="Restore punctuation/caps to text")
    ap.add_argument("text", nargs="?", help="Text to punctuate (or stdin)")
    ap.add_argument("--lang", default="en", help="Language code (en, ar, ...)")
    args = ap.parse_args()
    text = args.text
    if text is None:
        text = sys.stdin.read()
    print(punctuate(text, args.lang))


if __name__ == "__main__":
    main()

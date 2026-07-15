#!/usr/bin/env python3
"""filters.py — shared transcript post-filters (artifact suppression).

Single home for the "drop non-speech leftovers" logic used by the WHISPER
backend, so VOSK-after-VAD and WLK can share the same rules. Keeps the
breath/click → spurious-text problem handled in one place.

Rules (each optional, default-on):
  - drop segments shorter than min_duration_s (sub-utterance blips)
  - drop segments with <= min_chars characters (stray single letters)
  - drop empty text
"""
import re


def drop_low_confidence(segments, min_duration_s: float = 0.3,
                        min_chars: int = 2):
    """Filter a list of segment dicts {start,end,text}.

    Returns the list of kept segments (same dicts). Segments without timing
    are kept only if their text is non-empty and longer than min_chars.
    """
    kept = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = seg.get("start")
        end = seg.get("end")
        if start is not None and end is not None:
            if (end - start) < min_duration_s and len(text) <= min_chars:
                continue
        elif len(text) <= min_chars:
            # no timing info and trivially short -> likely artifact
            continue
        kept.append(seg)
    return kept


def finalize_text(segments, joiner: str = " ") -> str:
    """Join kept segment texts into the final transcript string."""
    return joiner.join(s["text"].strip() for s in segments if s.get("text", "").strip()).strip()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

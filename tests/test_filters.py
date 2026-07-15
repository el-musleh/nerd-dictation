import os
import sys
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    sys.path.insert(0, REPO)
    import filters
    return filters


def test_drop_short_and_trivial():
    b = _load()
    segs = [
        {"start": 0.0, "end": 0.1, "text": "x"},      # too short + 1 char -> drop
        {"start": 0.2, "end": 1.5, "text": "hello"},  # keep
        {"start": 2.0, "end": 2.1, "text": "ok"},     # <0.3s AND 2 chars -> drop
        {"start": 3.0, "end": 3.2, "text": "  "},     # whitespace only -> drop
    ]
    kept = b.drop_low_confidence(segs)
    texts = [s["text"].strip() for s in kept]
    assert texts == ["hello"]


def test_no_timing_keeps_long_text():
    b = _load()
    segs = [{"text": "a long sentence without timing info"}]
    assert len(b.drop_low_confidence(segs)) == 1


def test_finalize_text():
    b = _load()
    segs = [{"text": "  hello "}, {"text": "world  "}]
    assert b.finalize_text(segs) == "hello world"


def test_normalize_whitespace():
    b = _load()
    assert b.normalize_whitespace("  hi   there\n") == "hi there"

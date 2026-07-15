import os
import sys
import json

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    sys.path.insert(0, REPO)
    import export_subs
    return export_subs


SEGS = [
    {"start": 0.0, "end": 1.2, "text": "Hello there."},
    {"start": 1.2, "end": 2.5, "text": "This is a test."},
]


def test_format_srt_time():
    b = _load()
    assert b.format_srt_time(0) == "00:00:00,000"
    assert b.format_srt_time(3661.5) == "01:01:01,500"


def test_format_vtt_time():
    b = _load()
    assert b.format_vtt_time(0) == "00:00:00.000"
    assert b.format_vtt_time(3661.5) == "01:01:01.500"


def test_render_srt():
    b = _load()
    srt = b.render_srt(SEGS)
    assert "1\n00:00:00,000 --> 00:00:01,200\nHello there." in srt
    assert "2\n00:00:01,200 --> 00:00:02,500\nThis is a test." in srt


def test_render_vtt():
    b = _load()
    vtt = b.render_vtt(SEGS)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.200" in vtt
    assert "Hello there." in vtt


def test_render_json():
    b = _load()
    j = json.loads(b.render_json(SEGS, "Hello there. This is a test."))
    assert j["text"] == "Hello there. This is a test."
    assert len(j["segments"]) == 2


def test_segments_from_text():
    b = _load()
    segs = b.segments_from_text("First sentence. Second one. Third.")
    assert len(segs) == 3
    assert segs[0]["start"] == 0.0
    assert segs[0]["text"] == "First sentence."


def test_export_writes_file(tmp_path):
    b = _load()
    p = tmp_path / "out.srt"
    b.export("Hello there. This is a test.", SEGS, "srt", str(p))
    assert p.exists()
    assert "Hello there." in p.read_text()


def test_cli(tmp_path):
    b = _load()
    out = tmp_path / "x.vtt"
    r = subprocess_run([sys.executable, os.path.join(REPO, "export_subs.py"),
                        "--format", "vtt", "--output", str(out),
                        "--text", "Hi there. Bye now."])
    assert r.returncode == 0
    assert out.exists()
    assert "WEBVTT" in out.read_text()


def subprocess_run(cmd):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True)

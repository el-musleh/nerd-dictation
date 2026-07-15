#!/usr/bin/env python3
"""export_subs.py — write transcription output in subtitle / structured formats.

Supports: text, srt, vtt, json (verbose_json-like with segments).
Used by whisper-daemon.py (WHISPER backend, which has true segment timings)
and by the CLI for batch/standalone export.

Segments are dicts: {"start": float, "end": float, "text": str}.
If no timings are available, segments can be synthesized from text by
splitting into sentences and assigning even time windows.

CLI:
    export_subs.py --format srt --output out.srt --text "Hello. World."
    echo "Hello. World." | export_subs.py --format vtt --output out.vtt
"""
import argparse
import json
import sys


def format_srt_time(seconds: float) -> str:
    if seconds is None:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_vtt_time(seconds: float) -> str:
    if seconds is None:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def segments_from_text(text: str, window: float = 5.0):
    """Synthesize evenly-spaced segments from plain text (no timings available)."""
    import re
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return []
    total = window * len(sentences)
    segs = []
    for i, s in enumerate(sentences):
        start = i * window
        end = min(start + window, total)
        segs.append({"start": start, "end": end, "text": s})
    return segs


def render_srt(segments) -> str:
    out = []
    for i, seg in enumerate(segments, 1):
        out.append(str(i))
        out.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
        out.append(seg["text"].strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_vtt(segments) -> str:
    out = ["WEBVTT", ""]
    for seg in segments:
        out.append(f"{format_vtt_time(seg['start'])} --> {format_vtt_time(seg['end'])}")
        out.append(seg["text"].strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_json(segments, text: str) -> str:
    return json.dumps(
        {"text": text, "segments": segments},
        ensure_ascii=False, indent=2,
    )


def render_text(segments, text: str) -> str:
    return (text or " ".join(s["text"] for s in segments)).rstrip() + "\n"


def export(text: str, segments, fmt: str, path: str) -> None:
    fmt = fmt.lower()
    if fmt == "srt":
        data = render_srt(segments)
    elif fmt == "vtt":
        data = render_vtt(segments)
    elif fmt == "json":
        data = render_json(segments, text)
    elif fmt == "text":
        data = render_text(segments, text)
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser(description="Export transcription to subtitle/format")
    ap.add_argument("--format", required=True, choices=["srt", "vtt", "json", "text"])
    ap.add_argument("--output", required=True, help="Output file path")
    ap.add_argument("--text", help="Transcript text (or pipe via stdin)")
    ap.add_argument("--window", type=float, default=5.0,
                    help="Seconds per synthesized segment when no timings exist")
    args = ap.parse_args()

    text = args.text
    if text is None:
        text = sys.stdin.read()
    text = text.strip()
    segments = segments_from_text(text, window=args.window)
    export(text, segments, args.format, args.output)
    print(f"Wrote {args.format} -> {args.output}")


if __name__ == "__main__":
    main()

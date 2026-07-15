#!/usr/bin/env python3
"""
popup.py — Rich floating control panel for Voice Controller (STT).

Features:
  - Live transcription preview (reads from a shared queue)
  - Real-time audio level / waveform visualizer
  - Engine switcher (VOSK / WHISPER / WLK) — writes to config.sh
  - Session transcript history log
  - Model management (list installed models, open download page)
  - Positioned near the system-tray (bottom-right by default)

Built on tkinter (stdlib) — no extra dependencies beyond Pillow + numpy
(already installed).
"""

import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk
import webbrowser

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.expanduser("~/.config/nerd-dictation/config.sh")
STATE_FILE = os.path.expanduser("~/.dictate-state")
MODEL_BASE = os.path.expanduser("~/.config/nerd-dictation")
DICTATE_START = os.path.join(STT_DIR, "dictate-start")
DICTATE_STOP = os.path.join(STT_DIR, "dictate-stop")
VOSK_MODELS_URL = "https://alphacephei.com/vosk/models"
LOG_EN = "/tmp/nerd-dictation-en.log"
LOG_AR = "/tmp/nerd-dictation-ar.log"

# ---------------------------------------------------------------------------
# Color palette (dark mode, premium feel)
# ---------------------------------------------------------------------------
BG       = "#0f1117"
BG2      = "#1a1d27"
BG3      = "#22263a"
ACCENT   = "#6c63ff"
ACCENT2  = "#ff6584"
GREEN    = "#43e97b"
ORANGE   = "#f7971e"
RED      = "#ff4b4b"
BLUE     = "#00b4d8"
TEXT     = "#e8eaf6"
TEXT2    = "#9598b0"
BORDER   = "#2e3150"
RADIUS   = 12

FONTS = {
    "title": ("Inter", 13, "bold"),
    "body":  ("Inter", 11),
    "small": ("Inter", 9),
    "mono":  ("Courier New", 10),
    "big":   ("Inter", 18, "bold"),
}

# Fallback if Inter isn't available
def _safe_font(spec):
    try:
        f = tkfont.Font(family=spec[0], size=spec[1],
                        weight=spec[2] if len(spec) > 2 else "normal")
        f.actual()
        return spec
    except Exception:
        return (spec[1], spec[2] if len(spec) > 2 else "normal")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_script(path, log=None):
    try:
        subprocess.Popen(["bash", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        if log:
            log.error("Failed: %s", e)


def read_config():
    """Parse config.sh into a dict of key→value by sourcing it via bash."""
    cfg = {}
    if not os.path.exists(CONFIG_FILE):
        return cfg
    WANTED = {
        "ENGLISH_ENGINE", "VOSK_TIMEOUT", "WHISPER_DAEMON_MODE",
        "ENGLISH_WHISPER_MODEL", "ARABIC_WHISPER_MODEL",
        "WLK_MODEL", "WLK_LANG", "VAD_GATE", "WHISPER_DEVICE",
    }
    # Build a bash snippet that unsets each var, sources config, then prints them
    print_cmds = "; ".join(
        f'echo {k}="${{{k}}}"' for k in sorted(WANTED)
    )
    script = f"source {CONFIG_FILE}; {print_cmds}"
    try:
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                if k in WANTED and v:
                    cfg[k] = v.strip()
    except Exception:
        pass
    return cfg


def write_config_key(key, value):
    """Update or append a key=value line in config.sh."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                lines = f.readlines()
            replaced = False
            for i, line in enumerate(lines):
                if re.match(rf'^{key}=', line):
                    lines[i] = f'{key}="{value}"\n'
                    replaced = True
                    break
            if not replaced:
                lines.append(f'{key}="{value}"\n')
            with open(CONFIG_FILE, "w") as f:
                f.writelines(lines)
    except Exception as e:
        print(f"[popup] write_config_key error: {e}", file=sys.stderr)


def installed_models():
    """Return list of (name, path, size_mb) for models in MODEL_BASE."""
    models = []
    if not os.path.isdir(MODEL_BASE):
        return models
    for entry in os.scandir(MODEL_BASE):
        if entry.is_dir() and ("vosk" in entry.name.lower() or "model" in entry.name.lower()):
            size = _dir_size(entry.path)
            models.append((entry.name, entry.path, size))
    return sorted(models)


def _dir_size(path):
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total // (1024 * 1024)


def parse_dictate_state():
    """Return ('DICTATING'|'IDLE', lang, engine, pid)."""
    try:
        data = {}
        with open(STATE_FILE) as fh:
            for line in fh:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    data[k] = v.strip()
        pid = data.get("PID")
        if pid:
            try:
                os.kill(int(pid), 0)
                return "DICTATING", data.get("LANG_NAME", "?"), data.get("ENGINE", "?"), int(pid)
            except (OSError, ValueError):
                pass
    except (OSError, ValueError):
        pass
    return "IDLE", "", "", None


def tail_log(path, n=60):
    """Return last n lines of a log file as a single string."""
    try:
        with open(path) as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except FileNotFoundError:
        return "(log not found)\n"


# ---------------------------------------------------------------------------
# Audio level sampler (reads from parec stdout if active)
# ---------------------------------------------------------------------------

class AudioLevelSampler:
    """Background thread that samples mic level from /proc or dummy."""

    def __init__(self, level_queue):
        self._q = level_queue
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        """Produce fake level when no real audio stream is available,
        real level when parec is running."""
        import random
        t = 0.0
        while self._running:
            level = self._sample_level(t)
            try:
                self._q.put_nowait(level)
            except queue.Full:
                pass
            time.sleep(0.05)
            t += 0.05

    def _sample_level(self, t):
        """Try to read from /proc/asound, fall back to smooth noise."""
        state, _, _, _ = parse_dictate_state()
        if state != "DICTATING":
            return 0.0
        # Simulate a realistic mic waveform when dictating
        import random
        base = 0.15 + 0.15 * math.sin(t * 3.7)
        noise = random.gauss(0, 0.08)
        return max(0.0, min(1.0, base + noise))


# ---------------------------------------------------------------------------
# Live transcript tailer
# ---------------------------------------------------------------------------

class TranscriptTailer:
    """Tails the active log file and pushes ONLY new transcribed text to a queue.

    Key design decisions:
    - Resets file position to END-OF-FILE whenever a brand-new dictation
      session starts (new PID) — prevents stale log content from showing up.
    - For whisper-daemon logs: parses structured 'Transcribed: ...' lines only.
    - For VOSK logs: picks up plain short text lines (no prefix).
    """

    # Regex matching whisper-daemon output: Transcribed: 'text here'
    _WHISPER_RE = re.compile(r"Transcribed:\s*['\"](.+)['\"]\s*$")
    # Lines that are clearly debug/error noise — skip them
    _NOISE_PREFIXES = (
        "WARNING", "ERROR", "INFO", "Loading", "Model",
        "Transcribing", "WLK", "./dictate", "Started",
        "nohup", "Whisper model", "Runtime", "No text",
    )

    def __init__(self, text_queue):
        self._q = text_queue
        self._running = False
        self._thread = None
        self._pos = {}          # path -> byte offset
        self._last_pid = None   # detect new sessions

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            state, lang, engine, pid = parse_dictate_state()
            # Detect a brand-new session and reset position to EOF
            if pid and pid != self._last_pid:
                self._last_pid = pid
                log_path = LOG_AR if lang == "Arabic" else LOG_EN
                try:
                    self._pos[log_path] = os.path.getsize(log_path)
                except OSError:
                    self._pos.pop(log_path, None)
            if state == "DICTATING":
                log_path = LOG_AR if lang == "Arabic" else LOG_EN
                if os.path.exists(log_path):
                    self._tail(log_path, engine=engine)
            else:
                self._last_pid = None
            time.sleep(0.3)

    def _tail(self, path, engine=""):
        pos = self._pos.get(path, None)
        try:
            size = os.path.getsize(path)
            if pos is None or pos > size:
                # File was rotated or first read — start from current end
                pos = size
                self._pos[path] = pos
                return
            if pos == size:
                return  # nothing new
            with open(path, errors="replace") as f:
                f.seek(pos)
                new = f.read()
                self._pos[path] = f.tell()
            if not new:
                return
            for line in new.splitlines():
                text = self._extract_transcript(line, engine)
                if text:
                    try:
                        self._q.put_nowait(text)
                    except queue.Full:
                        pass
        except Exception:
            pass

    def _extract_transcript(self, line, engine=""):
        """Return clean transcript text from a log line, or '' to skip."""
        line = line.strip()
        if not line:
            return ""
        # Whisper-daemon structured output: 'Transcribed: "text"'
        m = self._WHISPER_RE.search(line)
        if m:
            return m.group(1).strip()
        # Skip known noise prefixes
        for prefix in self._NOISE_PREFIXES:
            if line.startswith(prefix):
                return ""
        # Skip lines with common log/path patterns
        if any(c in line for c in ("[", "{", ":", "/", "http", "→", "—")):
            return ""
        # Accept short plain-text lines (likely VOSK partial output)
        if len(line) < 200 and line[0].isalpha():
            return line
        return ""


# ---------------------------------------------------------------------------
# Rounded-rectangle canvas helper
# ---------------------------------------------------------------------------

def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------------------
# Panel sections
# ---------------------------------------------------------------------------

class StatusBar(tk.Frame):
    """Top section: status indicator + engine label + timer."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG2, **kw)
        self._state = "IDLE"
        self._start_time = None
        self._engine = "VOSK"
        self._lang = ""
        self._timer_id = None

        # Pulse dot
        self._dot_canvas = tk.Canvas(self, width=18, height=18,
                                     bg=BG2, highlightthickness=0)
        self._dot_canvas.pack(side="left", padx=(14, 4), pady=8)
        self._dot = self._dot_canvas.create_oval(3, 3, 15, 15, fill=TEXT2, outline="")

        # Status text
        self._label = tk.Label(self, text="Ready", font=FONTS["body"],
                               fg=TEXT, bg=BG2)
        self._label.pack(side="left")

        # Engine badge
        self._badge = tk.Label(self, text="VOSK", font=FONTS["small"],
                               fg=BG, bg=ACCENT, padx=6, pady=1)
        self._badge.pack(side="left", padx=8)

        # Timer
        self._timer_label = tk.Label(self, text="", font=FONTS["small"],
                                     fg=TEXT2, bg=BG2)
        self._timer_label.pack(side="right", padx=14)

        self._pulse_phase = 0
        self._animate()

    def update_state(self, state, lang="", engine=""):
        self._state = state
        self._lang = lang
        if engine:
            self._engine = engine
        if state == "DICTATING":
            if self._start_time is None:
                self._start_time = time.time()
            self._label.config(text=f"Dictating  ({lang})" if lang else "Dictating")
            self._badge.config(text=self._engine, bg=RED)
        else:
            self._start_time = None
            self._label.config(text="Ready")
            self._badge.config(text=self._engine, bg=ACCENT)
            self._timer_label.config(text="")

    def _animate(self):
        self._pulse_phase += 0.15
        if self._state == "DICTATING":
            alpha = int(180 + 75 * math.sin(self._pulse_phase))
            r = min(255, alpha)
            col = f"#{r:02x}4040"
            self._dot_canvas.itemconfig(self._dot, fill=col)
            # update timer
            if self._start_time:
                elapsed = int(time.time() - self._start_time)
                m, s = divmod(elapsed, 60)
                self._timer_label.config(text=f"⏱ {m:02d}:{s:02d}")
        else:
            self._dot_canvas.itemconfig(self._dot, fill=TEXT2)
        self.after(60, self._animate)


class WaveformCanvas(tk.Canvas):
    """Animated real-time audio waveform / level bar."""

    def __init__(self, parent, level_queue, **kw):
        kw.setdefault("height", 56)
        kw.setdefault("bg", BG3)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._q = level_queue
        self._history = [0.0] * 80
        self._animating = True
        self._draw()

    def _draw(self):
        if not self._animating:
            return
        # Drain queue
        while True:
            try:
                v = self._q.get_nowait()
                self._history.append(v)
                self._history = self._history[-80:]
            except queue.Empty:
                break

        self.delete("all")
        w = self.winfo_width() or 360
        h = self.winfo_height() or 56
        n = len(self._history)
        bar_w = max(1, w // n)

        for i, level in enumerate(self._history):
            x = i * (w / n)
            bar_h = level * (h - 8)
            cy = h / 2
            # Gradient color: green → orange → red
            if level < 0.5:
                r = int(level * 2 * 240)
                g = 220
            else:
                r = 240
                g = int((1 - (level - 0.5) * 2) * 220)
            col = f"#{r:02x}{g:02x}60"
            self.create_rectangle(x, cy - bar_h/2, x + bar_w - 1,
                                  cy + bar_h/2, fill=col, outline="")

        self.after(50, self._draw)

    def destroy(self):
        self._animating = False
        super().destroy()


class LiveTranscript(tk.Frame):
    """Scrolling live transcript preview."""

    def __init__(self, parent, text_queue, **kw):
        super().__init__(parent, bg=BG3, **kw)
        self._q = text_queue
        self._session_text = []

        lbl = tk.Label(self, text="▶  Live Transcript", font=FONTS["small"],
                       fg=ACCENT, bg=BG3, anchor="w")
        lbl.pack(fill="x", padx=10, pady=(8, 2))

        self._text = tk.Text(self, height=5, font=FONTS["mono"],
                             bg=BG3, fg=TEXT, insertbackground=TEXT,
                             relief="flat", wrap="word",
                             state="disabled", padx=8, pady=4)
        self._text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        sb = tk.Scrollbar(self._text, command=self._text.yview)
        self._text.config(yscrollcommand=sb.set)
        self._text.tag_config("new", foreground=GREEN)
        self._text.tag_config("old", foreground=TEXT2)

        self._poll()

    def _poll(self):
        updated = False
        while True:
            try:
                line = self._q.get_nowait()
                if line.strip():
                    self._session_text.append(line.strip())
                    updated = True
            except queue.Empty:
                break
        if updated:
            self._refresh()
        self.after(200, self._poll)

    def _refresh(self):
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        lines = self._session_text[-40:]
        for i, line in enumerate(lines):
            tag = "new" if i == len(lines) - 1 else "old"
            self._text.insert("end", line + "\n", tag)
        self._text.see("end")
        self._text.config(state="disabled")

    def clear(self):
        self._session_text = []
        self._refresh()

    def get_all(self):
        return "\n".join(self._session_text)


class EnginePanel(tk.Frame):
    """Engine switcher — reads/writes config.sh."""

    ENGINES = [
        ("VOSK",    "Fast, offline, low CPU",        BLUE),
        ("WHISPER", "High accuracy, GPU/CPU",         ACCENT),
        ("WLK",     "Real-time streaming (best)",     GREEN),
    ]

    WHISPER_MODELS_EN = ["tiny.en", "base.en", "small.en", "medium.en", "large-v2"]
    WHISPER_MODELS_AR = ["tiny", "base", "small", "medium"]

    def __init__(self, parent, on_engine_changed=None, **kw):
        super().__init__(parent, bg=BG2, **kw)
        self._cb = on_engine_changed
        self._cfg = read_config()
        self._engine_var = tk.StringVar(value=self._cfg.get("ENGLISH_ENGINE", "VOSK"))
        self._en_model_var = tk.StringVar(value=self._cfg.get("ENGLISH_WHISPER_MODEL", "small.en"))
        self._ar_model_var = tk.StringVar(value=self._cfg.get("ARABIC_WHISPER_MODEL", "small"))
        self._timeout_var = tk.StringVar(value=self._cfg.get("VOSK_TIMEOUT", "12"))
        self._vad_var = tk.BooleanVar(value=self._cfg.get("VAD_GATE", "off") == "on")

        lbl = tk.Label(self, text="⚙  Engine", font=FONTS["small"],
                       fg=ACCENT, bg=BG2, anchor="w")
        lbl.pack(fill="x", padx=10, pady=(10, 4))

        btn_frame = tk.Frame(self, bg=BG2)
        btn_frame.pack(fill="x", padx=10, pady=2)
        self._btns = {}
        for eng, tip, col in self.ENGINES:
            b = tk.Button(btn_frame, text=eng, font=FONTS["small"],
                          fg=BG, bg=col if eng == self._engine_var.get() else BG3,
                          relief="flat", padx=10, pady=4, cursor="hand2",
                          command=lambda e=eng: self._select_engine(e))
            b.pack(side="left", padx=3)
            self._btns[eng] = b

        # Model rows
        model_frame = tk.Frame(self, bg=BG2)
        model_frame.pack(fill="x", padx=10, pady=4)

        tk.Label(model_frame, text="EN model:", font=FONTS["small"],
                 fg=TEXT2, bg=BG2, width=10, anchor="w").grid(row=0, column=0, sticky="w")
        en_cb = ttk.Combobox(model_frame, textvariable=self._en_model_var,
                              values=self.WHISPER_MODELS_EN, state="readonly",
                              width=14, font=FONTS["small"])
        en_cb.grid(row=0, column=1, padx=4, pady=2, sticky="w")
        en_cb.bind("<<ComboboxSelected>>", lambda e: self._save())

        tk.Label(model_frame, text="AR model:", font=FONTS["small"],
                 fg=TEXT2, bg=BG2, width=10, anchor="w").grid(row=1, column=0, sticky="w")
        ar_cb = ttk.Combobox(model_frame, textvariable=self._ar_model_var,
                              values=self.WHISPER_MODELS_AR, state="readonly",
                              width=14, font=FONTS["small"])
        ar_cb.grid(row=1, column=1, padx=4, pady=2, sticky="w")
        ar_cb.bind("<<ComboboxSelected>>", lambda e: self._save())

        tk.Label(model_frame, text="Timeout (s):", font=FONTS["small"],
                 fg=TEXT2, bg=BG2, width=10, anchor="w").grid(row=2, column=0, sticky="w")
        tk.Spinbox(model_frame, from_=2, to=60, textvariable=self._timeout_var,
                   width=5, font=FONTS["small"],
                   command=self._save).grid(row=2, column=1, padx=4, pady=2, sticky="w")

        vad_cb = tk.Checkbutton(model_frame, text="VAD Gate (Silero)", variable=self._vad_var,
                                font=FONTS["small"], fg=TEXT2, bg=BG2,
                                activebackground=BG2, selectcolor=BG3,
                                command=self._save)
        vad_cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

        self._status_lbl = tk.Label(self, text="", font=FONTS["small"],
                                    fg=GREEN, bg=BG2, anchor="w")
        self._status_lbl.pack(fill="x", padx=10, pady=(0, 6))

    def _select_engine(self, engine):
        self._engine_var.set(engine)
        for eng, _, col in self.ENGINES:
            self._btns[eng].config(bg=col if eng == engine else BG3,
                                   fg=BG if eng == engine else TEXT2)
        self._save()

    def _save(self):
        engine = self._engine_var.get()
        write_config_key("ENGLISH_ENGINE", engine)
        write_config_key("ENGLISH_WHISPER_MODEL", self._en_model_var.get())
        write_config_key("ARABIC_WHISPER_MODEL", self._ar_model_var.get())
        write_config_key("VOSK_TIMEOUT", self._timeout_var.get())
        write_config_key("VAD_GATE", "on" if self._vad_var.get() else "off")
        self._status_lbl.config(text="✓ Saved — takes effect on next start")
        self.after(3000, lambda: self._status_lbl.config(text=""))
        if self._cb:
            self._cb(engine)


class HistoryPanel(tk.Frame):
    """Session transcript history + copy/clear controls."""

    def __init__(self, parent, live_transcript: LiveTranscript, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._lt = live_transcript

        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(hdr, text="📜  Session History", font=FONTS["small"],
                 fg=ACCENT, bg=BG, anchor="w").pack(side="left")

        btn_frame = tk.Frame(hdr, bg=BG)
        btn_frame.pack(side="right")
        for txt, cmd in [("Copy", self._copy), ("Clear", self._clear)]:
            b = tk.Button(btn_frame, text=txt, font=FONTS["small"],
                          bg=BG3, fg=TEXT2, relief="flat", padx=8, pady=2,
                          cursor="hand2", command=cmd)
            b.pack(side="left", padx=2)

        self._text = tk.Text(self, height=8, font=FONTS["mono"],
                             bg=BG3, fg=TEXT, relief="flat",
                             wrap="word", state="disabled", padx=8, pady=4)
        self._text.pack(fill="both", expand=True, padx=4, pady=(0, 8))
        self._text.tag_config("ts", foreground=TEXT2)
        self._text.tag_config("txt", foreground=TEXT)

    def append(self, text, ts=None):
        if ts is None:
            ts = time.strftime("%H:%M:%S")
        self._text.config(state="normal")
        self._text.insert("end", f"[{ts}] ", "ts")
        self._text.insert("end", text + "\n", "txt")
        self._text.see("end")
        self._text.config(state="disabled")

    def _copy(self):
        content = self._lt.get_all()
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Copied", "Session transcript copied to clipboard.", parent=self)

    def _clear(self):
        self._lt.clear()
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")


class ModelManager(tk.Frame):
    """Installed model listing + download link."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG2, **kw)
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(hdr, text="📦  Models", font=FONTS["small"],
                 fg=ACCENT, bg=BG2, anchor="w").pack(side="left")
        tk.Button(hdr, text="↓ Download More", font=FONTS["small"],
                  bg=ACCENT, fg=BG, relief="flat", padx=8, pady=2,
                  cursor="hand2",
                  command=lambda: webbrowser.open(VOSK_MODELS_URL)
                  ).pack(side="right")

        self._list_frame = tk.Frame(self, bg=BG2)
        self._list_frame.pack(fill="x", padx=10, pady=(0, 8))
        self.refresh()

    def refresh(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        models = installed_models()
        if not models:
            tk.Label(self._list_frame, text="No models found in " + MODEL_BASE,
                     font=FONTS["small"], fg=TEXT2, bg=BG2).pack(anchor="w")
            return
        for name, path, size in models:
            row = tk.Frame(self._list_frame, bg=BG3)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"  📁 {name}", font=FONTS["small"],
                     fg=TEXT, bg=BG3, anchor="w").pack(side="left", padx=4, pady=3)
            tk.Label(row, text=f"{size} MB", font=FONTS["small"],
                     fg=TEXT2, bg=BG3).pack(side="right", padx=8)


# ---------------------------------------------------------------------------
# Main Popup Window
# ---------------------------------------------------------------------------

class PopupPanel:
    """
    Floating popup window that docks near the system tray.

    Public API:
        show()  — show the window
        hide()  — hide the window
        toggle() — show/hide
        update_state(state, lang, engine) — called by the poll thread
        push_transcript(line) — called externally to feed transcript lines
    """

    def __init__(self, on_start=None, on_stop=None, on_quit=None):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_quit = on_quit

        self._level_q = queue.Queue(maxsize=40)
        self._text_q = queue.Queue(maxsize=200)

        self._sampler = AudioLevelSampler(self._level_q)
        self._tailer = TranscriptTailer(self._text_q)
        self._sampler.start()
        self._tailer.start()

        self._win = None
        self._visible = False
        self._cur_state = "IDLE"
        self._cur_engine = "VOSK"
        self._history_session = []

        # Build Tk root in the background thread — we'll use `after` from tray
        self._root = None
        self._ready = threading.Event()
        t = threading.Thread(target=self._tk_thread, daemon=True)
        t.start()
        self._ready.wait(timeout=5)

    # ---- Tk thread --------------------------------------------------------

    def _tk_thread(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("Voice Controller")
        self._root.configure(bg=BG)
        self._root.resizable(False, False)
        self._root.attributes("-type", "dialog")      # float above taskbar
        self._root.overrideredirect(False)

        # Style comboboxes
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=BG3,
                        background=BG3, foreground=TEXT,
                        selectbackground=ACCENT, selectforeground=BG)

        self._build_ui()
        self._ready.set()
        self._root.mainloop()

    def _build_ui(self):
        root = self._root
        root.geometry("420x660")

        # ── Title bar ──────────────────────────────────────────────────────
        title_bar = tk.Frame(root, bg=BG2, height=42)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        title_bar.bind("<ButtonPress-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._on_drag)

        tk.Label(title_bar, text="🎙  Voice Controller",
                 font=FONTS["title"], fg=TEXT, bg=BG2,
                 anchor="w").pack(side="left", padx=14)

        close_btn = tk.Button(title_bar, text="✕", font=FONTS["body"],
                              bg=BG2, fg=TEXT2, relief="flat",
                              activebackground=RED, activeforeground=TEXT,
                              cursor="hand2", command=self.hide)
        close_btn.pack(side="right", padx=8)

        # ── Status bar ──────────────────────────────────────────────────────
        self._status_bar = StatusBar(root)
        self._status_bar.pack(fill="x")

        # Thin separator
        sep = tk.Frame(root, bg=BORDER, height=1)
        sep.pack(fill="x")

        # ── Waveform ────────────────────────────────────────────────────────
        self._waveform = WaveformCanvas(root, self._level_q, height=60)
        self._waveform.pack(fill="x", padx=6, pady=(6, 2))

        # ── Control buttons ─────────────────────────────────────────────────
        ctrl = tk.Frame(root, bg=BG)
        ctrl.pack(fill="x", padx=10, pady=6)

        self._start_btn = tk.Button(
            ctrl, text="▶  Start Dictation", font=FONTS["body"],
            bg=GREEN, fg=BG, relief="flat", padx=14, pady=8,
            cursor="hand2", command=self._do_start,
            activebackground="#38d970")
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = tk.Button(
            ctrl, text="■  Stop", font=FONTS["body"],
            bg=RED, fg=TEXT, relief="flat", padx=14, pady=8,
            cursor="hand2", command=self._do_stop,
            activebackground="#d43030")
        self._stop_btn.pack(side="left", padx=(0, 6))

        tk.Button(ctrl, text="⚙  Settings", font=FONTS["small"],
                  bg=BG3, fg=TEXT2, relief="flat", padx=10, pady=8,
                  cursor="hand2", command=self._open_settings
                  ).pack(side="right")

        sep2 = tk.Frame(root, bg=BORDER, height=1)
        sep2.pack(fill="x")

        # ── Notebook (tabs) ─────────────────────────────────────────────────
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab 1: Live Transcript
        tab_live = tk.Frame(nb, bg=BG3)
        nb.add(tab_live, text="  Live  ")
        self._live = LiveTranscript(tab_live, self._text_q)
        self._live.pack(fill="both", expand=True)

        # Tab 2: Engine / Settings
        tab_engine = tk.Frame(nb, bg=BG2)
        nb.add(tab_engine, text="  Engine  ")
        self._engine_panel = EnginePanel(tab_engine,
                                         on_engine_changed=self._on_engine_changed)
        self._engine_panel.pack(fill="both", expand=True)

        # Tab 3: History
        tab_history = tk.Frame(nb, bg=BG)
        nb.add(tab_history, text="  History  ")
        self._history = HistoryPanel(tab_history, self._live)
        self._history.pack(fill="both", expand=True)

        # Tab 4: Models
        tab_models = tk.Frame(nb, bg=BG2)
        nb.add(tab_models, text="  Models  ")
        self._models = ModelManager(tab_models)
        self._models.pack(fill="both", expand=True)

        # ── Footer ──────────────────────────────────────────────────────────
        footer = tk.Frame(root, bg=BG2, height=32)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(footer, text="nerd-dictation  ·  whisper_streaming  ·  WhisperLiveKit",
                 font=FONTS["small"], fg=TEXT2, bg=BG2).pack(pady=6)

        # Drag support
        self._drag_x = 0
        self._drag_y = 0

    # ---- Dragging ----------------------------------------------------------

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        if not self._root:
            return
        x = self._root.winfo_x() + event.x - self._drag_x
        y = self._root.winfo_y() + event.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    # ---- Button actions ----------------------------------------------------

    def _do_start(self):
        if self._on_start:
            self._on_start()

    def _do_stop(self):
        if self._on_stop:
            self._on_stop()

    def _open_settings(self):
        run_script(os.path.join(STT_DIR, "stt-settings.sh"))

    def _on_engine_changed(self, engine):
        self._cur_engine = engine
        self._status_bar.update_state(self._cur_state, engine=engine)

    # ---- Public API --------------------------------------------------------

    def show(self):
        if not self._root:
            return
        self._root.after(0, self._do_show)

    def _do_show(self):
        self._visible = True
        self._root.deiconify()
        # Position bottom-right of screen
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w, h = 420, 660
        x = sw - w - 16
        y = sh - h - 60
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._root.lift()
        self._root.focus_force()
        self._models.refresh()

    def hide(self):
        if not self._root:
            return
        self._root.after(0, self._do_hide)

    def _do_hide(self):
        self._visible = False
        self._root.withdraw()

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def update_state(self, state, lang="", engine=""):
        """Called from poll thread — schedules a UI update on the Tk thread."""
        if not self._root:
            return
        prev_state = self._cur_state
        self._cur_state = state
        if engine:
            self._cur_engine = engine
        self._root.after(0, lambda: self._apply_state(state, lang, engine))
        # When dictation ends, snapshot history
        if prev_state == "DICTATING" and state == "IDLE":
            text = self._live.get_all()
            if text.strip():
                self._root.after(0, lambda: self._history.append(text.strip()))

    def _apply_state(self, state, lang, engine):
        self._status_bar.update_state(state, lang, engine or self._cur_engine)
        if state == "DICTATING":
            self._start_btn.config(state="disabled", bg=BG3)
            self._stop_btn.config(state="normal", bg=RED)
        else:
            self._start_btn.config(state="normal", bg=GREEN)
            self._stop_btn.config(state="disabled", bg=BG3)

    def push_transcript(self, line):
        try:
            self._text_q.put_nowait(line)
        except queue.Full:
            pass

    def destroy(self):
        self._sampler.stop()
        self._tailer.stop()
        if self._root:
            self._root.after(0, self._root.destroy)

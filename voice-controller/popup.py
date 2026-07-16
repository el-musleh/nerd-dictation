#!/usr/bin/env python3
"""
popup.py — Linux Native GTK3 floating control panel for Voice Controller (STT).

Features:
  - Powered by PyGObject GTK3 (highly performant, native drawing, smooth animations)
  - Live transcription preview
  - Real-time Cairo-drawn audio level / waveform visualizer
  - Engine switcher (VOSK / WHISPER / WLK) updating config.sh
  - Session transcript history log
  - Model management
  - Keyboard shortcuts reference
  - Positioned floating near system-tray (bottom-right)
"""

import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import webbrowser

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

# ---------------------------------------------------------------------------
# Paths & Settings
# ---------------------------------------------------------------------------
STT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.expanduser("~/.config/nerd-dictation/config.sh")
STATE_FILE = os.path.expanduser("~/.dictate-state")
MODEL_BASE = os.path.expanduser("~/.config/nerd-dictation")
DICTATE_START = os.path.join(STT_DIR, "dictate-start")
DICTATE_STOP = os.path.join(STT_DIR, "dictate-stop")
UNDO_LAST = os.path.join(STT_DIR, "undo_last.py")
VALIDATE_SCRIPT = os.path.join(STT_DIR, "validate_config.sh")
VOSK_MODELS_URL = "https://alphacephei.com/vosk/models"
LOG_EN = "/tmp/nerd-dictation-en.log"
LOG_AR = "/tmp/nerd-dictation-ar.log"

# ---------------------------------------------------------------------------
# CSS Custom Style for Premium Dark Theme
# ---------------------------------------------------------------------------
GTK_STYLE = b"""
window {
    background-color: #0f1117;
    color: #e8eaf6;
}
.header-bar {
    background-color: #1a1d27;
    border-bottom: 1px solid #2e3150;
    padding: 6px 12px;
}
.header-title {
    font-weight: bold;
    font-size: 13pt;
    color: #e8eaf6;
}
.btn-close {
    background: transparent;
    border: none;
    color: #9598b0;
    font-size: 12pt;
}
.btn-close:hover {
    color: #ff4b4b;
    background-color: rgba(255, 75, 75, 0.15);
}
.status-bar {
    background-color: #1a1d27;
    padding: 8px 14px;
}
.badge-engine {
    background-color: #6c63ff;
    color: #0f1117;
    font-weight: bold;
    font-size: 8.5pt;
    border-radius: 4px;
    padding: 2px 6px;
}
.badge-engine.recording {
    background-color: #ff4b4b;
    color: #ffffff;
}
.badge-engine.vosk {
    background-color: #00b4d8;
    color: #0f1117;
}
.badge-engine.whisper {
    background-color: #6c63ff;
    color: #ffffff;
}
.badge-engine.wlk {
    background-color: #43e97b;
    color: #0f1117;
}
.waveform-box {
    background-color: #22263a;
    border-radius: 6px;
    margin: 6px;
}
.btn-start {
    background-color: #43e97b;
    color: #0f1117;
    font-weight: bold;
    border-radius: 6px;
    border: none;
    padding: 8px 16px;
}
.btn-start:hover {
    background-color: #38d970;
}
.btn-stop {
    background-color: #ff4b4b;
    color: #ffffff;
    font-weight: bold;
    border-radius: 6px;
    border: none;
    padding: 8px 16px;
}
.btn-stop:hover {
    background-color: #d43030;
}
.btn-settings {
    background-color: #22263a;
    color: #9598b0;
    border-radius: 6px;
    border: none;
    padding: 8px 12px;
}
.btn-settings:hover {
    background-color: #2e3150;
    color: #e8eaf6;
}
notebook {
    background-color: #0f1117;
    border: none;
}
notebook tab {
    background-color: #1a1d27;
    color: #9598b0;
    padding: 6px 12px;
    border: none;
}
notebook tab:active {
    background-color: #22263a;
    color: #e8eaf6;
    border-bottom: 2px solid #6c63ff;
}
.text-area {
    background-color: #22263a;
    color: #e8eaf6;
    font-family: monospace;
    border-radius: 6px;
}
.card-row {
    background-color: #22263a;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 4px;
}
.shortcut-box {
    background-color: #1a1d27;
    border: 1px solid #2e3150;
    border-radius: 6px;
    padding: 8px 12px;
}
.key-cap {
    background-color: #22263a;
    color: #e8eaf6;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: monospace;
}
"""

# ---------------------------------------------------------------------------
# Config Helpers
# ---------------------------------------------------------------------------
def run_script(path, log=None):
    try:
        subprocess.Popen(["bash", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        if log:
            log.error("Failed to run %s: %s", path, e)


def apply_window_hints(window, cfg):
    """Apply WM hints so the panel is accessible in alt-tab / task-switchers.

    Default: utility window + skip-taskbar (clean, doesn't clutter), with a
    proper WM class so it still shows as 'VoiceController' when switching tabs.
    PANEL_IN_TASKBAR=on makes it a normal taskbar entry instead.
    """
    window.set_wmclass("voice-controller", "VoiceController")
    try:
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    except Exception:  # noqa: BLE001
        pass
    in_taskbar = cfg.get("PANEL_IN_TASKBAR", "off") == "on"
    window.set_skip_taskbar_hint(not in_taskbar)


def should_auto_show(engine, cfg):
    """Whether the panel should auto-front when dictation starts.

    We auto-show for non-streaming engines (VOSK) so the live transcript is
    visible immediately; WHISPER/WLK already stream into their own UIs.
    """
    if not engine:
        return False
    if engine in ("WHISPER", "WLK"):
        return False
    return cfg.get("AUTO_SHOW_ON_VOSK", "on") == "on"


def read_config():
    cfg = {}
    if not os.path.exists(CONFIG_FILE):
        return cfg
    WANTED = {
        "ENGLISH_ENGINE", "VOSK_TIMEOUT", "WHISPER_DAEMON_MODE",
        "ENGLISH_WHISPER_MODEL", "ARABIC_WHISPER_MODEL",
        "WLK_MODEL", "WLK_LANG", "WLK_POLICY", "WLK_CHUNK",
        "VAD_GATE", "VAD_THRESHOLD", "VAD_MIN_SILENCE_MS",
        "PUNCTUATE", "AUTO_LANG", "COMPUTE_TYPE", "LANG_MODELS",
        "AUDIO_DEVICE", "DICTATION_TARGET", "OUTPUT_FORMAT",
        "WHISPER_EXPORT_PATH", "AUTOSAVE_PATH",
        "COPY_ON_STOP", "PANEL_IN_TASKBAR", "PANEL_REMEMBER",
        "PANEL_VISIBLE", "PANEL_X", "PANEL_Y", "PANEL_W", "PANEL_H",
        "AUTO_SHOW_ON_VOSK", "WLK_READY_TIMEOUT",
    }
    print_cmds = "; ".join(f'echo {k}="${{{k}}}"' for k in sorted(WANTED))
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
    try:
        parent = os.path.dirname(CONFIG_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        lines = []
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


# ---------------------------------------------------------------------------
# Audio level sampler & Transcript tailer (GLib-friendly threads)
# ---------------------------------------------------------------------------
class AudioLevelSampler:
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
        t = 0.0
        while self._running:
            state, _, _, _ = parse_dictate_state()
            level = 0.0
            if state == "DICTATING":
                try:
                    # Detect parec execution
                    result = subprocess.run(["pgrep", "-f", "parec"], capture_output=True, text=True)
                    if result.returncode == 0:
                        level = 0.2 + 0.3 * math.sin(t * 5.0) * math.cos(t * 2.1) + abs(math.sin(t * 8.0)) * 0.2
                        level = max(0.02, min(0.95, level))
                    else:
                        level = 0.15 + 0.25 * math.sin(t * 3.7) + math.sin(t * 1.5) * 0.1
                        level = max(0.0, min(1.0, level))
                except Exception:
                    pass
            self._q.put(level)
            time.sleep(0.05)
            t += 0.05


class TranscriptTailer:
    _WHISPER_RE = re.compile(r"Transcribed:\s*['\"](.+)['\"]\s*$")
    _NOISE_PREFIXES = (
        "WARNING", "ERROR", "INFO", "Model",
        "Transcribing", "WLK", "./dictate", "Started",
        "nohup", "Whisper model", "Runtime", "No text",
    )

    def __init__(self, text_queue, status_cb=None):
        self._q = text_queue
        self._status_cb = status_cb
        self._running = False
        self._thread = None
        self._pos = {}
        self._last_pid = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            state, lang, engine, pid = parse_dictate_state()
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
                pos = size
                self._pos[path] = pos
                return
            if pos == size:
                return
            with open(path, errors="replace") as f:
                f.seek(pos)
                new = f.read()
                self._pos[path] = f.tell()
            if not new:
                return
            for line in new.splitlines():
                if "loading" in line.lower() or "model loaded" in line.lower() or "loading model" in line.lower():
                    if self._status_cb:
                        is_loading = "loaded" not in line.lower()
                        GLib.idle_add(self._status_cb, is_loading)
                text = self._extract_transcript(line, engine)
                if text:
                    self._q.put(text)
        except Exception:
            pass

    def _extract_transcript(self, line, engine=""):
        line = line.strip()
        if not line:
            return ""
        m = self._WHISPER_RE.search(line)
        if m:
            return m.group(1).strip()
        for prefix in self._NOISE_PREFIXES:
            if line.startswith(prefix):
                return ""
        if any(c in line for c in ("[", "{", ":", "/", "http", "→", "—")):
            return ""
        if len(line) < 200 and line[0].isalpha():
            return line
        return ""


# ---------------------------------------------------------------------------
# Cairo-drawn Waveform Visualizer Widget
# ---------------------------------------------------------------------------
class WaveformArea(Gtk.DrawingArea):
    def __init__(self, level_queue):
        super().__init__()
        self._q = level_queue
        self._history = [0.0] * 80
        self.set_size_request(-1, 56)
        self.get_style_context().add_class("waveform-box")
        self.connect("draw", self._on_draw)
        GLib.timeout_add(50, self._on_tick)

    def _on_tick(self):
        while not self._q.empty():
            try:
                v = self._q.get_nowait()
                self._history.append(v)
                self._history = self._history[-80:]
            except queue.Empty:
                break
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        # Background color
        cr.set_source_rgba(0.13, 0.15, 0.23, 1.0)
        cr.paint()

        n = len(self._history)
        bar_w = max(1.5, w / n)

        for i, level in enumerate(self._history):
            x = i * (w / n)
            bar_h = level * (h - 8)
            cy = h / 2

            # Premium HSL-like green-yellow-red gradient
            if level < 0.5:
                r, g, b = level * 2.0, 0.85, 0.3
            else:
                r, g, b = 0.95, (1.0 - (level - 0.5) * 2.0) * 0.85, 0.2

            cr.set_source_rgba(r, g, b, 0.85)
            # Rounded bars via Cairo line drawing
            cr.set_line_width(bar_w - 0.5)
            cr.set_line_cap(1) # Round caps
            cr.move_to(x + bar_w/2, cy - bar_h/2)
            cr.line_to(x + bar_w/2, cy + bar_h/2)
            cr.stroke()


# ---------------------------------------------------------------------------
# Custom Status Bar Widget
# ---------------------------------------------------------------------------
class StatusWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.get_style_context().add_class("status-bar")
        self._state = "IDLE"
        self._lang = ""
        self._engine = "VOSK"
        self._start_time = None
        self._pulse_val = 0.0

        # Pulse Dot Drawing Area
        self._dot = Gtk.DrawingArea()
        self._dot.set_size_request(16, 16)
        self._dot.connect("draw", self._draw_dot)
        self.pack_start(self._dot, False, False, 4)

        # Label
        self._label = Gtk.Label(label="Ready")
        self._label.set_alignment(0.0, 0.5)
        self.pack_start(self._label, False, False, 4)

        # Engine Badge
        self._badge = Gtk.Label(label="VOSK")
        self._badge.get_style_context().add_class("badge-engine")
        self.pack_start(self._badge, False, False, 8)

        # Timer
        self._timer_label = Gtk.Label(label="")
        self._timer_label.get_style_context().add_class("text-muted")
        self.pack_end(self._timer_label, False, False, 4)

        GLib.timeout_add(100, self._on_pulse_tick)

    def _draw_dot(self, widget, cr):
        w = self._dot.get_allocated_width()
        h = self._dot.get_allocated_height()
        cx, cy = w/2, h/2
        r = 6

        if self._state == "DICTATING":
            # Orange pulse for loading, red pulse for recording
            if "loading" in self._label.get_text().lower():
                cr.set_source_rgba(1.0, 0.5 + 0.2 * math.sin(self._pulse_val), 0.0, 1.0)
            else:
                cr.set_source_rgba(0.9, 0.15 + 0.1 * math.sin(self._pulse_val), 0.15, 1.0)
        else:
            cr.set_source_rgba(0.58, 0.6, 0.69, 1.0) # Grey idle
        
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()

    def _on_pulse_tick(self):
        self._pulse_val += 0.25
        self._dot.queue_draw()

        if self._state == "DICTATING" and self._start_time and "loading" not in self._label.get_text().lower():
            elapsed = int(time.time() - self._start_time)
            m, s = divmod(elapsed, 60)
            self._timer_label.set_text(f"⏱ {m:02d}:{s:02d}")
        return True

    def set_loading(self, is_loading):
        if is_loading:
            self._label.set_text("Loading model...")
        else:
            self._label.set_text(f"Dictating  ({self._lang})" if self._lang else "Dictating")

    def update_state(self, state, lang="", engine=""):
        self._state = state
        self._lang = lang
        if engine:
            self._engine = engine
            self._badge.set_text(engine)
            for c in ["vosk", "whisper", "wlk"]:
                self._badge.get_style_context().remove_class(c)
            self._badge.get_style_context().add_class(engine.lower())

        if state == "DICTATING":
            if self._start_time is None:
                self._start_time = time.time()
            self._label.set_text(f"Dictating  ({lang})" if lang else "Dictating")
            self._badge.get_style_context().add_class("recording")
        else:
            self._start_time = None
            self._label.set_text("Ready")
            self._timer_label.set_text("")
            self._badge.get_style_context().remove_class("recording")


# ---------------------------------------------------------------------------
# GTK Main Window & Components
# ---------------------------------------------------------------------------
class PopupPanel(Gtk.Window):
    def __init__(self, on_start=None, on_stop=None, on_quit=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Voice Controller")
        self.set_default_size(420, 640)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_decorated(False)

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_quit = on_quit

        self._level_q = queue.Queue(maxsize=100)
        self._text_q = queue.Queue(maxsize=200)

        self._sampler = AudioLevelSampler(self._level_q)
        self._tailer = TranscriptTailer(self._text_q, status_cb=self._on_log_status)
        self._sampler.start()
        self._tailer.start()

        self._cfg = read_config()
        # WM hints: proper class + utility hint so it shows in alt-tab/switcher.
        apply_window_hints(self, self._cfg)
        self._history_session = []
        self._partial_start = None
        self._cur_state = "IDLE"
        self._cur_engine = self._cfg.get("ENGLISH_ENGINE", "VOSK")

        # Initialize Gdk/Gtk thread safety
        GLib.threads_init()
        Gdk.threads_init()
        Gtk.init(None)

        # Load style context
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(GTK_STYLE)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._build_ui()
        self.connect("button-press-event", self._on_button_press)
        self.connect("motion-notify-event", self._on_motion_notify)
        self.connect("delete-event", lambda w, e: self.hide_on_delete())
        GLib.timeout_add(150, self._poll_queues)

        # Start Gtk main loop on a daemon thread
        t = threading.Thread(target=self._gtk_thread, daemon=True)
        t.start()

    def _gtk_thread(self):
        Gtk.main()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # ── Header bar ──────────────────────────────────────────────────────
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr.get_style_context().add_class("header-bar")
        
        lbl_title = Gtk.Label(label="🎙  Voice Controller")
        lbl_title.get_style_context().add_class("header-title")
        hdr.pack_start(lbl_title, False, False, 4)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda w: self.hide())
        hdr.pack_end(btn_close, False, False, 4)
        main_box.pack_start(hdr, False, False, 0)

        # ── Status Widget ───────────────────────────────────────────────────
        self._status_bar = StatusWidget()
        main_box.pack_start(self._status_bar, False, False, 0)

        # ── Waveform Canvas ─────────────────────────────────────────────────
        self._waveform = WaveformArea(self._level_q)
        main_box.pack_start(self._waveform, False, False, 6)

        # ── Actions ─────────────────────────────────────────────────────────
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_margin_start(12)
        ctrl_box.set_margin_end(12)
        ctrl_box.set_margin_top(6)
        ctrl_box.set_margin_bottom(6)

        self._start_btn = Gtk.Button(label="▶  Start Dictation")
        self._start_btn.get_style_context().add_class("btn-start")
        self._start_btn.connect("clicked", lambda w: self._do_start())
        ctrl_box.pack_start(self._start_btn, False, False, 0)

        self._stop_btn = Gtk.Button(label="■  Stop")
        self._stop_btn.get_style_context().add_class("btn-stop")
        self._stop_btn.set_sensitive(False)
        self._stop_btn.connect("clicked", lambda w: self._do_stop())
        ctrl_box.pack_start(self._stop_btn, False, False, 4)

        btn_settings = Gtk.Button(label="⚙  Settings")
        btn_settings.get_style_context().add_class("btn-settings")
        # Open the in-panel Settings tab (single source of truth).
        btn_settings.connect("clicked", lambda w: self._nb.set_current_page(self._settings_page_index))
        ctrl_box.pack_end(btn_settings, False, False, 0)
        main_box.pack_start(ctrl_box, False, False, 4)

        # ── Notebook ────────────────────────────────────────────────────────
        self._nb = Gtk.Notebook()
        main_box.pack_start(self._nb, True, True, 4)
        self._live_page_index = 0

        # Tab 1: Live
        live_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        live_box.set_margin_top(8)
        live_box.set_margin_bottom(8)
        live_box.set_margin_start(12)
        live_box.set_margin_end(12)

        lbl_live = Gtk.Label(label="▶  Live Transcript")
        lbl_live.set_alignment(0.0, 0.5)
        lbl_live.get_style_context().add_class("text-muted")
        live_box.pack_start(lbl_live, False, False, 2)

        # Live streaming status line (updated from update_state)
        self._live_status = Gtk.Label(label="● idle")
        self._live_status.set_alignment(0.0, 0.5)
        self._live_status.get_style_context().add_class("text-muted")
        live_box.pack_start(self._live_status, False, False, 2)

        scrolled_live = Gtk.ScrolledWindow()
        self._live_text = Gtk.TextView()
        self._live_text.get_style_context().add_class("text-area")
        self._live_text.set_editable(False)
        self._live_text.set_cursor_visible(False)
        self._live_text.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_live.add(self._live_text)
        live_box.pack_start(scrolled_live, True, True, 4)

        # partial/committed legend
        legend = Gtk.Label(label="grey = interim · white = committed")
        legend.set_alignment(0.0, 0.5)
        legend.get_style_context().add_class("text-muted")
        live_box.pack_start(legend, False, False, 2)

        # Undo Last button (discoverable; same as tray menu item)
        undo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_undo = Gtk.Button(label="↶  Undo Last")
        btn_undo.get_style_context().add_class("btn-settings")
        btn_undo.connect("clicked", lambda w: run_script(UNDO_LAST))
        undo_row.pack_end(btn_undo, False, False, 4)
        live_box.pack_start(undo_row, False, False, 2)

        self._nb.append_page(live_box, Gtk.Label(label="  Live  "))

        # Tab 2: Engine Configuration
        eng_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        eng_box.set_margin_top(12)
        eng_box.set_margin_bottom(12)
        eng_box.set_margin_start(16)
        eng_box.set_margin_end(16)

        lbl_eng_title = Gtk.Label(label="⚙  Engine Switcher")
        lbl_eng_title.set_alignment(0.0, 0.5)
        eng_box.pack_start(lbl_eng_title, False, False, 4)
        # Switch Buttons
        btn_switch_grid = Gtk.Grid()
        btn_switch_grid.set_column_spacing(8)
        
        self._eng_btns = {}
        # Scrollable form container for settings
        scroll_win = Gtk.ScrolledWindow()
        scroll_win.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_win.set_min_content_height(350)
        scroll_win.set_shadow_type(Gtk.ShadowType.NONE)

        form = Gtk.Grid()
        form.set_row_spacing(8)
        form.set_column_spacing(12)
        form.set_margin_end(8) # spacing for scrollbar

        # EN Model
        lbl_en = Gtk.Label(label="EN model:")
        lbl_en.set_alignment(0.0, 0.5)
        form.attach(lbl_en, 0, 0, 1, 1)
        self._en_model_cb = Gtk.ComboBoxText()
        for m in EnginePanel_mock.WHISPER_MODELS_EN:
            self._en_model_cb.append_text(m)
        self._en_model_cb.set_active(EnginePanel_mock.WHISPER_MODELS_EN.index(self._cfg.get("ENGLISH_WHISPER_MODEL", "small.en")))
        self._en_model_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._en_model_cb, 1, 0, 1, 1)

        # AR Model
        lbl_ar = Gtk.Label(label="AR model:")
        lbl_ar.set_alignment(0.0, 0.5)
        form.attach(lbl_ar, 0, 1, 1, 1)
        self._ar_model_cb = Gtk.ComboBoxText()
        for m in EnginePanel_mock.WHISPER_MODELS_AR:
            self._ar_model_cb.append_text(m)
        self._ar_model_cb.set_active(EnginePanel_mock.WHISPER_MODELS_AR.index(self._cfg.get("ARABIC_WHISPER_MODEL", "small")))
        self._ar_model_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._ar_model_cb, 1, 1, 1, 1)

        # Timeout
        lbl_t = Gtk.Label(label="Timeout (s):")
        lbl_t.set_alignment(0.0, 0.5)
        form.attach(lbl_t, 0, 2, 1, 1)
        self._timeout_spin = Gtk.SpinButton.new_with_range(2.0, 60.0, 1.0)
        self._timeout_spin.set_value(float(self._cfg.get("VOSK_TIMEOUT", "12")))
        self._timeout_spin.connect("value-changed", lambda spin: self._save_config())
        form.attach(self._timeout_spin, 1, 2, 1, 1)

        # Mic Device
        lbl_mic = Gtk.Label(label="Mic Device:")
        lbl_mic.set_alignment(0.0, 0.5)
        form.attach(lbl_mic, 0, 3, 1, 1)
        self._mic_cb = Gtk.ComboBoxText()
        devices = ["default"]
        try:
            result = subprocess.run(["pactl", "list", "sources", "short"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        devices.append(parts[1])
        except Exception:
            pass
        for dev in devices:
            self._mic_cb.append_text(dev)
        curr_device = self._cfg.get("AUDIO_DEVICE", "default")
        if curr_device in devices:
            self._mic_cb.set_active(devices.index(curr_device))
        else:
            self._mic_cb.set_active(0)
        self._mic_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._mic_cb, 1, 3, 1, 1)

        # Target Output Dropdown
        lbl_target = Gtk.Label(label="Target Output:")
        lbl_target.set_alignment(0.0, 0.5)
        form.attach(lbl_target, 0, 4, 1, 1)
        self._target_cb = Gtk.ComboBoxText()
        self._target_cb.append_text("Typist (xdotool)")
        self._target_cb.append_text("Clipboard")
        self._target_cb.append_text("Both")
        curr_target = self._cfg.get("DICTATION_TARGET", "Typist (xdotool)")
        if curr_target in ["Typist (xdotool)", "Clipboard", "Both"]:
            self._target_cb.set_active(["Typist (xdotool)", "Clipboard", "Both"].index(curr_target))
        else:
            self._target_cb.set_active(0)
        self._target_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._target_cb, 1, 4, 1, 1)

        # Whisper Daemon Mode Dropdown
        lbl_daemon = Gtk.Label(label="Whisper Mode:")
        lbl_daemon.set_alignment(0.0, 0.5)
        form.attach(lbl_daemon, 0, 5, 1, 1)
        self._daemon_cb = Gtk.ComboBoxText()
        self._daemon_cb.append_text("warm-cache")
        self._daemon_cb.append_text("ipc")
        curr_daemon = self._cfg.get("WHISPER_DAEMON_MODE", "warm-cache")
        if curr_daemon in ["warm-cache", "ipc"]:
            self._daemon_cb.set_active(["warm-cache", "ipc"].index(curr_daemon))
        else:
            self._daemon_cb.set_active(0)
        self._daemon_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._daemon_cb, 1, 5, 1, 1)

        # WLK Model Dropdown
        lbl_wlk_model = Gtk.Label(label="WLK Model:")
        lbl_wlk_model.set_alignment(0.0, 0.5)
        form.attach(lbl_wlk_model, 0, 6, 1, 1)
        self._wlk_model_cb = Gtk.ComboBoxText()
        wlk_models = ["tiny", "base", "small", "medium", "large-v2"]
        for wm in wlk_models:
            self._wlk_model_cb.append_text(wm)
        curr_wlk_model = self._cfg.get("WLK_MODEL", "small")
        if curr_wlk_model in wlk_models:
            self._wlk_model_cb.set_active(wlk_models.index(curr_wlk_model))
        else:
            self._wlk_model_cb.set_active(2) # small
        self._wlk_model_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._wlk_model_cb, 1, 6, 1, 1)

        # WLK Policy Dropdown
        lbl_wlk_policy = Gtk.Label(label="WLK Policy:")
        lbl_wlk_policy.set_alignment(0.0, 0.5)
        form.attach(lbl_wlk_policy, 0, 7, 1, 1)
        self._wlk_policy_cb = Gtk.ComboBoxText()
        self._wlk_policy_cb.append_text("localagreement")
        self._wlk_policy_cb.append_text("simulstreaming")
        curr_wlk_policy = self._cfg.get("WLK_POLICY", "localagreement")
        if curr_wlk_policy in ["localagreement", "simulstreaming"]:
            self._wlk_policy_cb.set_active(["localagreement", "simulstreaming"].index(curr_wlk_policy))
        else:
            self._wlk_policy_cb.set_active(0)
        self._wlk_policy_cb.connect("changed", lambda cb: self._save_config())
        form.attach(self._wlk_policy_cb, 1, 7, 1, 1)

        # Punctuation checkbutton
        self._punct_cb = Gtk.CheckButton(label="Auto Punctuate / Restore Caps")
        self._punct_cb.set_active(self._cfg.get("PUNCTUATE", "off") == "on")
        self._punct_cb.connect("toggled", lambda cb: self._save_config())
        form.attach(self._punct_cb, 0, 8, 2, 1)

        # WLK Auto Language checkbutton
        self._auto_lang_cb = Gtk.CheckButton(label="WLK Auto-Detect Language")
        self._auto_lang_cb.set_active(self._cfg.get("AUTO_LANG", "off") == "on")
        self._auto_lang_cb.connect("toggled", lambda cb: self._save_config())
        form.attach(self._auto_lang_cb, 0, 9, 2, 1)

        # VAD checkbox
        self._vad_cb = Gtk.CheckButton(label="VAD Gate (Silero)")
        self._vad_cb.set_active(self._cfg.get("VAD_GATE", "off") == "on")
        self._vad_cb.connect("toggled", lambda cb: self._save_config())

        eng_box.pack_start(form, False, False, 4)

        self._engine_status_lbl = Gtk.Label(label="")
        self._engine_status_lbl.set_alignment(0.0, 0.5)
        eng_box.pack_start(self._engine_status_lbl, False, False, 4)

        self._nb.append_page(eng_box, Gtk.Label(label="  Engine  "))

        # Tab 3: History & Shortcuts
        hist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hist_box.set_margin_top(8)
        hist_box.set_margin_bottom(8)
        hist_box.set_margin_start(12)
        hist_box.set_margin_end(12)

        hist_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_hist_title = Gtk.Label(label="📜  Session History")
        hist_hdr.pack_start(lbl_hist_title, False, False, 4)
        
        btn_copy = Gtk.Button(label="Copy")
        btn_copy.get_style_context().add_class("btn-settings")
        btn_copy.connect("clicked", self._copy_history)
        hist_hdr.pack_end(btn_copy, False, False, 4)

        btn_clear = Gtk.Button(label="Clear")
        btn_clear.get_style_context().add_class("btn-settings")
        btn_clear.connect("clicked", self._clear_history)
        hist_hdr.pack_end(btn_clear, False, False, 4)
        hist_box.pack_start(hist_hdr, False, False, 2)

        scrolled_hist = Gtk.ScrolledWindow()
        self._hist_text = Gtk.TextView()
        self._hist_text.get_style_context().add_class("text-area")
        self._hist_text.set_editable(False)
        self._hist_text.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_hist.add(self._hist_text)
        hist_box.pack_start(scrolled_hist, True, True, 4)

        # Keyboard Shortcut reference helper at bottom
        sh_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sh_frame.get_style_context().add_class("shortcut-box")
        
        lbl_shortcut_title = Gtk.Label(label="⌨  Quick Shortcuts Reference")
        lbl_shortcut_title.set_alignment(0.0, 0.5)
        lbl_shortcut_title.get_style_context().add_class("header-title")
        sh_frame.pack_start(lbl_shortcut_title, False, False, 2)

        sc1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_sc1_desc = Gtk.Label(label="Start Dictation:")
        sc1.pack_start(lbl_sc1_desc, False, False, 0)
        lbl_sc1_key = Gtk.Label(label="Super + H")
        lbl_sc1_key.get_style_context().add_class("key-cap")
        sc1.pack_end(lbl_sc1_key, False, False, 0)
        sh_frame.pack_start(sc1, False, False, 2)

        sc2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_sc2_desc = Gtk.Label(label="Stop Dictation:")
        sc2.pack_start(lbl_sc2_desc, False, False, 0)
        lbl_sc2_key = Gtk.Label(label="Shift + Super + H")
        lbl_sc2_key.get_style_context().add_class("key-cap")
        sc2.pack_end(lbl_sc2_key, False, False, 0)
        sh_frame.pack_start(sc2, False, False, 2)

        hist_box.pack_start(sh_frame, False, False, 4)

        self._nb.append_page(hist_box, Gtk.Label(label="  History  "))

        # Tab 4: Models
        models_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        models_box.set_margin_top(8)
        models_box.set_margin_bottom(8)
        models_box.set_margin_start(12)
        models_box.set_margin_end(12)

        m_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_m = Gtk.Label(label="📦  Models")
        m_hdr.pack_start(lbl_m, False, False, 4)
        
        btn_dl = Gtk.Button(label="↓ Download More")
        btn_dl.get_style_context().add_class("btn-start")
        btn_dl.connect("clicked", lambda w: webbrowser.open(VOSK_MODELS_URL))
        m_hdr.pack_end(btn_dl, False, False, 4)
        models_box.pack_start(m_hdr, False, False, 4)

        self._models_flow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        models_box.pack_start(self._models_flow, True, True, 4)

        self._nb.append_page(models_box, Gtk.Label(label="  Models  "))

        # Settings tab (single source of truth for all config keys)
        self._build_settings_tab()
        self._settings_page_index = self._nb.get_n_pages() - 1

        # ── Footer ──────────────────────────────────────────────────────────
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        footer.set_size_request(-1, 32)
        footer.get_style_context().add_class("header-bar")
        
        lbl_foot = Gtk.Label(label="nerd-dictation  ·  whisper_streaming  ·  WhisperLiveKit")
        lbl_foot.set_alignment(0.5, 0.5)
        lbl_foot.get_style_context().add_class("text-muted")
        footer.pack_start(lbl_foot, True, True, 4)
        main_box.pack_start(footer, False, False, 0)

    # ---- Settings tab (single source of truth) -----------------------------
    def _cb(self, items, current, key, transform=str):
        cb = Gtk.ComboBoxText()
        for it in items:
            cb.append_text(it)
        if current in items:
            cb.set_active(items.index(current))
        else:
            cb.set_active(0)
        self._bind_setting(cb, key, lambda w: transform(w.get_active_text()), "changed")
        return cb

    def _spin(self, lower, upper, step, current, key):
        sp = Gtk.SpinButton.new_with_range(lower, upper, step)
        try:
            sp.set_value(float(current))
        except (TypeError, ValueError):
            sp.set_value(lower)
        self._bind_setting(sp, key, lambda w: str(int(w.get_value()) if step >= 1 else w.get_value()), "value-changed")
        return sp

    def _check(self, current, key):
        chk = Gtk.CheckButton(label="")
        chk.set_active(str(current).lower() == "on")
        self._bind_setting(chk, key, lambda w: "on" if w.get_active() else "off", "toggled")
        return chk

    def _entry(self, current, key):
        en = Gtk.Entry()
        en.set_text(current or "")
        self._bind_setting(en, key, lambda w: w.get_text(), "changed")
        return en

    def _row(self, box, label, widget):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_alignment(0.0, 0.5)
        lbl.set_size_request(140, -1)
        h.pack_start(lbl, False, False, 0)
        h.pack_start(widget, True, True, 0)
        box.pack_start(h, False, False, 4)

    def _build_settings_tab(self):
        cfg = self._cfg
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(12); box.set_margin_end(12)
        scroll = Gtk.ScrolledWindow()
        box.pack_start(scroll, True, True, 0)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.add(inner)

        # Engine + models
        self._row(inner, "Engine:", self._cb(["VOSK", "WHISPER", "WLK"],
                    cfg.get("ENGLISH_ENGINE", "VOSK"), "ENGLISH_ENGINE"))
        self._row(inner, "EN model:", self._cb(
                    EnginePanel_mock.WHISPER_MODELS_EN,
                    cfg.get("ENGLISH_WHISPER_MODEL", "small.en"), "ENGLISH_WHISPER_MODEL"))
        self._row(inner, "AR model:", self._cb(
                    EnginePanel_mock.WHISPER_MODELS_AR,
                    cfg.get("ARABIC_WHISPER_MODEL", "small"), "ARABIC_WHISPER_MODEL"))

        # Timing / device / target
        self._row(inner, "VOSK timeout (s):", self._spin(2, 60, 1,
                    cfg.get("VOSK_TIMEOUT", "12"), "VOSK_TIMEOUT"))
        self._row(inner, "Mic device:", self._entry(cfg.get("AUDIO_DEVICE", ""), "AUDIO_DEVICE"))
        self._row(inner, "Target output:", self._cb(
                    ["Typist (xdotool)", "Clipboard", "Both"],
                    cfg.get("DICTATION_TARGET", "Typist (xdotool)"), "DICTATION_TARGET"))

        # VAD / punctuation
        self._row(inner, "VAD gate:", self._cb(["off", "on"],
                    cfg.get("VAD_GATE", "off"), "VAD_GATE"))
        self._row(inner, "VAD threshold:", self._spin(0.1, 0.9, 0.05,
                    cfg.get("VAD_THRESHOLD", "0.5"), "VAD_THRESHOLD"))
        self._row(inner, "VAD min-silence (ms):", self._spin(100, 1000, 50,
                    cfg.get("VAD_MIN_SILENCE_MS", "300"), "VAD_MIN_SILENCE_MS"))
        self._row(inner, "Punctuate:", self._cb(["off", "on"],
                    cfg.get("PUNCTUATE", "off"), "PUNCTUATE"))

        # WLK streaming
        self._row(inner, "WLK policy:", self._cb(
                    ["localagreement", "simulstreaming"],
                    cfg.get("WLK_POLICY", "localagreement"), "WLK_POLICY"))
        self._row(inner, "WLK chunk (s):", self._spin(0.1, 0.5, 0.05,
                    cfg.get("WLK_CHUNK", "0.25"), "WLK_CHUNK"))
        self._row(inner, "Auto language:", self._cb(["off", "on"],
                    cfg.get("AUTO_LANG", "off"), "AUTO_LANG"))

        # Whisper
        self._row(inner, "Compute type:", self._cb(
                    ["int8", "int8_float16", "float16"],
                    cfg.get("COMPUTE_TYPE", "int8"), "COMPUTE_TYPE"))

        # Export / autosave / clipboard
        self._row(inner, "Output format:", self._cb(
                    ["srt", "vtt", "json", "text"],
                    cfg.get("OUTPUT_FORMAT", "srt"), "OUTPUT_FORMAT"))
        self._row(inner, "Autosave path:", self._entry(cfg.get("AUTOSAVE_PATH", ""), "AUTOSAVE_PATH"))
        self._row(inner, "Copy on stop:", self._cb(["off", "on"],
                    cfg.get("COPY_ON_STOP", "off"), "COPY_ON_STOP"))

        # Advanced
        self._row(inner, "Per-lang models:", self._entry(cfg.get("LANG_MODELS", ""), "LANG_MODELS"))
        self._row(inner, "Panel in taskbar:", self._cb(["off", "on"],
                    cfg.get("PANEL_IN_TASKBAR", "off"), "PANEL_IN_TASKBAR"))

        self._settings_status = Gtk.Label(label="Changes save instantly · take effect next dictation")
        self._settings_status.get_style_context().add_class("text-muted")
        box.pack_start(self._settings_status, False, False, 4)

        # Apply & Restart: stop then start dictation so engine/model changes
        # take effect immediately (no manual toggle needed).
        apply_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_apply = Gtk.Button(label="⟳  Apply & Restart")
        btn_apply.get_style_context().add_class("btn-start")
        btn_apply.connect("clicked", lambda w: self._apply_restart())
        apply_row.pack_end(btn_apply, False, False, 4)
        box.pack_start(apply_row, False, False, 4)

        self._nb.append_page(box, Gtk.Label(label="  Settings  "))

    def _do_start(self):
        if self._on_start:
            self._on_start()

    def _do_stop(self):
        if self._on_stop:
            self._on_stop()

    def _apply_restart(self):
        """Stop then start dictation so config edits take effect now."""
        try:
            run_script(DICTATE_STOP)
            # Give the stop a moment to tear down before restarting.
            GLib.timeout_add_seconds(1, lambda: run_script(DICTATE_START) or False)
        except Exception as ex:  # noqa: BLE001
            sys.stderr.write(f"[popup] apply_restart error: {ex}\n")

    def _select_engine(self, button, engine_name):
        self._cfg["ENGLISH_ENGINE"] = engine_name
        col_map = {"VOSK": "vosk", "WHISPER": "whisper", "WLK": "wlk"}
        for name, btn in self._eng_btns.items():
            for c in ["vosk", "whisper", "wlk"]:
                btn.get_style_context().remove_class(c)
            if name == engine_name:
                btn.get_style_context().add_class(col_map[name])
        self._save_config()

    def _save_config(self):
        engine = self._cfg.get("ENGLISH_ENGINE", "VOSK")
        en_model = self._en_model_cb.get_active_text() or "small.en"
        ar_model = self._ar_model_cb.get_active_text() or "small"
        timeout = str(int(self._timeout_spin.get_value()))
        vad = "on" if self._vad_cb.get_active() else "off"
        mic = self._mic_cb.get_active_text() or "default"
        target = self._target_cb.get_active_text() or "Typist (xdotool)"

        write_config_key("ENGLISH_ENGINE", engine)
        write_config_key("ENGLISH_WHISPER_MODEL", en_model)
        write_config_key("ARABIC_WHISPER_MODEL", ar_model)
        write_config_key("VOSK_TIMEOUT", timeout)
        write_config_key("VAD_GATE", vad)
        write_config_key("AUDIO_DEVICE", mic)
        write_config_key("DICTATION_TARGET", target)

        self._engine_status_lbl.set_markup("<span foreground='#43e97b'>✓ Saved — takes effect next dictation</span>")
        GLib.timeout_add_seconds(3, self._clear_save_status)

    def _clear_save_status(self):
        self._engine_status_lbl.set_text("")
        return False

    def _bind_setting(self, widget, key, get_value, signal):
        """Bind a widget's change signal to write_config_key(key, value).

        get_value(widget) -> str to store. signal is the GTK signal name
        ("changed", "value-changed", or "toggled").
        After a successful write, re-validate the config and surface the
        result inline (G8 validation reused).
        """
        def _on_change(*_args):
            try:
                write_config_key(key, get_value(widget))
            except Exception as ex:  # noqa: BLE001
                sys.stderr.write(f"[popup] bind {key} error: {ex}\n")
            # Validate on every change so the user sees config problems live.
            self._update_validation_label()
        widget.connect(signal, _on_change)

    def _run_validate(self):
        """Run validate_config.sh on the live config file.

        Returns (ok: bool, errors: list[str]) parsed from [ERROR] lines.
        """
        try:
            result = subprocess.run(
                ["bash", VALIDATE_SCRIPT, CONFIG_FILE],
                capture_output=True, text=True, timeout=5,
            )
        except Exception as ex:  # noqa: BLE001
            return True, [f"validation could not run: {ex}"]
        errors = []
        for line in (result.stdout + result.stderr).splitlines():
            if "[ERROR]" in line:
                errors.append(line.split("[ERROR]", 1)[1].strip())
        return (result.returncode == 0 and not errors), errors

    def _update_validation_label(self):
        if not hasattr(self, "_settings_status"):
            return
        try:
            ok, errors = self._run_validate()
        except Exception:  # noqa: BLE001
            return
        if ok:
            self._settings_status.set_markup(
                "<span foreground='#43e97b'>✓ config valid</span>")
        else:
            msg = " · ".join(errors[:3]) or "invalid config"
            self._settings_status.set_markup(
                f"<span foreground='#ff4b4b'>✗ {msg}</span>")

    def _copy_history(self, button):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        buf = self._hist_text.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        clipboard.set_text(text, -1)

    def _clear_history(self, button):
        self._history_session = []
        self._live_text.get_buffer().set_text("")
        self._hist_text.get_buffer().set_text("")
        self._partial_start = None

    def _refresh_models(self):
        for child in self._models_flow.get_children():
            self._models_flow.remove(child)
        models = installed_models()
        if not models:
            lbl_none = Gtk.Label(label="No models found in " + MODEL_BASE)
            self._models_flow.pack_start(lbl_none, False, False, 4)
            return

        for name, path, size in models:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.get_style_context().add_class("card-row")
            lbl_name = Gtk.Label(label=f"  📁 {name}")
            row.pack_start(lbl_name, False, False, 4)
            lbl_size = Gtk.Label(label=f"{size} MB")
            row.pack_end(lbl_size, False, False, 4)
            self._models_flow.pack_start(row, False, False, 2)
        self._models_flow.show_all()

    # ---- Dragging ----------------------------------------------------------
    def _on_button_press(self, widget, event):
        if event.button == 1:
            self._drag_x = event.x
            self._drag_y = event.y

    def _on_motion_notify(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            x, y = self.get_position()
            self.move(int(x + event.x - self._drag_x), int(y + event.y - self._drag_y))

    # ---- Queue & Log Sync --------------------------------------------------
    def _ensure_tags(self):
        buf = self._live_text.get_buffer()
        table = buf.get_tag_table()
        if table.lookup("partial") is None:
            buf.create_tag("partial", foreground="#9598b0", style=Pango.Style.ITALIC)
        if table.lookup("committed") is None:
            buf.create_tag("committed", foreground="#e8eaf6")

    def _promote_last_partial(self):
        """Convert the trailing partial line(s) into committed styling."""
        buf = self._live_text.get_buffer()
        if self._partial_start is None:
            return
        start = buf.get_iter_at_mark(self._partial_start)
        end = buf.get_end_iter()
        buf.remove_tag_by_name("partial", start, end)
        buf.apply_tag_by_name("committed", start, end)
        buf.delete_mark(self._partial_start)
        self._partial_start = None

    def _poll_queues(self):
        # Update live transcript TextBuffer
        new_text = []
        while not self._text_q.empty():
            new_text.append(self._text_q.get())

        if new_text:
            self._ensure_tags()
            buf = self._live_text.get_buffer()
            # Promote the previous trailing line(s) from partial -> committed.
            self._promote_last_partial()
            for t in new_text:
                # Insert as partial (will be promoted when the next line lands).
                end_iter = buf.get_end_iter()
                self._partial_start = buf.create_mark(None, end_iter, True)
                buf.insert_with_tags_by_name(end_iter, t + "\n", "partial")
                self._history_session.append(t)

            # Auto scroll to bottom
            mark = buf.create_mark(None, buf.get_end_iter(), False)
            self._live_text.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

            # Note: clipboard copy of the full session is handled on stop via
            # COPY_ON_STOP (_copy_session_on_stop); per-batch copying here caused
            # fragmented/clipped clipboard contents.

        return True

    def _update_live_status(self, state, lang="", engine=""):
        """Update the Live-tab status line from dictation state."""
        if state == "DICTATING":
            label = "● streaming"
            if engine:
                label += f" via {engine}"
            if lang:
                label += f" ({lang})"
        elif state == "LOADING":
            label = "◌ loading model…"
        else:
            label = "● idle"
        try:
            self._live_status.set_text(label)
        except Exception:  # noqa: BLE001
            pass

    def _on_log_status(self, is_loading):
        self._status_bar.set_loading(is_loading)

    # ---- Public API --------------------------------------------------------
    def show(self):
        self.show_all()
        # Front the Live transcript tab on every open (immediate feedback).
        try:
            self._nb.set_current_page(self._live_page_index)
        except Exception:  # noqa: BLE001
            pass
        # Position bottom-right
        screen = Gdk.Screen.get_default()
        sw = screen.get_width()
        sh = screen.get_height()
        w, h = 420, 640
        self.move(sw - w - 16, sh - h - 60)
        self._refresh_models()

    def hide(self):
        Gtk.Window.hide(self)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show()

    def update_state(self, state, lang="", engine=""):
        prev_state = self._cur_state
        if state == prev_state and engine == self._cur_engine:
            return
        
        self._cur_state = state
        if engine:
            self._cur_engine = engine

        GLib.idle_add(self._status_bar.update_state, state, lang, engine)
        GLib.idle_add(self._update_live_status, state, lang, engine)

        if state == "DICTATING":
            GLib.idle_add(self._start_btn.set_sensitive, False)
            GLib.idle_add(self._stop_btn.set_sensitive, True)
            # Auto-front the panel for non-streaming engines (VOSK) so the user
            # sees the live transcript immediately.
            if should_auto_show(engine, self._cfg):
                GLib.idle_add(self.show)
        else:
            GLib.idle_add(self._start_btn.set_sensitive, True)
            GLib.idle_add(self._stop_btn.set_sensitive, False)

        # Snapshot session history when dictation ends
        if prev_state == "DICTATING" and state == "IDLE":
            GLib.idle_add(self._promote_last_partial)
            GLib.idle_add(self._copy_session_on_stop)
            GLib.idle_add(self._snapshot_history)

    def _copy_session_on_stop(self):
        """Copy the full committed transcript to the clipboard (if enabled)."""
        if self._cfg.get("COPY_ON_STOP", "off") != "on":
            return
        if not self._history_session:
            return
        text = "\n".join(self._history_session)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)

    def _snapshot_history(self):
        if self._history_session:
            buf = self._hist_text.get_buffer()
            ts = time.strftime("%H:%M:%S")
            full_text = "\n".join(self._history_session)
            buf.insert(buf.get_end_iter(), f"[{ts}]\n{full_text}\n\n")
            self._history_session = []

    def destroy(self):
        self._sampler.stop()
        self._tailer.stop()
        Gtk.Window.destroy(self)


# ---------------------------------------------------------------------------
# Mock classes to bridge the older UI layouts cleanly
# ---------------------------------------------------------------------------
class EnginePanel_mock:
    ENGINES = [
        ("VOSK", "VOSK Engine", "vosk"),
        ("WHISPER", "Whisper Local Engine", "whisper"),
        ("WLK", "WhisperLiveKit Streaming", "wlk")
    ]
    WHISPER_MODELS_EN = ["tiny.en", "base.en", "small.en", "medium.en", "large-v2"]
    WHISPER_MODELS_AR = ["tiny", "base", "small", "medium"]

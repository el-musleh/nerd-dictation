import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import popup


def test_read_config_includes_new_keys(tmp_path, monkeypatch):
    """read_config() must surface every key the Settings tab can edit."""
    cfg_file = tmp_path / "config.sh"
    cfg_file.write_text(
        'COMPUTE_TYPE="int8"\n'
        'VAD_THRESHOLD="0.4"\n'
        'VAD_MIN_SILENCE_MS="300"\n'
        'LANG_MODELS="en:small.en,ar:small"\n'
        'AUTOSAVE_PATH="/tmp/out.txt"\n'
        'OUTPUT_FORMAT="srt"\n'
        'WLK_CHUNK="0.25"\n'
        'DICTATION_TARGET="Clipboard"\n'
        'WHISPER_EXPORT_PATH="/tmp/exp.srt"\n'
        'PANEL_IN_TASKBAR="on"\n'
        'COPY_ON_STOP="on"\n'
    )
    monkeypatch.setattr(popup, "CONFIG_FILE", str(cfg_file))
    cfg = popup.read_config()
    assert cfg.get("COMPUTE_TYPE") == "int8"
    assert cfg.get("VAD_THRESHOLD") == "0.4"
    assert cfg.get("VAD_MIN_SILENCE_MS") == "300"
    assert cfg.get("LANG_MODELS") == "en:small.en,ar:small"
    assert cfg.get("AUTOSAVE_PATH") == "/tmp/out.txt"
    assert cfg.get("OUTPUT_FORMAT") == "srt"
    assert cfg.get("WLK_CHUNK") == "0.25"
    assert cfg.get("DICTATION_TARGET") == "Clipboard"
    assert cfg.get("WHISPER_EXPORT_PATH") == "/tmp/exp.srt"
    assert cfg.get("PANEL_IN_TASKBAR") == "on"
    assert cfg.get("COPY_ON_STOP") == "on"

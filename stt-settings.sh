#!/bin/bash
# STT Settings — edit ~/.config/nerd-dictation/config.sh via a yad form.
# Mirrors tts-settings.sh (yad dialog). No notifications (tray-only).
notify-send() { :; }

CONFIG="$HOME/.config/nerd-dictation/config.sh"
[ -f "$CONFIG" ] || { echo "config.sh not found: $CONFIG" >&2; exit 1; }

# Source to read resolved values (config.sh is variable defs only).
source "$CONFIG"

ENGINE=${ENGLISH_ENGINE:-VOSK}
VTIMEOUT=${VOSK_TIMEOUT:-12}
WMODE=${WHISPER_DAEMON_MODE:-warm-cache}
EMODEL=${ENGLISH_WHISPER_MODEL:-small.en}
AMODEL=${ARABIC_WHISPER_MODEL:-small}

OFMT=${OUTPUT_FORMAT:-srt}

VT=${VAD_THRESHOLD:-0.5}
VS=${VAD_MIN_SILENCE_MS:-300}
PUNCT=${PUNCTUATE:-off}
WCHUNK=${WLK_CHUNK:-0.25}
WPOL=${WLK_POLICY:-localagreement}
CTYPE=${COMPUTE_TYPE:-int8}
AUTOL=${AUTO_LANG:-off}

# Build combobox lists with current value first (yad uses ! separator)
ENGINE_LIST="$ENGINE!VOSK!WHISPER!WLK"
WMODE_LIST="$WMODE!warm-cache!ipc"
EMODEL_LIST="$EMODEL!small.en!base.en!tiny.en!medium.en"
AMODEL_LIST="$AMODEL!small!base!medium"
OFMT_LIST="$OFMT!srt!vtt!json!text"
PUNCT_LIST="$PUNCT!off!on"
WPOL_LIST="$WPOL!localagreement!simulstreaming"
CTYPE_LIST="$CTYPE!int8!int8_float16!float16"
AUTOL_LIST="$AUTOL!off!on"

RESULTS=$(yad --title="STT Settings" --form --width=460 \
    --field="English Engine:CB"       "$ENGINE_LIST" \
    --field="VOSK Silence Timeout (s):NUM" "$VTIMEOUT" \
    --field="VAD Threshold (0-1):NUM" "$VT" \
    --field="VAD Min Silence (ms):NUM" "$VS" \
    --field="Whisper Mode:CB"         "$WMODE_LIST" \
    --field="English Whisper Model:CB" "$EMODEL_LIST" \
    --field="Arabic Whisper Model:CB"  "$AMODEL_LIST" \
    --field="Output Format:CB"        "$OFMT_LIST" \
    --field="Punctuate VOSK:CB"       "$PUNCT_LIST" \
    --field="WLK Chunk (s):NUM"       "$WCHUNK" \
    --field="WLK Policy:CB"           "$WPOL_LIST" \
    --field="Whisper Quantization:CB" "$CTYPE_LIST" \
    --field="Auto Language (WLK):CB"  "$AUTOL_LIST" \
    --field="Apply on next dictation start:LBL" "" \
    --button="Save":0 --button="Cancel":1)
EXIT=$?

if [ "$EXIT" -eq 0 ]; then
    E=$(echo  "$RESULTS" | cut -d'|' -f1)
    V=$(echo  "$RESULTS" | cut -d'|' -f2 | grep -o '[0-9]\+' | head -1); V=${V:-12}
    VT=$(echo  "$RESULTS" | cut -d'|' -f3 | grep -o '[0-9.]\+' | head -1); VT=${VT:-0.5}
    VS=$(echo  "$RESULTS" | cut -d'|' -f4 | grep -o '[0-9]\+' | head -1); VS=${VS:-300}
    W=$(echo  "$RESULTS" | cut -d'|' -f5)
    EM=$(echo "$RESULTS" | cut -d'|' -f6)
    AM=$(echo "$RESULTS" | cut -d'|' -f7)
    OF=$(echo "$RESULTS" | cut -d'|' -f8)
    PC=$(echo "$RESULTS" | cut -d'|' -f9)
    WC=$(echo "$RESULTS" | cut -d'|' -f10 | grep -o '[0-9.]\+' | head -1); WC=${WC:-0.25}
    WP=$(echo "$RESULTS" | cut -d'|' -f11)
    CT=$(echo "$RESULTS" | cut -d'|' -f12)
    AT=$(echo "$RESULTS" | cut -d'|' -f13)

    _set() {  # key newvalue -> replace or append in config.sh
        local k="$1" v="$2"
        if grep -qE "^$k=" "$CONFIG"; then
            sed -i "s|^$k=.*|$k=\"$v\"|" "$CONFIG"
        else
            echo "$k=\"$v\"" >> "$CONFIG"
        fi
    }
    _set ENGLISH_ENGINE        "$E"
    _set VOSK_TIMEOUT          "$V"
    _set VAD_THRESHOLD         "$VT"
    _set VAD_MIN_SILENCE_MS    "$VS"
    _set WHISPER_DAEMON_MODE   "$W"
    _set ENGLISH_WHISPER_MODEL "$EM"
    _set ARABIC_WHISPER_MODEL  "$AM"
    _set OUTPUT_FORMAT         "$OF"
    _set PUNCTUATE             "$PC"
    _set WLK_CHUNK             "$WC"
    _set WLK_POLICY            "$WP"
    _set COMPUTE_TYPE          "$CT"
    _set AUTO_LANG             "$AT"
fi

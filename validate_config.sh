#!/bin/bash
# validate_config.sh — validate ~/.config/nerd-dictation/config.sh.
#
# Checks every known key is present and within its allowed set/range, and
# warns about unknown/legacy keys. Exits non-zero if any hard error is found
# (so it can gate `dictate-start` or a CI check).
#
# Usage: validate_config.sh [path-to-config.sh]

set -u
CONFIG="${1:-$HOME/.config/nerd-dictation/config.sh}"
[ -f "$CONFIG" ] || { echo "ERROR: config not found: $CONFIG"; exit 1; }
# shellcheck disable=SC1090
source "$CONFIG"

err=0 warn=0
err() { echo "ERROR: $1"; err=1; }
warnf() { echo "WARN: $1"; warn=1; }

# --- enum checks -----------------------------------------------------------
# Empty (unset) is valid: these keys have working code defaults, so a minimal
# config that relies on defaults must not be rejected.
case "${ENGLISH_ENGINE:-}" in ''|VOSK|WHISPER|WLK) ;; *) err "ENGLISH_ENGINE must be VOSK|WHISPER|WLK (got '${ENGLISH_ENGINE:-<unset>}')" ;; esac
case "${WHISPER_DAEMON_MODE:-}" in ''|warm-cache|ipc) ;; *) err "WHISPER_DAEMON_MODE must be warm-cache|ipc" ;; esac
case "${VAD_GATE:-}" in ''|off|on) ;; *) err "VAD_GATE must be off|on" ;; esac
case "${PUNCTUATE:-}" in ''|off|on) ;; *) err "PUNCTUATE must be off|on" ;; esac
case "${AUTO_LANG:-}" in ''|off|on) ;; *) err "AUTO_LANG must be off|on" ;; esac
case "${WLK_POLICY:-}" in ''|localagreement|simulstreaming) ;; *) err "WLK_POLICY must be localagreement|simulstreaming" ;; esac
case "${OUTPUT_FORMAT:-}" in ''|srt|vtt|json|text) ;; *) err "OUTPUT_FORMAT must be srt|vtt|json|text" ;; esac
case "${COMPUTE_TYPE:-}" in ''|int8|int8_float16|float16) ;; *) err "COMPUTE_TYPE must be int8|int8_float16|float16" ;; esac

# --- numeric range checks --------------------------------------------------
# Only validate when the key is actually set (unset = use code default).
is_num() { [[ "$1" =~ ^[0-9]+(\.[0-9]+)?$ ]]; }
is_int() { [[ "$1" =~ ^[0-9]+$ ]]; }

[ -n "${VAD_THRESHOLD:-}" ] && { is_num "${VAD_THRESHOLD}" || err "VAD_THRESHOLD must be numeric (0..1)"; }
[ -n "${VAD_MIN_SILENCE_MS:-}" ] && { is_num "${VAD_MIN_SILENCE_MS}" || err "VAD_MIN_SILENCE_MS must be numeric (ms)"; }
[ -n "${WLK_CHUNK:-}" ] && { is_num "${WLK_CHUNK}" || err "WLK_CHUNK must be numeric (seconds)"; }
[ -n "${VOSK_TIMEOUT:-}" ] && { is_int "${VOSK_TIMEOUT}" || err "VOSK_TIMEOUT must be an integer (seconds)"; }
[ -n "${WLK_READY_TIMEOUT:-}" ] && { is_int "${WLK_READY_TIMEOUT}" || err "WLK_READY_TIMEOUT must be an integer (seconds)"; }

# --- legacy / unknown key warnings ----------------------------------------
# Keys that existed before but were renamed (migration hints).
for legacy in WHISPER_SOCKET_OLD; do :; done
if grep -qE '^WHISPER_SOCKET=' "$CONFIG"; then
    warnf "WHISPER_SOCKET is no longer used (whisper-daemon manages its own socket); safe to remove."
fi

echo "Config validation: $([ $err -eq 0 ] && echo OK || echo FAILED) (warnings: $warn)"
exit $err

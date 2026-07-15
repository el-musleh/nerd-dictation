#!/bin/bash
# lib_common.sh — shared bash helpers for nerd-dictation launcher scripts.
# Sourced (not executed) by dictate-start and the test suite.

# Resolve the Whisper model for a given language, honoring LANG_MODELS
# overrides (comma-separated "lang:model" pairs). Falls back to $2.
# Usage: resolve_whisper_model <lang> <fallback>
resolve_whisper_model() {
    local lang="$1" fallback="$2"
    local pair
    if [ -n "${LANG_MODELS:-}" ]; then
        local IFS=,
        for pair in $LANG_MODELS; do
            local k="${pair%%:*}" v="${pair##*:}"
            if [ "$k" = "$lang" ] && [ -n "$v" ]; then
                echo "$v"
                return
            fi
        done
        unset IFS
    fi
    echo "$fallback"
}

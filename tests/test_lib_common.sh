#!/bin/bash
# Unit test for lib_common.sh:resolve_whisper_model (C6 / G5).
# Sourced in a subshell so it never launches anything.
set -u
cd "$(dirname "$0")/.." || exit 1
source lib_common.sh

fail=0
check() {
    local desc="$1" expected="$2" got="$3"
    if [ "$expected" = "$got" ]; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc (expected '$expected', got '$got')"
        fail=1
    fi
}

# empty map -> fallback
unset LANG_MODELS
check "empty map falls back" "small.en" "$(resolve_whisper_model en small.en)"

# exact override
LANG_MODELS="en:base.en,ar:small"
check "en override" "base.en" "$(resolve_whisper_model en small.en)"
check "ar override" "small" "$(resolve_whisper_model ar tiny)"
check "de absent -> fallback" "medium" "$(resolve_whisper_model de medium)"

# single pair
LANG_MODELS="fr:large"
check "fr override single" "large" "$(resolve_whisper_model fr base.en)"

exit $fail

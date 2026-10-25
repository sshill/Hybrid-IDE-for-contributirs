#!/usr/bin/env bash
# Stop Hook (Kernel v0.9.9)
# Emits task complete audio chime if available, always exits with {}
set -euo pipefail

INPUT="$(cat || true)"
echo "$(date): Stop hook fired with input: ${INPUT}" >> /tmp/antigravity_hooks.log

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for SOUND in "${SCRIPT_DIR}/../sounds/task_complete.wav" "${HOME}/.gemini/config/sounds/task_complete.wav"; do
    if [ -f "$SOUND" ]; then
        if command -v paplay >/dev/null 2>&1; then
            paplay "$SOUND" >/dev/null 2>&1 &
        elif command -v aplay >/dev/null 2>&1; then
            aplay -q "$SOUND" >/dev/null 2>&1 &
        fi
        break
    fi
done

echo "{}"

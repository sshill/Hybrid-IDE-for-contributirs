#!/usr/bin/env bash
# PostToolUse Hook Wrapper (Kernel v0.9.9)
# Executes post_tool_hook.py to manage Runtime Circuit Breaker
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/post_tool_hook.py" "$@"

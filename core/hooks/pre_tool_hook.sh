#!/usr/bin/env bash
# Shell hook wrapper for Antigravity & IDE integrations (Kernel v0.9.9)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/pre_tool_hook.py" "$@"

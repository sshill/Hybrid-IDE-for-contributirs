#!/usr/bin/env bash
# PreInvocation Hook wrapper for Hybrid IDE Kernel v0.9.9
# Automatically initializes Brain-First telemetry and injects regulation guidance on new chat invocations.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/pre_invocation_hook.py" "$@"

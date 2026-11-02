#!/usr/bin/env bash
# ==============================================================================
# build_dist.sh — Hybrid IDE Distribution Package Builder (v0.9.12)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/core/engine/build_distribution.py" "$@"

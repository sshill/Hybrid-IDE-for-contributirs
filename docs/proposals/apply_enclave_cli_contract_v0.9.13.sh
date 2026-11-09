#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel)"
PATCH_FILE="$SCRIPT_DIR/enclave_cli_contract_v0.9.13.patch"

if [[ ! -f "$PATCH_FILE" ]]; then
    printf 'Patch file not found: %s\n' "$PATCH_FILE" >&2
    exit 1
fi

cd "$REPO_ROOT"

if git apply --check "$PATCH_FILE"; then
    git apply "$PATCH_FILE"
    printf 'Patch applied.\n'
elif git apply --reverse --check "$PATCH_FILE"; then
    printf 'Patch is already applied; continuing with verification.\n'
else
    printf 'Patch does not apply cleanly. No files were changed by this batch.\n' >&2
    exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
python3 -m py_compile \
    core/enclave/enclave_daemon.py \
    core/verify/test_provenance_security.py

python3 -m unittest -q \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_cli_apply_contract \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_cli_daemon_payload \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_cli_query_file_contract \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_http_apply_contract \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_tools_help_schema \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_patch_mode_simulation \
    core.verify.test_provenance_security.TestProvenanceSecurity.test_enclave_synthesis_tier1_atomic_apply

printf 'Patch verification passed. Review `git diff` before committing.\n'

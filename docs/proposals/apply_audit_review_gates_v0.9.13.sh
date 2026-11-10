#!/usr/bin/env bash
# Apply the deterministic audit-review gates and run focused verification.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
PATCH_FILE="$SCRIPT_DIR/audit_review_gates_v0.9.13.patch"

git -C "$REPO_ROOT" apply --check "$PATCH_FILE"
git -C "$REPO_ROOT" apply "$PATCH_FILE"
cd "$REPO_ROOT"

python3 -m unittest \
  core.verify.test_audit_gate \
  core.verify.test_provenance_security.TestProvenanceSecurity.test_audit_transcript_receipts_and_plan_marker_are_immutable \
  core.verify.test_provenance_security.TestProvenanceSecurity.test_audit_routing_is_fail_closed_and_ignores_stale_attestation \
  core.verify.test_provenance_security.TestProvenanceSecurity.test_audit_query_requires_structured_report_and_blocks_identical_repeat \
  core.verify.test_provenance_security.TestProvenanceSecurity.test_copilot_audit_output_is_streamed_to_terminal

python3 -m py_compile \
  core/verify/audit_gate.py \
  core/verify/test_audit_gate.py \
  core/enclave/enclave_daemon.py \
  core/engine/diagnostic_runner.py \
  core/hooks/pre_tool_hook.py \
  core/hooks/pre_invocation_hook.py \
  core/verify/phase5_verify.py

git diff --check
printf 'Audit review gates applied and focused checks passed. Review git diff before committing.\n'

# Proposal: CLI and Enclave Contract Repair (v0.9.13)

**Status:** Implementation proposal
**Repository baseline:** `main` at `0017e850e7755d7738f5d92372800acc0e899646`
**Scope:** CLI `--target` / `--query` behavior, `/apply` request validation, runtime tool schema, and `ENCLAVE_INTERFACE.md`.

## Problem

The CLI advertises `--target`, but its apply payload reads `args.allow_multiple`
without declaring that argparse option. Consequently, invoking `--target` can
fail with `AttributeError` before the Enclave handles the request. The
replacement engine already supports `allow_multiple` and the HTTP `/apply`
handler already reads it, so the CLI and the underlying apply contract are
inconsistent.

The published interface guide also describes commands and behavior that do not
match the implementation: it presents nonexistent subcommands, calls `--query`
a JMESPath expression, and documents `--target` as a service URI. In addition,
the runtime help and health/diagnostics responses report v0.9.12 although the
CLI identifies itself as v0.9.13.

## Goals

1. Make the CLI, HTTP handler, runtime help schema, and interface guide describe
   the same implemented operations and defaults.
2. Keep patching deterministic: require exactly one match by default; permit
   replacing all matches only with an explicit opt-in.
3. Reject malformed apply arguments before file access or mutation.
4. Ensure `--json-output` for `--target` produces parseable JSON on stdout.
5. Add regression tests that exercise CLI and HTTP behavior without calling
   external model providers.

## Proposed implementation

### 1. Repair and validate the CLI apply arguments

In `core/enclave/enclave_daemon.py`:

- Add `--allow-multiple` as `store_true`; its default must remain `false`.
- Include the parsed value in the payload passed to either the local
  `enclave_apply` function or HTTP `POST /apply`.
- Validate `target_path` as a non-empty string.
- Validate `allow_multiple` as a JSON boolean for HTTP requests. Do not coerce
  strings such as `"false"` to booleans.
- In patch mode, require `start_line` and `end_line` together when either is
  supplied. Require integer line numbers (JSON booleans are not valid integers
  here); the replacement engine remains responsible for range bounds and
  matching.
- Preserve the existing safe default: without `--allow-multiple`, a target
  occurring zero or multiple times is rejected before writing.

### 2. Keep JSON output machine-readable

When `--target --json-output` performs a local apply, send informational
passport/provenance messages emitted during the operation to stderr and reserve
stdout for the JSON receipt. Preserve existing human-readable output when
`--json-output` is not selected. Add a test that parses stdout as exactly one
JSON value.

### 3. Synchronize runtime schema and version

Update `get_tools_help()` to version `0.9.13`, describe the actual
`POST /apply` and `POST /query` field names/defaults, identify
`--allow-multiple`, explain the paired inclusive line range, and list the
implemented health/help/diagnostics routes. Set `/health`, `/diagnostics`, and
CLI `--check-all` version fields to `0.9.13` as well.

Do not claim that a successful process exit or `status: SUCCESS` proves a
semantic audit passed. The current query path considers a non-`ERROR:` model
response successful, and an existing attestation marker may affect routing.
Document this limitation; fixing audit verdict semantics and attestation
binding is explicitly out of scope for this proposal.

### 4. Replace the stale interface guide

Rewrite `core/enclave/ENCLAVE_INTERFACE.md` as an operator contract based on
the current parser and HTTP handler:

- Explain that `--target` is a filesystem path and that the CLI has flags, not
  the documented `run` / `apply` / `query` subcommands.
- Distinguish CLI `--query` and `--query-file` from HTTP `POST /query`; specify
  that a query-file is the full prompt and does not receive an implicit audit
  instruction.
- Explain the CLI `--mode` default versus the HTTP `/query` mode default.
- Document `/apply` parameter names, patch matching rules, `--json-output`,
  return statuses, and bounded examples.
- List only implemented HTTP routes and CLI flags, and identify operations
  that are CLI-only.
- State operational limitations that affect safe use, including loopback
  service exposure, local fallback after a daemon-call error, and the fact
  that a successful query response is not proof of an independent audit.

Keep the document factual: do not describe intended pipeline phases or
security guarantees as implemented behavior unless the code enforces them.

### 5. Add regression tests

Extend `core/verify/test_provenance_security.py` or add a focused stdlib
`unittest` module. Tests must use temporary files, an ephemeral loopback HTTP
port, and mocked model calls where applicable; they must not require API
credentials or external providers.

Cover at least:

- CLI `--target` synthesis no longer raises `AttributeError`.
- CLI default patch behavior rejects multiple matches without changing bytes.
- A unique patch succeeds; an incomplete line range fails; explicit
  `--allow-multiple` replaces all matches.
- CLI passes `allow_multiple` through to a running daemon.
- HTTP `/apply` enforces boolean and paired-integer inputs and preserves the
  file on rejected requests.
- HTTP `/help` and `/health` expose the expected v0.9.13 contract.
- `--query-file` takes precedence over `--query`, forwards the file contents
  and explicit mode/tier, and leaves JSON stdout parseable.
- Existing synthesis, patch, and schema tests continue to pass.

## Acceptance criteria

- `python3 core/enclave/enclave_daemon.py --help` lists `--allow-multiple`.
- `python3 core/enclave/enclave_daemon.py --help-tools` emits valid JSON whose
  schema version is `0.9.13`.
- A normal `--target` call reaches apply logic instead of failing on a missing
  argparse attribute.
- A rejected patch does not change the target file; multi-match replacement
  occurs only when explicitly enabled.
- CLI JSON output parses without filtering log lines.
- The focused regression tests and the repository's Phase 5 verification pass.
- The interface guide matches actual code and clearly separates verified
  behavior from limitations or future work.

## Implementation order and boundaries

1. Add the CLI flag and request validation.
2. Add focused regression tests and confirm safe patch defaults.
3. Synchronize the runtime schema/version and the interface guide.
4. Run focused tests, then `python3 core/verify/phase5_verify.py`.
5. Review the final diff and confirm only the planned files changed.

This proposal does **not** authorize changing the plan approval gate, query
success/verdict semantics, attestation behavior, context filtering, Git First
hooks, or the architecture diagram. Those require separate designs and
verification.

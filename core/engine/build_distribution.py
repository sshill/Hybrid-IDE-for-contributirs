#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_distribution.py — Hybrid IDE Kernel v0.9.11 Distribution Package Builder
Constructs an isolated, zero-credential distribution package for clean install
on Debian 13 (Trixie) and Linux environments (Python 3.10+ stdlib only).
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys

sys.dont_write_bytecode = True

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DIST_ROOT = os.path.join(PROJECT_ROOT, "distribution", "hybrid-ide")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

INSTALL_SH_CONTENT = """#!/usr/bin/env bash
# ==============================================================================
# install.sh — Hybrid IDE Kernel v0.9.11 Standalone Installer for Debian 13 & Linux
# Safe, idempotent installation with automatic backup, non-root execution,
# and zero external PyPI dependencies (Python 3.10+ stdlib only).
# ==============================================================================
set -euo pipefail

DRY_RUN=false
UNINSTALL=false
TARGET_DIR="${HOME}/.gemini/config/plugins/hybrid-ide"
BACKUP_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${HOME}/.gemini/config/plugins/hybrid-ide.bak-${BACKUP_TIMESTAMP}"

show_help() {
    cat << HELP_EOF
Usage: ./install.sh [OPTIONS]

Options:
  --dry-run      Simulate installation without making filesystem changes.
  --uninstall    Safely remove the installed hybrid-ide plugin.
  -h, --help     Show this help message.

Environment:
  Target Directory: ${TARGET_DIR}
  Prerequisites:     bash (>=4.0), python3 (>=3.10), git
HELP_EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

if [[ "${UNINSTALL}" == "true" ]]; then
    echo "=== Uninstalling Hybrid IDE Plugin ==="
    if [[ -d "${TARGET_DIR}" ]]; then
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "[DRY-RUN] Would backup ${TARGET_DIR} to ${BACKUP_DIR} and remove it."
        else
            echo "Creating safety backup before removal: ${BACKUP_DIR}"
            cp -r "${TARGET_DIR}" "${BACKUP_DIR}"
            rm -rf "${TARGET_DIR}"
            echo "Successfully uninstalled ${TARGET_DIR}. Safety backup preserved at ${BACKUP_DIR}."
        fi
    else
        echo "Nothing to uninstall: ${TARGET_DIR} does not exist."
    fi
    exit 0
fi

echo "======================================================================"
echo "🚀 Hybrid IDE Kernel v0.9.11 Installer (Debian 13 / Linux)"
echo "======================================================================"

# Check prerequisites
echo "[Step 1/5] Checking prerequisites..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not installed." >&2
    exit 1
fi
PYTHON_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MAJOR="$(echo "${PYTHON_VER}" | cut -d. -f1)"
PYTHON_MINOR="$(echo "${PYTHON_VER}" | cut -d. -f2)"

if [[ "${PYTHON_MAJOR}" -lt 3 ]] || [[ "${PYTHON_MAJOR}" -eq 3 && "${PYTHON_MINOR}" -lt 10 ]]; then
    echo "ERROR: Python 3.10+ required. Detected Python ${PYTHON_VER}." >&2
    exit 1
fi
echo "  - Python: ${PYTHON_VER} (OK, stdlib only)"

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required but not installed." >&2
    exit 1
fi
echo "  - Git: $(git --version) (OK)"

DIST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify checksums (P1: Hard failure on integrity error)
if [[ -f "${DIST_DIR}/SHA256SUMS" ]]; then
    echo "[Step 2/5] Verifying package integrity (SHA256)..."
    if ! (cd "${DIST_DIR}" && sha256sum --check --status SHA256SUMS); then
        echo "ERROR: SHA256 checksum mismatch! Package integrity compromised." >&2
        exit 1
    fi
    echo "  - Integrity check passed (SHA256 verified)."
else
    echo "ERROR: SHA256SUMS file missing from distribution package." >&2
    exit 1
fi

# Backup existing installation
echo "[Step 3/5] Managing installation target and backups..."
if [[ -d "${TARGET_DIR}" ]]; then
    echo "  - Existing installation detected at ${TARGET_DIR}."
    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "[DRY-RUN] Would create backup at: ${BACKUP_DIR}"
    else
        cp -r "${TARGET_DIR}" "${BACKUP_DIR}"
        echo "  - Backup created: ${BACKUP_DIR}"
    fi
fi

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[DRY-RUN] Would install to: ${TARGET_DIR}"
    echo "[DRY-RUN] Dry run complete. No files were modified."
    exit 0
fi

# Perform installation with clean deployment
echo "[Step 4/5] Deploying plugin files to ${TARGET_DIR}..."
rm -rf "${TARGET_DIR}/bin" "${TARGET_DIR}/rules" "${TARGET_DIR}/skills"
mkdir -p "${TARGET_DIR}/bin"
mkdir -p "${TARGET_DIR}/rules"
mkdir -p "${TARGET_DIR}/skills/reglament"
mkdir -p "${TARGET_DIR}/skills/bridge"

cp -r "${DIST_DIR}/bin/"* "${TARGET_DIR}/bin/"
cp -r "${DIST_DIR}/rules/"* "${TARGET_DIR}/rules/"
cp "${DIST_DIR}/plugin/plugin.json" "${TARGET_DIR}/plugin.json"

if [[ -d "${DIST_DIR}/skills/reglament" ]]; then
    cp -r "${DIST_DIR}/skills/reglament/"* "${TARGET_DIR}/skills/reglament/"
fi
if [[ -d "${DIST_DIR}/skills/bridge" ]]; then
    cp -r "${DIST_DIR}/skills/bridge/"* "${TARGET_DIR}/skills/bridge/"
fi

# Generate real hooks.json from template with actual $HOME
sed "s|{{HOME}}|${HOME}|g" "${DIST_DIR}/plugin/hooks.template.json" > "${TARGET_DIR}/hooks.json"
echo "  - Generated: ${TARGET_DIR}/hooks.json"

# Set permissions
chmod +x "${TARGET_DIR}/bin/"*.sh
chmod +x "${TARGET_DIR}/bin/"*.py
chmod 644 "${TARGET_DIR}/hooks.json" "${TARGET_DIR}/plugin.json" "${TARGET_DIR}/rules/AGENTS.md"

# Configure .env safely if missing
if [[ ! -f "${TARGET_DIR}/.env" ]]; then
    cp "${DIST_DIR}/.env.example" "${TARGET_DIR}/.env"
    chmod 600 "${TARGET_DIR}/.env"
    echo "  - Created default configuration: ${TARGET_DIR}/.env (permissions: 600)"
else
    echo "  - Existing configuration preserved: ${TARGET_DIR}/.env"
fi

# Run post-install self-verification (P2: Execute real verification)
echo "[Step 5/5] Running post-install self-verification..."
if [[ -f "${DIST_DIR}/verify.sh" ]]; then
    "${DIST_DIR}/verify.sh" --target "${TARGET_DIR}"
else
    python3 "${TARGET_DIR}/bin/phase5_verify.py"
fi

echo "======================================================================"
echo "✅ Hybrid IDE Kernel v0.9.9 successfully installed!"
echo "   Plugin path: ${TARGET_DIR}"
echo "   Next steps:"
echo "   1. Configure API keys in: ${TARGET_DIR}/.env (chmod 600)"
echo "   2. Restart or open your Antigravity IDE session"
echo "   3. Type /reglament in any conversation to run the 4-Tier AI Battle Test"
echo "======================================================================"
"""

VERIFY_SH_CONTENT = """#!/usr/bin/env bash
# ==============================================================================
# verify.sh — Hybrid IDE Distribution Package Verification Script
# Runs non-destructive health checks across Python, ASTs, and Framework rules.
# ==============================================================================
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

TARGET_DIR="${HOME}/.gemini/config/plugins/hybrid-ide"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

echo "=== Verifying Hybrid IDE Target: ${TARGET_DIR} ==="

if [[ ! -d "${TARGET_DIR}/bin" ]]; then
    echo "ERROR: Target bin directory not found: ${TARGET_DIR}/bin" >&2
    exit 1
fi

# 1. Check Python stdlib syntax on all scripts
echo "1. Checking Python syntax (py_compile)..."
for pyfile in "${TARGET_DIR}/bin/"*.py; do
    if [[ -f "${pyfile}" ]]; then
        python3 -m py_compile "${pyfile}"
    fi
done
echo "   -> All Python tools pass py_compile."

# 2. Check bash syntax on hooks
echo "2. Checking Bash syntax (bash -n)..."
for shfile in "${TARGET_DIR}/bin/"*.sh; do
    if [[ -f "${shfile}" ]]; then
        bash -n "${shfile}"
    fi
done
echo "   -> All hook shell scripts pass syntax validation."

# 3. Check Phase 5 verification
if [[ -f "${TARGET_DIR}/bin/phase5_verify.py" ]]; then
    echo "3. Executing Phase 5 verification engine..."
    python3 "${TARGET_DIR}/bin/phase5_verify.py"
fi

# 4. Check permissions
echo "4. Checking security permissions..."
if [[ -f "${TARGET_DIR}/.env" ]]; then
    PERMS="$(stat -c %a "${TARGET_DIR}/.env")"
    if [[ "${PERMS}" != "600" ]]; then
        echo "WARNING: ${TARGET_DIR}/.env has permissions ${PERMS}, changing to 600..."
        chmod 600 "${TARGET_DIR}/.env"
    fi
fi
echo "   -> Permissions verified."

find "${TARGET_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "=== All Verification Checks Passed ==="
"""

ENV_EXAMPLE_CONTENT = """# ==============================================================================
# Hybrid IDE v0.9.11 Environment Configuration Template
# Place credentials in ~/.gemini/config/plugins/hybrid-ide/.env (chmod 600)
# ==============================================================================

# Tier 1: Local Edge Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:1.5b

# Tier 2: Cloud Fallback Hub (Groq / OpenRouter)
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b

# Tier 4: Claude Sonnet Arbiter (Optional direct Anthropic API key)
# ANTHROPIC_API_KEY=

# Tier 4.5: GitHub Copilot CLI token (or authenticate via `gh auth login`)
# GITHUB_TOKEN=
"""

HOOKS_TEMPLATE_JSON = """{
  "PreInvocation": [
    {
      "type": "command",
      "command": "{{HOME}}/.gemini/config/plugins/hybrid-ide/bin/pre_invocation_hook.sh"
    }
  ],
  "PreToolUse": [
    {
      "type": "command",
      "command": "{{HOME}}/.gemini/config/plugins/hybrid-ide/bin/pre_tool_hook.sh"
    }
  ],
  "PostToolUse": [
    {
      "type": "command",
      "command": "{{HOME}}/.gemini/config/plugins/hybrid-ide/bin/post_tool_hook.sh"
    }
  ],
  "Stop": [
    {
      "type": "command",
      "command": "{{HOME}}/.gemini/config/plugins/hybrid-ide/bin/stop_hook.sh"
    }
  ]
}
"""

PLUGIN_JSON_CONTENT = """{
  "name": "hybrid-ide",
  "version": "1.0.0",
  "description": "Hybrid IDE Framework Core & Constitutional Kernel v0.9.11",
  "author": "Serhii Khylevych",
  "hooks": "hooks.json"
}
"""

README_MD_CONTENT = """# Hybrid IDE Distribution Package (v0.9.11)

Self-contained distribution package of the Hybrid IDE Constitutional Kernel and Orchestration Framework.
Designed for Debian 13 (Trixie) and Linux environments with zero PyPI dependencies (Python 3.10+ stdlib only).

## Package Contents
- `bin/`: Core tools (`phase1_inspect.py`, `diagnostic_runner.py`, `phase2_router.py`, `phase4_provenance.py`, `phase5_verify.py`, `validate_general_policy.py`) and lifecycle hooks (`pre_invocation_hook`, `pre_tool_hook`, `post_tool_hook`, `stop_hook`).
- `rules/`: Global constitutional kernel (`AGENTS.md`).
- `plugin/`: Plugin metadata (`plugin.json`) and portable template (`hooks.template.json`).
- `skills/`: Standard skills (`reglament`, `bridge`).
- `.env.example`: Configuration template for AI models (Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet, Tier 4.5 Copilot CLI).
- `install.sh`: Idempotent installer with `--dry-run`, `--uninstall`, and automatic backups.
- `verify.sh`: Post-installation verification suite.

## Quick Installation on Debian 13
```bash
./install.sh
```
To preview changes without touching the filesystem:
```bash
./install.sh --dry-run
```
To uninstall:
```bash
./install.sh --uninstall
```
"""


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def make_executable(path: str):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_package():
    print(f"=== [1/6] Cleaning and preparing {DIST_ROOT} ===")
    if os.path.exists(DIST_ROOT):
        shutil.rmtree(DIST_ROOT)
    os.makedirs(os.path.join(DIST_ROOT, "bin"), exist_ok=True)
    os.makedirs(os.path.join(DIST_ROOT, "rules"), exist_ok=True)
    os.makedirs(os.path.join(DIST_ROOT, "plugin"), exist_ok=True)
    for sk in ("reglament", "bridge", "principal", "supervisor"):
        os.makedirs(os.path.join(DIST_ROOT, "skills", sk), exist_ok=True)

    print("=== [2/6] Packaging Core Framework Tools and Hooks ===")
    core_files = [
        os.path.join(PROJECT_ROOT, "core", "engine", "diagnostic_runner.py"),
        os.path.join(PROJECT_ROOT, "core", "engine", "validate_migration_content.py"),
        os.path.join(PROJECT_ROOT, "core", "inspect", "phase1_inspect.py"),
        os.path.join(PROJECT_ROOT, "core", "router", "phase2_router.py"),
        os.path.join(PROJECT_ROOT, "core", "provenance", "phase4_provenance.py"),
        os.path.join(PROJECT_ROOT, "core", "verify", "phase5_verify.py"),
        os.path.join(PROJECT_ROOT, "core", "verify", "validate_general_policy.py"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "pre_invocation_hook.py"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "pre_invocation_hook.sh"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "pre_tool_hook.py"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "pre_tool_hook.sh"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "post_tool_hook.py"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "post_tool_hook.sh"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "stop_hook.sh"),
        os.path.join(PROJECT_ROOT, "core", "hooks", "__init__.py"),
        os.path.join(PROJECT_ROOT, "core", "enclave", "enclave_daemon.py"),
        os.path.join(PROJECT_ROOT, "core", "enclave", "__init__.py")
    ]

    for src in core_files:
        if not os.path.exists(src):
            raise FileNotFoundError(f"Missing core file: {src}")
        dst = os.path.join(DIST_ROOT, "bin", os.path.basename(src))
        shutil.copy2(src, dst)
        if dst.endswith(".sh") or dst.endswith(".py"):
            make_executable(dst)

    print("=== [3/6] Packaging Rules, Manifest, and Skills ===")
    # Global AGENTS.md rule & GEMINI policy template for 37/37 verification
    kernel_rule = os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md")
    if os.path.exists(kernel_rule):
        shutil.copy2(kernel_rule, os.path.join(DIST_ROOT, "rules", "AGENTS.md"))
    else:
        shutil.copy2(os.path.join(PROJECT_ROOT, "AGENTS.md"), os.path.join(DIST_ROOT, "rules", "AGENTS.md"))

    gemini_template = os.path.join(PROJECT_ROOT, "config", "GEMINI.template.md")
    if os.path.exists(gemini_template):
        shutil.copy2(gemini_template, os.path.join(DIST_ROOT, "rules", "GEMINI.template.md"))

    # Manifest and Template
    with open(os.path.join(DIST_ROOT, "plugin", "plugin.json"), "w", encoding="utf-8") as f:
        f.write(PLUGIN_JSON_CONTENT)
    with open(os.path.join(DIST_ROOT, "plugin", "hooks.template.json"), "w", encoding="utf-8") as f:
        f.write(HOOKS_TEMPLATE_JSON)
    with open(os.path.join(DIST_ROOT, ".env.example"), "w", encoding="utf-8") as f:
        f.write(ENV_EXAMPLE_CONTENT)

    # Skills
    for skill in ("reglament", "bridge", "principal", "supervisor"):
        cand_paths = [
            os.path.join(PROJECT_ROOT, "skills", skill, "SKILL.md"),
            os.path.expanduser(f"~/.gemini/config/skills/{skill}/SKILL.md"),
            os.path.expanduser(f"~/.gemini/config/plugins/hybrid-ide/skills/{skill}/SKILL.md"),
            os.path.join(PROJECT_ROOT, "templates", f"{skill}_SKILL.md")
        ]
        found = False
        for p in cand_paths:
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(DIST_ROOT, "skills", skill, "SKILL.md"))
                found = True
                break
        if not found:
            print(f"Warning: SKILL.md for {skill} not found, skipped.")

    print("=== [4/6] Writing Installer, Verifier, and Package Docs ===")
    install_sh = os.path.join(DIST_ROOT, "install.sh")
    with open(install_sh, "w", encoding="utf-8") as f:
        f.write(INSTALL_SH_CONTENT)
    make_executable(install_sh)

    verify_sh = os.path.join(DIST_ROOT, "verify.sh")
    with open(verify_sh, "w", encoding="utf-8") as f:
        f.write(VERIFY_SH_CONTENT)
    make_executable(verify_sh)

    with open(os.path.join(DIST_ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_MD_CONTENT)

    # Generate root build_dist.sh wrapper
    root_build_sh = os.path.join(PROJECT_ROOT, "build_dist.sh")
    root_sh_content = (
        "#!/usr/bin/env bash\\n"
        "# ==============================================================================\\n"
        "# build_dist.sh — Hybrid IDE Distribution Package Builder (v0.9.11)\\n"
        "# ==============================================================================\\n"
        "set -euo pipefail\\n\\n"
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\\n'
        'exec python3 "${SCRIPT_DIR}/core/engine/build_distribution.py" "$@"\\n'
    ).replace("\\n", "\n")
    with open(root_build_sh, "w", encoding="utf-8") as f:
        f.write(root_sh_content)
    make_executable(root_build_sh)

    # Register root build_dist.sh in provenance ledger
    prov_script = os.path.join(PROJECT_ROOT, "core", "provenance", "phase4_provenance.py")
    if os.path.exists(prov_script):
        try:
            from core.provenance.phase4_provenance import register_provenance
            register_provenance(
                root_build_sh,
                model="openai/gpt-oss-120b",
                source_prompt="Hybrid IDE v0.9.11 Distribution Package Builder wrapper"
            )
        except Exception as e:
            print(f"Notice: provenance registration exception: {e}")

    print("=== [5/6] Generating SHA256SUMS ===")
    for root, dirs, files in os.walk(DIST_ROOT, topdown=False):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    checksum_lines = []
    for root, dirs, files in os.walk(DIST_ROOT):
        for fname in sorted(files):
            if fname == "SHA256SUMS":
                continue
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, DIST_ROOT)
            sha = compute_sha256(fpath)
            checksum_lines.append(f"{sha}  {relpath}\n")

    checksum_lines.sort(key=lambda x: x.split()[1])
    with open(os.path.join(DIST_ROOT, "SHA256SUMS"), "w", encoding="utf-8") as f:
        f.writelines(checksum_lines)

    print("=== [6/6] Running Zero-Credentials and Zero-Host Audit ===")
    leak_patterns = [
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),
        re.compile(r"gsk_[0-9A-Za-z]{20,}"),
        re.compile(r"sk-ant-[0-9A-Za-z]{20,}"),
        re.compile(r"ghp_[0-9A-Za-z]{20,}"),
        re.compile(r"/home/hills")
    ]
    leaks_found = 0
    for root, dirs, files in os.walk(DIST_ROOT):
        for fname in files:
            if ".secret" in fname.lower() or fname.endswith(".key"):
                print(f"❌ SECRET FILE DETECTED in package: {fname}")
                leaks_found += 1
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, 1):
                    for pat in leak_patterns:
                        if pat.search(line):
                            print(f"❌ LEAK DETECTED in {os.path.relpath(fpath, DIST_ROOT)}: line {line_idx}: {line.strip()[:60]}")
                            leaks_found += 1

    if leaks_found > 0:
        raise ValueError(f"Build failed: {leaks_found} credentials/host paths detected in distribution package!")

    print("======================================================================")
    print(f"✅ Distribution package successfully built at: {DIST_ROOT}")
    print(f"   Files packaged: {len(checksum_lines)}")
    print("   Zero API keys, zero hardcoded host paths verified.")
    print("======================================================================")


if __name__ == "__main__":
    build_package()

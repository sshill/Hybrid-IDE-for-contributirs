#!/usr/bin/env python3
import sys
import os
import py_compile
import traceback
import runpy

import subprocess

# Prevent creation of .pyc files
sys.dont_write_bytecode = True

def compile_python_files(root_path):
    """
    Recursively compile all .py files under ``root_path``.
    Returns a list of (file_path, exception) tuples for files that failed to compile.
    """
    failures = []
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                py_compile.compile(file_path, doraise=True)
            except Exception as exc:
                failures.append((file_path, exc))
    return failures

def run_validator(validator_path, policy_path):
    """
    Execute the validator script located at ``validator_path`` with explicit policy path.
    """
    if not os.path.isfile(validator_path):
        raise FileNotFoundError(f"Validator script not found: {validator_path}")

    res = subprocess.run([sys.executable, validator_path, "--policy", policy_path])
    if res.returncode != 0:
        sys.exit(res.returncode)

import argparse

def main():
    parser = argparse.ArgumentParser(description="Phase 5 Deterministic Verification Runner")
    parser.add_argument("--remote-ci", action="store_true", help="Також перевірити віддалений GitHub Actions CI")
    parser.add_argument("--commit", type=str, default=None, help="Commit SHA для віддаленого CI")
    args, _ = parser.parse_known_args()

    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(os.path.join(SCRIPT_DIR, '..', '..', 'core')):
            REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
            CORE_DIR = os.path.join(REPO_ROOT, 'core')
            VALIDATOR_PATH = os.path.join(CORE_DIR, 'verify', 'validate_general_policy.py')
        else:
            REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
            CORE_DIR = SCRIPT_DIR
            VALIDATOR_PATH = os.path.join(SCRIPT_DIR, 'validate_general_policy.py')

        # Determine policy path (GEMINI.template.md contains 37/37 structural rules)
        policy_cands = [
            os.path.join(REPO_ROOT, 'config', 'GEMINI.template.md'),
            os.path.join(SCRIPT_DIR, '..', 'rules', 'GEMINI.template.md'),
            os.path.join(REPO_ROOT, 'rules', 'GEMINI.template.md'),
            os.path.join(REPO_ROOT, 'GEMINI.md'),
            os.path.join(SCRIPT_DIR, '..', 'rules', 'AGENTS.md'),
            os.path.expanduser('~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md')
        ]
        policy_path = None
        for p in policy_cands:
            if os.path.isfile(p):
                policy_path = p
                break
        if not policy_path:
            policy_path = policy_cands[0]

        # 1. Compile all Python files under CORE_DIR
        if os.path.isdir(CORE_DIR):
            compile_errors = compile_python_files(CORE_DIR)
            if compile_errors:
                sys.stderr.write("Syntax errors detected in the following files:\n")
                for file_path, exc in compile_errors:
                    sys.stderr.write(f"  {file_path}: {exc}\n")
                sys.exit(1)

        # 1.5. Unit test for Anchored Grounding Gate (Anti-Echo / Anti-Vague validation)
        diag_path = os.path.join(REPO_ROOT, 'core', 'engine', 'diagnostic_runner.py')
        if os.path.isfile(diag_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("diag_test", diag_path)
            diag_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(diag_mod)
            vague_check = diag_mod.check_anchor_spec("знайди щось про персонажа")
            if vague_check.get("anchored"):
                sys.stderr.write("❌ Anchored Grounding Unit Test Failed: Vague query was not flagged!\n")
                sys.exit(1)
            anchored_check = diag_mod.check_anchor_spec("перевір FormID 0x0302F3FF у MercyRecruitmentQuestScript.psc")
            if not anchored_check.get("anchored"):
                sys.stderr.write("❌ Anchored Grounding Unit Test Failed: Grounded query was rejected!\n")
                sys.exit(1)

        # 1.6. Run provenance security and passport unit tests suite (30/30 tests)
        prov_test_path = os.path.join(REPO_ROOT, 'core', 'verify', 'test_provenance_security.py')
        if os.path.isfile(prov_test_path):
            res_prov = subprocess.run([sys.executable, "-m", "unittest", "core.verify.test_provenance_security"], cwd=REPO_ROOT)
            if res_prov.returncode != 0:
                sys.stderr.write("❌ Provenance Security Unit Tests Failed!\n")
                sys.exit(res_prov.returncode)

        # 1.7. Run Chat Context Auditor tests and active session audit (Kernel v0.9.12)
        chat_test_path = os.path.join(REPO_ROOT, 'core', 'verify', 'test_chat_context_auditor.py')
        if os.path.isfile(chat_test_path):
            res_chat_test = subprocess.run([sys.executable, "-m", "unittest", "core.verify.test_chat_context_auditor"], cwd=REPO_ROOT)
            if res_chat_test.returncode != 0:
                sys.stderr.write("❌ Chat Context Auditor Unit Tests Failed!\n")
                sys.exit(res_chat_test.returncode)

        chat_auditor_path = os.path.join(REPO_ROOT, 'core', 'verify', 'chat_context_auditor.py')
        if os.path.isfile(chat_auditor_path):
            is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
            if is_ci:
                sys.stdout.write("ℹ️ CI Environment detected: skipping interactive chat transcript audit.\n")
            else:
                res_chat_audit = subprocess.run([sys.executable, chat_auditor_path, "--current-session", "--strict"], cwd=REPO_ROOT)
                if res_chat_audit.returncode != 0:
                    sys.stderr.write("❌ Phase 4/Phase 5 Chat Context Audit Violation Detected! Release blocked.\n")
                    sys.exit(res_chat_audit.returncode)

        # 2. Run the general policy validator with deterministic policy path
        run_validator(VALIDATOR_PATH, policy_path)

        # 3. Optional remote CI verification
        if args.remote_ci:
            remote_verifier = os.path.join(CORE_DIR, 'verify', 'verify_remote_ci.py')
            cmd = [sys.executable, remote_verifier]
            if args.commit:
                cmd.extend(["--commit", args.commit])
            res = subprocess.run(cmd)
            if res.returncode != 0:
                sys.exit(res.returncode)

        # If we reach this point, everything passed
        sys.stdout.write("Phase 5 verification succeeded.\n")
        sys.exit(0)

    except Exception as e:
        sys.stderr.write("An unexpected error occurred during verification:\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()

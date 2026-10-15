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

def main():
    try:
        # Determine repository root (two levels up from this file)
        REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        CORE_DIR = os.path.join(REPO_ROOT, 'core')
        VALIDATOR_PATH = os.path.join(CORE_DIR, 'verify', 'validate_general_policy.py')

        # Determine policy path relative to REPO_ROOT
        policy_path = os.path.join(REPO_ROOT, 'config', 'GEMINI.template.md')
        if not os.path.isfile(policy_path):
            policy_path = os.path.join(REPO_ROOT, 'GEMINI.md')

        # 1. Compile all Python files under core/
        compile_errors = compile_python_files(CORE_DIR)
        if compile_errors:
            sys.stderr.write("Syntax errors detected in the following files:\n")
            for file_path, exc in compile_errors:
                sys.stderr.write(f"  {file_path}: {exc}\n")
            sys.exit(1)

        # 2. Run the general policy validator with deterministic policy path
        run_validator(VALIDATOR_PATH, policy_path)

        # If we reach this point, everything passed
        sys.stdout.write("Phase 5 verification succeeded.\n")
        sys.exit(0)

    except Exception as e:
        sys.stderr.write("An unexpected error occurred during verification:\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()

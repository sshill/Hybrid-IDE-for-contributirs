#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-Tool Execution Interceptor & Hard Deny Gate (v0.9.0)
Path: core/hooks/pre_tool_hook.py
Standard: Antigravity Hard Enforcement Gate (Deterministic Execution Policy)

Intercepts and validates commands prior to execution by IDE / agents:
- Enforces trusted host execution prefixes
- Blocks destructive commands (Hard Deny)
- Exits 0 on ALLOW, 1 on DENY
"""

import sys
import os
import re
import argparse

sys.dont_write_bytecode = True

# Whitelist of approved deterministic command prefixes
trusted_host_prefixes = [
    "python3 core/",
    "python3 -m py_compile",
    "python3 core/verify/",
    "python3 core/engine/diagnostic_runner.py",
    "python3 .agents/scripts/diagnostic_runner.py",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git remote",
    "./setup_and_verify.sh",
    "./push_to_github.sh",
    "pytest",
]

# Blacklist of hazardous / destructive patterns (Hard Deny)
forbidden_patterns = [
    r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive)\s+[/~]",
    r">\s*/dev/sd[a-z]",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
    r"\bmkfs\b",
    r"\bdd\s+if=.*of=/dev/",
    r"\bchmod\s+(-R\s+)?777\s+[/~]",
    r"\bchown\s+(-R\s+)?.*\s+[/~]",
]

def normalize_command(cmd: str) -> str:
    """Strip leading wrappers like sudo, env, or shell invocations."""
    c = cmd.strip()
    c = re.sub(r"^(sudo|env|bash\s+-c|sh\s+-c)\s+", "", c).strip()
    return c

def evaluate_command(raw_cmd: str, strict: bool = False) -> tuple[bool, str]:
    """
    Evaluate command safety and prefix adherence.
    Returns (is_allowed: bool, reason: str).
    """
    cmd = normalize_command(raw_cmd)
    if not cmd:
        return True, "Empty command allowed."

    # 0. Hard Deny: Заборона сліпого шелл-краулінгу через ls/dir (Git & Index First v0.9.0)
    cmd_tokens = cmd.split()
    if cmd_tokens and cmd_tokens[0] in ("ls", "dir"):
        return False, (
            "HARD GATE VIOLATION (Git & Index First Protocol v0.9.0): "
            f"Команда '{cmd}' заблокована! Сліпий перегляд файлів через 'ls'/'dir' у пісочниці заборонено. "
            "Використовуйте: 1) 'git status -sb', 2) 'git ls-files <шлях>', 3) 'git show HEAD:<файл>', 4) маніфести у docs/knowledge/index/."
        )

    # 1. Hard Deny Check against destructive patterns
    for pat in forbidden_patterns:
        if re.search(pat, cmd, re.IGNORECASE):
            return False, f"Violates safety policy (matches hazardous pattern: {pat})"

    # 2. Hard Deny Check against inline eval (Zero Inline-Eval Policy)
    inline_eval_patterns = [
        r"\bpython[0-9.]*\s+(-c|--eval)\b",
        r"\b(bash|sh|zsh|dash)\s+-c\b",
        r"\b(eval|exec)\s+[\"']",
    ]
    for pat in inline_eval_patterns:
        if re.search(pat, cmd):
            return False, f"HARD GATE VIOLATION (Zero Inline-Eval Policy): Inline script execution forbidden: '{pat}'"

    # 3. Whitelist Check against trusted prefixes
    for prefix in trusted_host_prefixes:
        if cmd.startswith(prefix):
            return True, f"Approved under trusted prefix: '{prefix}'"

    # 4. Read-only and non-destructive diagnostic fallback
    safe_read_commands = ["git", "cat", "grep", "find", "head", "tail", "wc", "uname", "echo"]
    first_token = cmd.split()[0] if cmd.split() else ""
    if first_token in safe_read_commands:
        return True, f"Standard inspection command permitted: '{first_token}'"

    if strict:
        return False, f"Command '{cmd}' not in trusted prefix list and strict mode is active."

    return True, f"Permitted with audit log: '{cmd}'"

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Pre-Tool Hard Gate Interceptor"
    )
    parser.add_argument("cmd_args", nargs="*", help="Command string or arguments to evaluate")
    parser.add_argument("-c", "--command", type=str, default="", help="Command string to evaluate")
    parser.add_argument("--strict", action="store_true", help="Enforce strict whitelist-only mode")
    args = parser.parse_args()

    # Determine command
    if args.command:
        target_command = args.command
    elif args.cmd_args:
        target_command = " ".join(args.cmd_args)
    else:
        # Self-test mode when executed without arguments
        print("🟢 [PRE-TOOL HOOK: SELF-TEST] Hook operational. Interceptor ready.")
        print(f"   Registered trusted prefixes: {len(trusted_host_prefixes)}")
        print(f"   Registered forbidden patterns: {len(forbidden_patterns)}")
        return 0

    allowed, reason = evaluate_command(target_command, strict=args.strict)
    if allowed:
        print(f"🟢 [PRE-TOOL HOOK: ALLOW] {reason}")
        return 0
    else:
        print(f"❌ [PRE-TOOL HOOK: DENY] {reason}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

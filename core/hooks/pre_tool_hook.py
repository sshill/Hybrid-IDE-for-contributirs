#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-Tool Execution Interceptor & Hard Deny Gate (Policy v0.9.1)
Path: core/hooks/pre_tool_hook.py
Standard: Antigravity Hard Enforcement Gate (Deterministic Execution Policy)

Intercepts and validates commands & tool calls prior to execution:
- Enforces trusted host execution prefixes
- Blocks destructive commands (Hard Deny)
- Selective Code Guard (Zero DIY Coding for *.py, *.sh, *.ts, etc.)
- Provenance ledger verification
- Exits 0 on ALLOW, 1 on DENY (CLI) / returns JSON decision
"""

import sys
import os
import re
import json
import hashlib
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
    clean_cmd = cmd.strip().strip("\"'").strip()
    cmd_tokens = [t.strip("\"'") for t in clean_cmd.split()]
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

    # 3. Provenance check for AI generation attribution in git commit
    if "commit" in cmd and "[generated:" in cmd.lower():
        ledger_paths = [
            "/tmp/antigravity_provenance_ledger.json",
            "/home/hills/Documents/.agents/.provenance_ledger.json"
        ]
        has_ledger_entry = False
        for lp in ledger_paths:
            if os.path.exists(lp):
                try:
                    with open(lp, "r", encoding="utf-8") as f_l:
                        l_data = json.load(f_l)
                        if l_data and len(l_data) > 0:
                            has_ledger_entry = True
                            break
                except Exception:
                    pass
        if not has_ledger_entry:
            return False, "HARD GATE VIOLATION (Anti-Shadow Gate v0.9.1): Заборонено вказувати '[generated: <model>]' у коміті без реального запису у реєстрі провененсу."

    # 4. Whitelist Check against trusted prefixes
    for prefix in trusted_host_prefixes:
        if cmd.startswith(prefix):
            return True, f"Approved under trusted prefix: '{prefix}'"

    # 5. Read-only and non-destructive diagnostic fallback
    safe_read_commands = ["git", "cat", "grep", "find", "head", "tail", "wc", "uname", "echo"]
    first_token = cmd.split()[0] if cmd.split() else ""
    if first_token in safe_read_commands:
        return True, f"Standard inspection command permitted: '{first_token}'"

    if strict:
        return False, f"Command '{cmd}' not in trusted prefix list and strict mode is active."

    return True, f"Permitted with audit log: '{cmd}'"

def evaluate_tool_call_json(data: dict) -> dict:
    """Оцінка безпеки JSON виклику інструменту для IDE / Antigravity (Selective Code Guard v0.9.1)."""
    tool_call = data.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if name in ("write_to_file", "replace_file_content"):
        target_file = args.get("TargetFile", "")
        if target_file:
            normalized = target_file.replace("\\", "/").lower()
            base_name = os.path.basename(normalized)

            controlled_code_exts = (".py", ".sh", ".bash", ".ts", ".js", ".pas", ".cpp", ".h", ".go", ".rs", ".java")
            is_code_file = any(normalized.endswith(ext) for ext in controlled_code_exts)

            # Безумовні артефакти життєвого циклу оркестратора (Policy v0.9.3: Правило 2 файлів)
            is_lifecycle_artifact = (
                base_name in ("walkthrough.md", "implementation_plan.md") or
                "/brain/" in normalized
            )

            # Безпечні системні конфігурації та розмітка
            whitelist_config_exts = (".json", ".yaml", ".yml", ".txt", ".gitignore", ".cfg", ".ini", ".toml", ".log", ".csv", ".tsv", ".sql", ".html", ".css", ".svg", ".png", ".jpg", ".jpeg")
            is_config_file = any(normalized.endswith(ext) for ext in whitelist_config_exts)

            # Репозиторна проєктна документація (*.md поза /brain/):
            # Захист від Context Bloat та DIY-копірайтингу (Repository Docs Hygiene Gate v0.9.3)
            is_repo_doc = not is_code_file and normalized.endswith(".md") and not is_lifecycle_artifact
            if is_repo_doc:
                content_len = len(args.get("CodeContent", "")) or len(args.get("ReplacementContent", ""))
                # Якщо обсяг нового контенту або заміни > 1500 байт — вимагається реєстрація провененсу
                if content_len > 1500:
                    ledger_paths = [
                        "/tmp/antigravity_provenance_ledger.json",
                        "/home/hills/Documents/.agents/.provenance_ledger.json"
                    ]
                    has_doc_entry = False
                    abs_target = os.path.abspath(target_file)
                    for lp in ledger_paths:
                        if os.path.exists(lp):
                            try:
                                with open(lp, "r", encoding="utf-8") as lf:
                                    ledger_data = json.load(lf)
                                    if abs_target in ledger_data:
                                        has_doc_entry = True
                                        break
                            except Exception:
                                pass
                    if not has_doc_entry:
                        return {
                            "decision": "deny",
                            "reason": (
                                "HARD GATE VIOLATION (Repository Docs Hygiene Gate v0.9.3):\n"
                                f"Заборонено прямий DIY-синтез великої проєктної документації ({target_file}, {content_len} байт > 1.5 КБ) оркестратором!\n"
                                "Для захисту контексту від роздуття (Context Bloat) та збереження бюджету дій, великі посібники та шаблони зобов'язані генеруватися моделями ШІ (Tier 1 Ollama або Tier 2 Groq) через:\n"
                                f"python3 .agents/scripts/diagnostic_runner.py --groq-query \"<ТЗ>\" --out {target_file}\n"
                                "або вноситися точковими латками (<1.5 КБ) через replace_file_content."
                            )
                        }

            is_doc = is_lifecycle_artifact or is_config_file or (is_repo_doc and not is_code_file)

            # Автоматичне керування життєвим циклом Фази 4 через ключові артефакти
            if base_name == "implementation_plan.md":
                try:
                    with open("/tmp/antigravity_phase4_active.flag", "w") as pf:
                        pf.write("active")
                    with open("/tmp/antigravity_phase4_steps.txt", "w") as sf:
                        sf.write("0")
                except Exception:
                    pass
            elif base_name == "walkthrough.md":
                try:
                    if os.path.exists("/tmp/antigravity_phase4_active.flag"):
                        os.remove("/tmp/antigravity_phase4_active.flag")
                    if os.path.exists("/tmp/antigravity_phase4_steps.txt"):
                        os.remove("/tmp/antigravity_phase4_steps.txt")
                except Exception:
                    pass

            if not is_doc:
                abs_target = os.path.abspath(target_file)
                code_content = args.get("CodeContent", "")
                repl_content = args.get("ReplacementContent", "")

                content_hashes = []
                if code_content:
                    content_hashes.append(hashlib.sha256(code_content.encode("utf-8")).hexdigest())
                if repl_content:
                    content_hashes.append(hashlib.sha256(repl_content.encode("utf-8")).hexdigest())

                ledger_paths = [
                    "/tmp/antigravity_provenance_ledger.json",
                    "/home/hills/Documents/.agents/.provenance_ledger.json"
                ]
                ledger = {}
                for lp in ledger_paths:
                    if os.path.exists(lp):
                        try:
                            with open(lp, "r", encoding="utf-8") as lf:
                                ledger.update(json.load(lf))
                        except Exception:
                            pass

                authorized = False
                if abs_target in ledger:
                    authorized = True
                else:
                    for entry in ledger.values():
                        e_hash = entry.get("sha256")
                        if e_hash and e_hash in content_hashes:
                            authorized = True
                            break

                if not authorized:
                    for flag_path in ("/tmp/antigravity_provenance_valid.flag", "/tmp/antigravity_ollama_synthesized.flag"):
                        if os.path.exists(flag_path):
                            try:
                                with open(flag_path, "r", encoding="utf-8") as vf:
                                    flag_txt = vf.read()
                                    if abs_target in flag_txt:
                                        authorized = True
                                        break
                            except Exception:
                                pass

                if not authorized:
                    return {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Zero DIY Coding / Selective Code Guard v0.9.1):\n"
                            f"Заборонено прямий запис виконуваного коду через {name}. "
                            "Код має бути синтезований локальною Ollama (python3 .agents/scripts/diagnostic_runner.py --synthesize-script \"<task>\" --out <file>) або узгоджений через Phase 4 Provenance."
                        )
                    }

    return {"decision": "allow"}

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Pre-Tool Hard Gate Interceptor"
    )
    parser.add_argument("cmd_args", nargs="*", help="Command string or arguments to evaluate")
    parser.add_argument("-c", "--command", type=str, default="", help="Command string to evaluate")
    parser.add_argument("--strict", action="store_true", help="Enforce strict whitelist-only mode")
    parser.add_argument("--json", action="store_true", help="Process JSON input from stdin")
    args = parser.parse_args()

    # If stdin is not a tty and no CLI command is provided, parse JSON from stdin
    if args.json or (not sys.stdin.isatty() and not args.command and not args.cmd_args):
        try:
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
                res = evaluate_tool_call_json(data)
                print(json.dumps(res))
                return 0 if res.get("decision") == "allow" else 1
        except Exception as e:
            pass

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

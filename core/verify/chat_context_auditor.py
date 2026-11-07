#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/verify/chat_context_auditor.py — Детерміністичний форензік-аудитор контексту чату (Kernel v0.9.12).
Стандарт: Zero-Dep stdlib only, SLSA / in-toto Provenance Integrity.

Призначення:
Покроковий аналіз транскрипту сесії (transcript.jsonl) на відповідність 8 залізним правилам
регламенту Hybrid-IDE:
  1. Git-First Gate (Фаза 1): Заборона сліпих інструментів (list_dir, find_by_name, grep_search).
  2. Telemetry Gate (Фаза 1 -> 2): Обов'язковий вимір 2D-телеметрії перед створенням плану.
  3. Approval Gate (Фаза 3 -> 4): Заборона мутацій коду до явного схвалення користувачем (+/++).
  4. Zero Inline-Eval Gate (Фаза 4): Заборона прямого інлайн-виконання коду та heredoc.
  5. Shell State Isolation Gate (Фаза 4): Заборона шелл-перенаправлень у системні каталоги ядра.
  6. Secret Isolation Gate (Фаза 4): Заборона читання або маніпуляцій файлами секретів.
  7. Enclave Synthesis & Attribution Gate (Фаза 4.3 / 5): Перевірка відповідності [generated: ...] моделям сесії.
  8. Git State Seal Gate (Фаза 5.2): Обов'язковий локальний git commit після мутації коду.
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.dont_write_bytecode = True

INLINE_EVAL_PATTERNS = [
    r"^\s*python[0-9.]*\s+(-c|--eval)\b",
    r"^\s*(bash|sh|zsh|dash)\s+-c\b",
    r"\b(eval|exec)\s+[\"']",
    r"<<\s*['\"]?EOF",
    r"\|\s*(python[0-9.]*|bash|sh)\b"
]

FORBIDDEN_EXPLORATION_TOOLS = {
    "list_dir",
    "find_by_name",
    "grep_search"
}

CONTROLLED_CODE_EXTENSIONS = (
    ".py", ".sh", ".bash", ".ts", ".js", ".pas",
    ".cpp", ".h", ".go", ".rs", ".java", ".psc"
)


class ChatContextAuditor:
    def __init__(self, strict: bool = False, repo_path: str = None):
        self.strict = strict
        self.repo_path = repo_path or os.getcwd()
        self.telemetry_inspected = False
        self.plan_created = False
        self.plan_approved = False
        self.approved_plan_sha = None
        self.session_models = set()
        self.modified_code_files = []
        self.git_commits_executed = []
        self.violations = []
        self.passed_checks = []

    def _is_code_file(self, path: str) -> bool:
        if not path:
            return False
        clean = path.strip().lower()
        return any(clean.endswith(ext) for ext in CONTROLLED_CODE_EXTENSIONS)

    def _extract_target_file(self, args: dict) -> str:
        if not isinstance(args, dict):
            return ""
        return (
            args.get("TargetFile") or
            args.get("target_file") or
            args.get("path") or
            args.get("TargetDirectory") or
            ""
        )

    def audit_step(self, step: dict):
        step_index = step.get("step_index", -1)
        step_type = step.get("type", "")
        source = step.get("source", "")
        content = step.get("content", "")

        # 1. Фіксація використаних моделей ШІ
        if isinstance(content, str):
            model_match = re.search(r"model[:=]\s*([a-zA-Z0-9_\-.:/]+)", content, re.IGNORECASE)
            if model_match:
                self.session_models.add(model_match.group(1).strip().lower())
            invoc_match = re.search(r"Провайдер\s*/\s*Модель[:\*]*\s*[^/]+/([a-zA-Z0-9_\-.:/]+)", content, re.IGNORECASE)
            if invoc_match:
                self.session_models.add(invoc_match.group(1).strip().lower())

        # 2. Фіксація схвалення користувача (Фаза 3)
        if source == "USER_EXPLICIT" or step_type == "USER_INPUT":
            if isinstance(content, str):
                user_msg = content.strip().lower()
                if any(sig in user_msg for sig in ["+!", "+", "approved", "схвалюю", "схвалено", "proceed"]):
                    self.plan_approved = True

        # 3. Аналіз викликів інструментів
        tool_calls = step.get("tool_calls", [])
        if not tool_calls and isinstance(content, dict):
            tool_calls = content.get("tool_calls", [])

        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name", "")
            args = call.get("args", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            # Перевірка 1: Git-First Policy
            if name in FORBIDDEN_EXPLORATION_TOOLS:
                self.violations.append({
                    "gate": "GIT_FIRST_GATE",
                    "step": step_index,
                    "severity": "CRITICAL",
                    "tool": name,
                    "reason": f"Виклик забороненого інструменту сліпого пошуку '{name}'. Регламент v0.9.12 вимагає Git-First (git ls-files / git status)."
                })

            # Перевірка 2: Модифікація файлів
            if name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
                target = self._extract_target_file(args)
                base = os.path.basename(target)

                if base == "implementation_plan.md":
                    self.plan_created = True
                    if not self.telemetry_inspected:
                        self.violations.append({
                            "gate": "TELEMETRY_GATE",
                            "step": step_index,
                            "severity": "HIGH",
                            "file": target,
                            "reason": "Формування implementation_plan.md (Фаза 2) відбулося без попереднього виміру 2D-телеметрії сесії."
                        })
                elif self._is_code_file(target):
                    self.modified_code_files.append((step_index, target))
                    if not self.plan_approved:
                        self.violations.append({
                            "gate": "APPROVAL_GATE",
                            "step": step_index,
                            "severity": "CRITICAL",
                            "file": target,
                            "reason": f"Модифікація коду на диску ('{base}') виконана на кроці {step_index} БЕЗ явного схвалення плану користувачем (+/++)."
                        })

            # Перевірка 3: Виконання шелл-команд
            if name == "run_command":
                cmd = args.get("CommandLine", "") or args.get("command", "")
                if not cmd:
                    continue

                if "phase1_inspect.py --telemetry" in cmd or "enclave_daemon.py --telemetry" in cmd:
                    self.telemetry_inspected = True

                # Очищаємо текст команди від аргументів --task або --query, де описуються правила
                exec_cmd_part = cmd
                for flag in ("--task", "--query", "--attest-arbiter"):
                    if flag in exec_cmd_part:
                        exec_cmd_part = exec_cmd_part.split(flag)[0]

                # Zero Inline-Eval Gate
                for pat in INLINE_EVAL_PATTERNS:
                    if re.search(pat, exec_cmd_part):
                        self.violations.append({
                            "gate": "ZERO_INLINE_EVAL_GATE",
                            "step": step_index,
                            "severity": "CRITICAL",
                            "command": cmd,
                            "reason": f"Виявлено пряме інлайн-виконання коду або Here-doc ({pat}) у шеллі: '{cmd}'."
                        })
                        break

                # Shell State Isolation Gate
                redirect_matches = re.findall(r"(?:>|>>|\|\s*tee\s+-?a?)\s*([^\s;&|]+)", cmd)
                for rm in redirect_matches:
                    clean_rm = rm.strip("\"'")
                    if any(prot in clean_rm for prot in [".system_generated", "core/", "provenance_ledger", ".secret", "approved_plan.sha256"]):
                        self.violations.append({
                            "gate": "SHELL_STATE_ISOLATION_GATE",
                            "step": step_index,
                            "severity": "CRITICAL",
                            "command": cmd,
                            "reason": f"Спроба перенаправлення виводу шеллу у захищений системний файл ('{clean_rm}')."
                        })

                # Secret Isolation Gate
                norm_exec = exec_cmd_part.replace("\\", "/").lower()
                if ".core_master_hmac.secret" in norm_exec or ((".secret" in norm_exec) and any(v in norm_exec for v in ("cat ", "grep ", "head ", "tail ", "view "))):
                    self.violations.append({
                        "gate": "SECRET_ISOLATION_GATE",
                        "step": step_index,
                        "severity": "CRITICAL",
                        "command": cmd,
                        "reason": f"Спроба доступу до майстер-секрету або чутливих ключів через шелл: '{cmd}'."
                    })

                # Фіксація Git commit операцій
                if "git " in cmd and "commit" in cmd:
                    self.git_commits_executed.append((step_index, cmd))
                    # Git Attribution & Fake Model Check
                    if "generated:" in cmd.lower():
                        m = re.search(r"generated:\s*([a-zA-Z0-9_\-.:/]+)", cmd, re.IGNORECASE)
                        if m:
                            claimed_model = m.group(1).strip().lower()
                            if self.session_models and not any(claimed_model in sm or sm in claimed_model for sm in self.session_models):
                                self.violations.append({
                                    "gate": "GIT_ATTRIBUTION_GATE",
                                    "step": step_index,
                                    "severity": "HIGH",
                                    "command": cmd,
                                    "reason": f"Коміт заявляє модель '[generated: {claimed_model}]', але її виклику не зафіксовано у сесії."
                                })

    def audit_transcript(self, records: list[dict], check_live_git: bool = False) -> dict:
        self.telemetry_inspected = False
        self.plan_created = False
        self.plan_approved = False
        self.modified_code_files.clear()
        self.git_commits_executed.clear()
        self.violations.clear()
        self.passed_checks.clear()

        for rec in records:
            self.audit_step(rec)

        # 8. Git State Seal Gate (Фаза 5.2):
        # Якщо у сесії відбулася модифікація коду, обов'язково має бути викликаний git commit!
        if self.modified_code_files:
            if not self.git_commits_executed:
                last_mod_step = self.modified_code_files[-1][0]
                self.violations.append({
                    "gate": "GIT_STATE_SEAL_GATE",
                    "step": last_mod_step,
                    "severity": "CRITICAL",
                    "reason": (
                        f"Виявлено {len(self.modified_code_files)} модифікацій коду у Фазі 4, "
                        "але сесія завершилася БЕЗ автономного виклику 'git commit' у Фазі 5. "
                        "Регламент v0.9.12 вимагає обов'язкового запечатування змін у Git перед публікацією Walkthrough."
                    )
                })

        # Перевірка живого стану Git у поточному репозиторії
        if check_live_git and os.path.isdir(os.path.join(self.repo_path, ".git")):
            try:
                res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0 and res.stdout.strip():
                    dirty_code = [
                        line.strip() for line in res.stdout.splitlines()
                        if any(line.strip().endswith(ext) for ext in CONTROLLED_CODE_EXTENSIONS)
                    ]
                    if dirty_code and not self.git_commits_executed:
                        self.violations.append({
                            "gate": "GIT_STATE_SEAL_GATE",
                            "step": -1,
                            "severity": "HIGH",
                            "reason": f"Репозиторій має незакомічені зміни файлів коду ({len(dirty_code)} шт): {', '.join(dirty_code[:3])}."
                        })
            except Exception:
                pass

        if not any(v.get("gate") == "GIT_FIRST_GATE" for v in self.violations):
            self.passed_checks.append("Git-First Discovery Gate (жодного сліпого ls/find)")
        if not any(v.get("gate") == "TELEMETRY_GATE" for v in self.violations):
            self.passed_checks.append("2D-Telemetry Initialization Gate")
        if not any(v.get("gate") == "APPROVAL_GATE" for v in self.violations):
            self.passed_checks.append("Phase 3 Approval Gate (мутації лише після схвалення)")
        if not any(v.get("gate") == "ZERO_INLINE_EVAL_GATE" for v in self.violations):
            self.passed_checks.append("Zero Inline-Eval Gate (жодного inline python/bash/heredoc)")
        if not any(v.get("gate") == "SHELL_STATE_ISOLATION_GATE" for v in self.violations):
            self.passed_checks.append("Shell State Isolation Gate (захист .system_generated та core)")
        if not any(v.get("gate") == "SECRET_ISOLATION_GATE" for v in self.violations):
            self.passed_checks.append("Secret Isolation Gate (HMAC майстер-секрети захищено)")
        if not any(v.get("gate") == "GIT_ATTRIBUTION_GATE" for v in self.violations):
            self.passed_checks.append("Git Provenance Attribution Gate (відсутність фіктивних моделей)")
        if not any(v.get("gate") == "GIT_STATE_SEAL_GATE" for v in self.violations):
            self.passed_checks.append("Git State Seal Gate (всі модифікації запечатано комітом)")

        passed = len(self.violations) == 0
        return {
            "status": "PASS" if passed else "FAIL",
            "total_steps": len(records),
            "telemetry_inspected": self.telemetry_inspected,
            "plan_approved": self.plan_approved,
            "modified_code_files_count": len(self.modified_code_files),
            "git_commits_count": len(self.git_commits_executed),
            "violations_count": len(self.violations),
            "violations": self.violations,
            "passed_checks": self.passed_checks
        }


def resolve_transcript_path(conversation_id: str = None, transcript_path: str = None) -> str:
    if transcript_path and os.path.isfile(transcript_path):
        return os.path.abspath(transcript_path)

    brain_base = Path(os.path.expanduser("~/.gemini/antigravity/brain"))
    if conversation_id:
        cand = brain_base / conversation_id / ".system_generated" / "logs" / "transcript.jsonl"
        if cand.is_file():
            return str(cand)
        cand_alt = brain_base / conversation_id / "transcript.jsonl"
        if cand_alt.is_file():
            return str(cand_alt)
        return ""

    if brain_base.is_dir():
        candidates = []
        for sdir in brain_base.iterdir():
            if sdir.is_dir():
                tfile = sdir / ".system_generated" / "logs" / "transcript.jsonl"
                if tfile.is_file():
                    candidates.append((tfile.stat().st_mtime, str(tfile)))
                else:
                    tfile_alt = sdir / "transcript.jsonl"
                    if tfile_alt.is_file():
                        candidates.append((tfile_alt.stat().st_mtime, str(tfile_alt)))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

    return ""


def scan_all_sessions(recent_n: int = None) -> list[dict]:
    brain_base = Path(os.path.expanduser("~/.gemini/antigravity/brain"))
    results = []
    if not brain_base.is_dir():
        return results

    sessions = []
    for sdir in brain_base.iterdir():
        if sdir.is_dir():
            tfile = sdir / ".system_generated" / "logs" / "transcript.jsonl"
            if not tfile.is_file():
                tfile = sdir / "transcript.jsonl"
            if tfile.is_file():
                sessions.append((tfile.stat().st_mtime, sdir.name, str(tfile)))

    sessions.sort(key=lambda x: x[0], reverse=True)
    if recent_n and recent_n > 0:
        sessions = sessions[:recent_n]

    for mtime, conv_id, t_path in sessions:
        records = parse_transcript_file(t_path)
        auditor = ChatContextAuditor(strict=False)
        rep = auditor.audit_transcript(records, check_live_git=False)
        rep["conversation_id"] = conv_id
        rep["transcript_path"] = t_path
        results.append(rep)

    return results



def parse_transcript_file(path: str) -> list[dict]:
    records = []
    if not path or not os.path.isfile(path):
        return records
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                records.append(json.loads(line_str))
            except Exception:
                pass
    return records


def build_git_sha_manifest(repo_path: str = None) -> dict:
    repo = repo_path or os.getcwd()
    manifest = {}
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    fpath = os.path.join(repo, parts[1])
                    if os.path.isfile(fpath):
                        h = hashlib.sha256()
                        with open(fpath, "rb") as bf:
                            while chunk := bf.read(65536):
                                h.update(chunk)
                        manifest[parts[1]] = h.hexdigest()
    except Exception:
        pass
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Deterministic Chat Context & Regulation Auditor (Kernel v0.9.12)")
    parser.add_argument("--conversation-id", type=str, help="ID сесії (brain-каталог)")
    parser.add_argument("--transcript", type=str, help="Шлях до файлу transcript.jsonl")
    parser.add_argument("--current-session", action="store_true", help="Авто-резолв поточної активної сесії")
    parser.add_argument("--scan-all", action="store_true", help="Пакетний аудит усіх збережених сесій / тредів")
    parser.add_argument("--recent-sessions", type=int, default=None, help="Пакетний аудит N останніх сесій")
    parser.add_argument("--strict", action="store_true", help="Повернути ненульовий код при порушеннях")
    parser.add_argument("--json", action="store_true", help="Вивести результат у форматі JSON")
    parser.add_argument("--git-sha-manifest", action="store_true", help="Сформувати Git SHA-256 маніфест змінених файлів")

    args = parser.parse_args()

    if args.git_sha_manifest:
        manifest = build_git_sha_manifest()
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print("📦 [GIT SHA-256 MANIFEST]:")
            for k, v in manifest.items():
                print(f"  • {k}: {v}")
        return 0

    if args.scan_all or args.recent_sessions is not None:
        results = scan_all_sessions(recent_n=args.recent_sessions)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print("🛡️ [MULTI-THREAD CHAT CONTEXT AUDIT BATCH REPORT v0.9.12]")
            print(f"📊 Всього проаналізовано сесій: {len(results)}")
            print("=" * 70)
            passed = sum(1 for r in results if r.get("status") == "PASS")
            failed = len(results) - passed
            for r in results:
                status_icon = "🟢 PASS" if r.get("status") == "PASS" else "🔴 FAIL"
                cid = r.get("conversation_id", "")[:18]
                steps = r.get("total_steps", 0)
                viols = r.get("violations_count", 0)
                print(f"  • {status_icon} | ID: {cid}... | Кроки: {steps:4d} | Порушень: {viols:2d}")
            print("-" * 70)
            print(f"Підсумок: 🟢 PASS: {passed} | 🔴 FAIL: {failed}")
        return 0 if not (args.strict and failed > 0) else 1


    t_path = resolve_transcript_path(conversation_id=args.conversation_id, transcript_path=args.transcript)
    if not t_path:
        is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
        if is_ci:
            if args.json:
                print(json.dumps({"status": "PASS", "info": "CI/Headless environment - transcript audit skipped"}, indent=2))
            else:
                print("ℹ️ [CHAT CONTEXT AUDITOR]: CI/Headless environment detected (no active transcript). Skipping live transcript check.")
            return 0
        err = {"status": "ERROR", "error": "Transcript file not found"}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print("❌ [AUDIT ERROR]: Не вдалося знайти файл transcript.jsonl для аналізу.", file=sys.stderr)
        return 1 if args.strict else 0

    records = parse_transcript_file(t_path)
    auditor = ChatContextAuditor(strict=args.strict)
    report = auditor.audit_transcript(records, check_live_git=args.current_session)
    report["transcript_path"] = t_path

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status_icon = "🟢 PASS" if report["status"] == "PASS" else "🔴 FAIL"
        print("=" * 68)
        print(f"🛡️ [CHAT CONTEXT AUDIT REPORT v0.9.12]: {status_icon}")
        print(f"📄 Файл транскрипту: {t_path}")
        print(f"📊 Всього проаналізовано кроків: {report['total_steps']}")
        print(f"🚨 Зафіксовано порушень: {report['violations_count']}")
        print(f"📦 Модифіковано файлів коду: {report['modified_code_files_count']}")
        print(f"🔏 Виконано Git комітів: {report['git_commits_count']}")
        print("=" * 68)

        if report["passed_checks"]:
            print("\n✅ Успішно пройдені гейти:")
            for chk in report["passed_checks"]:
                print(f"  • {chk}")

        if report["violations"]:
            print("\n❌ ВИЯВЛЕНІ ПОРУШЕННЯ РЕГЛАМЕНТУ:")
            for v in report["violations"]:
                print(f"  🔴 [{v.get('gate')}] Step {v.get('step')} ({v.get('severity')}): {v.get('reason')}")
            print("\n⚠️ Відповідно до Kernel v0.9.12, коміт або реліз у Фазі 5 ЗАБЛОКОВАНО.")

    if args.strict and report["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

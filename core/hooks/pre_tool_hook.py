#!/usr/bin/env python3
import sys
import time
import json
import subprocess
import os
import re
import hashlib
from datetime import datetime

sys.dont_write_bytecode = True

LOG_FILE = "/tmp/antigravity_hooks.log"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SOUND_PATH = os.path.join(SCRIPT_DIR, "..", "sounds", "access_request.wav")
if not os.path.exists(SOUND_PATH):
    SOUND_PATH = os.path.expanduser("~/.gemini/config/sounds/access_request.wav")

import fcntl

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(f"{datetime.now().isoformat()} [PreToolUse] {msg}\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass

def play_sound():
    if os.path.exists(SOUND_PATH):
        try:
            subprocess.Popen(["/usr/bin/paplay", SOUND_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                subprocess.Popen(["/usr/bin/aplay", "-q", SOUND_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

def _import_provenance_hooks():
    prov_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "provenance"),
        os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/bin"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bin")),
    ]
    for pd in prov_dirs:
        if os.path.isdir(pd) and pd not in sys.path:
            sys.path.insert(0, pd)
    try:
        from core.provenance.phase4_provenance import reserve_passport, simulate_replacement, plan_authorizes
        return reserve_passport, simulate_replacement, plan_authorizes
    except ModuleNotFoundError:
        try:
            from phase4_provenance import reserve_passport, simulate_replacement, plan_authorizes
            return reserve_passport, simulate_replacement, plan_authorizes
        except ModuleNotFoundError:
            return None, None, None

def verify_contributor_plan_sanction(brain_state_dir: str, abs_target: str, base_name: str) -> bool:
    """
    Перевірка санкції Contributor Mode для ядра (Kernel v0.9.12).
    Використовує єдиний канонічний авторизатор plan_authorizes() із phase4_provenance.
    """
    if brain_state_dir and os.path.isdir(brain_state_dir):
        os.environ["HYBRID_IDE_BRAIN_DIR"] = os.path.dirname(brain_state_dir)
    prov_hooks = _import_provenance_hooks()
    plan_auth_fn = prov_hooks[2] if len(prov_hooks) > 2 else None
    if plan_auth_fn:
        ok, msg = plan_auth_fn(abs_target)
        if ok:
            log(f"plan_authorizes PASS: {msg}")
            return True
        log(f"plan_authorizes REJECT: {msg}")
        return False

    if not brain_state_dir:
        return False

    approved_sha_path = os.path.join(brain_state_dir, "approved_plan.sha256")
    if not os.path.isfile(approved_sha_path):
        return False

    plan_path = os.path.join(os.path.dirname(brain_state_dir), "implementation_plan.md")
    if not os.path.isfile(plan_path):
        return False

    try:
        with open(plan_path, "rb") as pf:
            current_plan_sha = hashlib.sha256(pf.read()).hexdigest()
        with open(approved_sha_path, "r", encoding="utf-8") as af:
            approved_plan_sha = af.read().strip()

        if current_plan_sha != approved_plan_sha:
            return False

        with open(plan_path, "r", encoding="utf-8") as pf:
            plan_text = pf.read()
            patterns = [
                rf"\[(?:MODIFY|NEW|DELETE)\]\s+.*?(?:`|/){re.escape(base_name)}`?",
                rf"`{re.escape(abs_target)}`",
                rf"\(file://[^\)]*{re.escape(base_name)}\)",
                rf"\b{re.escape(base_name)}\b"
            ]
            for pat in patterns:
                if re.search(pat, plan_text):
                    return True
    except Exception:
        pass

    return False

def main():
    try:
        raw = sys.stdin.read()
        log(f"raw input: {raw}")
        data = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        log(f"json decode error: {e}")
        data = {}

    tool_call = data.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args") or tool_call.get("arguments") or {}
    workspace_paths = data.get("workspacePaths", [])

    # ІЗОЛЯЦІЯ СТАНУ ЗА СЕСІЄЮ ТА ВОРКСПЕЙСОМ (Kernel v0.9.9 Brain-First State):
    conv_id = data.get("conversationId") or data.get("conversation_id") or ""
    artifact_dir = data.get("artifactDirectoryPath") or ""

    if conv_id:
        sess_id = hashlib.sha256(conv_id.encode("utf-8")).hexdigest()[:8]
    elif workspace_paths and workspace_paths[0]:
        sess_id = hashlib.sha256(workspace_paths[0].encode("utf-8")).hexdigest()[:8]
    elif "Cwd" in args:
        sess_id = hashlib.sha256(args["Cwd"].encode("utf-8")).hexdigest()[:8]
    else:
        sess_id = hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest()[:8]

    brain_state_dir = None
    brain_root = os.path.realpath(os.path.expanduser("~/.gemini/antigravity/brain"))
    if artifact_dir:
        real_art = os.path.realpath(artifact_dir)
        if real_art == brain_root or real_art.startswith(brain_root + os.sep):
            brain_state_dir = os.path.join(real_art, ".system_generated")
    elif conv_id:
        clean_conv = os.path.basename(str(conv_id).strip("/\\"))
        if clean_conv and clean_conv not in (".", ".."):
            clean_conv = "".join(c for c in clean_conv if c.isalnum() or c in ("-", "_", "."))
            if clean_conv:
                cand_dir = os.path.join(brain_root, clean_conv, ".system_generated")
                brain_state_dir = cand_dir
    else:
        if os.path.exists(brain_root):
            try:
                cands = [os.path.join(brain_root, d) for d in os.listdir(brain_root) if os.path.isdir(os.path.join(brain_root, d))]
                if cands:
                    cands.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    brain_state_dir = os.path.join(cands[0], ".system_generated")
            except Exception:
                pass

    if brain_state_dir:
        try:
            os.makedirs(brain_state_dir, exist_ok=True)
        except Exception:
            pass

    # Brain-First ізольовані шляхи стану
    brain_phase4_flag = os.path.join(brain_state_dir, "phase4_active.flag") if brain_state_dir else None
    brain_contract_file = os.path.join(brain_state_dir, "phase4_contract.json") if brain_state_dir else None
    brain_history_file = os.path.join(brain_state_dir, "action_history.json") if brain_state_dir else None
    brain_step_file = os.path.join(brain_state_dir, "phase4_steps.txt") if brain_state_dir else None
    brain_telemetry_flag = os.path.join(brain_state_dir, "telemetry.flag") if brain_state_dir else None
    brain_claude_flag = os.path.join(brain_state_dir, "claude_verified.flag") if brain_state_dir else None
    brain_copilot_flag = os.path.join(brain_state_dir, "copilot_executed.flag") if brain_state_dir else None
    brain_copilot_auth_flag = os.path.join(brain_state_dir, "copilot_authorized.flag") if brain_state_dir else None
    brain_ledger = os.path.join(brain_state_dir, "provenance_ledger.json") if brain_state_dir else None

    # Fallback /tmp шляхи з ізоляцією за сесією (Kernel v0.9.12)
    phase4_flag = f"/tmp/antigravity_phase4_{sess_id}.flag"
    legacy_phase4_flag = None
    contract_file = f"/tmp/antigravity_phase4_contract_{sess_id}.json"
    legacy_contract_file = None
    history_file = f"/tmp/antigravity_action_history_{sess_id}.json"
    step_file = f"/tmp/antigravity_phase4_steps_{sess_id}.txt"
    legacy_step_file = None
    telemetry_flag = f"/tmp/antigravity_telemetry_{sess_id}.flag"
    legacy_telemetry_flag = None

    all_telemetry_flags = [f for f in (brain_telemetry_flag, telemetry_flag) if f]
    all_phase4_flags = [f for f in (brain_phase4_flag, phase4_flag) if f]
    all_contract_files = [f for f in (brain_contract_file, contract_file) if f]
    all_history_files = [f for f in (brain_history_file, history_file) if f]
    all_step_files = [f for f in (brain_step_file, step_file) if f]
    all_claude_flags = [f for f in (brain_claude_flag, "/tmp/antigravity_claude_verified.flag") if f]
    all_copilot_flags = [f for f in (brain_copilot_flag, brain_copilot_auth_flag, f"/tmp/antigravity_copilot_executed_{sess_id}.flag") if f]
    brain_cb_file = os.path.join(brain_state_dir, "circuit_breaker_fails.txt") if brain_state_dir else None
    sess_cb_file = f"/tmp/antigravity_circuit_breaker_fails_{sess_id}.txt"
    all_cb_files = [f for f in (brain_cb_file, sess_cb_file) if f]

    # ============================================================
    # 0. HARD DENY GATE: Залізний бар'єр заборонених деструктивних команд
    # ============================================================
    if name == "run_command":
        cmd_line = args.get("CommandLine", "")

        # Авто-актуалізація прапорця телеметрії при запуску phase1_inspect.py --telemetry
        if "phase1_inspect.py" in cmd_line and "--telemetry" in cmd_line:
            try:
                for tf_path in all_telemetry_flags:
                    with open(tf_path, "w", encoding="utf-8") as tf:
                        json.dump({"sess_id": sess_id, "timestamp": time.time(), "status": "inspected"}, tf)
            except Exception:
                pass
        # HARD DENY GATE: Заборона сліпого шелл-краулінгу через ls/dir (Git & Index First v0.9.0)
        clean_cmd = cmd_line.strip().strip("\"'").strip()
        cmd_tokens = [t.strip("\"'") for t in clean_cmd.split()]
        if cmd_tokens and cmd_tokens[0] in ("ls", "dir"):
            log(f"HARD DENY: Attempted raw ls crawl: {cmd_line}")
            res = {
                "decision": "deny",
                "reason": (
                    "HARD GATE VIOLATION (Git & Index First Protocol v0.9.0):\n"
                    f"Команда '{cmd_line}' заблокована! Сліпий перегляд файлів через 'ls'/'dir' у пісочниці заборонено.\n"
                    "Дослідження структури та файлів виконується ВИКЛЮЧНО через:\n"
                    "1) 'git status -sb' або 'git ls-files <шлях>'\n"
                    "2) 'git log -n 5 --name-only'\n"
                    "3) 'git show HEAD:<файл>'\n"
                    "4) Маніфести у docs/knowledge/index/ або diagnostic_runner.py\n"
                )
            }
            print(json.dumps(res))
            return

        forbidden_git_destructive = [
            "git reset", "git revert", "git restore",
            "git push", "git merge", "git rebase"
        ]
        for pat in forbidden_git_destructive:
            if pat in cmd_line:
                log(f"HARD DENY: cmd='{cmd_line}' matched '{pat}'")
                res = {
                    "decision": "deny",
                    "reason": f"HARD GATE VIOLATION (GEMINI.md Approval Gate): Команда '{pat}' заборонена до автоматичного виконання без окремого схвалення користувача."
                }
                print(json.dumps(res))
                return

        # Захист від блокування Git через масовий force-add каталогів з гігабайтами ресурсів
        if "add" in cmd_line and "-f" in cmd_line:
            for bad_target in ["game/Data", "game/", "dist/"]:
                # Якщо передано каталог з даними, а не окремий файл
                tokens = cmd_line.split()
                for token in tokens:
                    token_clean = token.strip("\"'/,")
                    if token_clean in [bad_target.strip("/"), "game/Data", "dist", "game"]:
                        log(f"HARD DENY: dangerous bulk git add -f on directory '{token}'")
                        res = {
                            "decision": "deny",
                            "reason": f"HARD GATE VIOLATION: Заборонено масовий 'git add -f {token}' для каталогів з ресурсами. Стейджити дозволено виключно конкретні файли (наприклад: 'git add -f game/Data/MercyRecruitment.esp')."
                        }
                        print(json.dumps(res))
                        return

        # Захист від фальсифікації верифікації моделями ШІ (GEMINI.md Розділ 2.3)
        if "commit" in cmd_line and "verified: claude" in cmd_line.lower():
            if not any(os.path.exists(cf) for cf in all_claude_flags):
                log(f"HARD DENY: unverified claude attribution in commit")
                res = {
                    "decision": "deny",
                    "reason": "HARD GATE VIOLATION (GEMINI.md Section 2.3): Заборонено вказувати '[verified: claude...]' у повідомленні коміту без реального інференсу/виклику субагента Claude Sonnet."
                }
                print(json.dumps(res))
                return

        # Захист від фальсифікації аудиту Copilot CLI (Policy v0.9.7)
        if "commit" in cmd_line and "audited: copilot-cli" in cmd_line.lower():
            if not any(os.path.exists(cf) for cf in all_copilot_flags):
                log(f"HARD DENY: unverified copilot-cli attribution in commit")
                res = {
                    "decision": "deny",
                    "reason": "HARD GATE VIOLATION (Policy v0.9.7): Заборонено вказувати '[audited: copilot-cli]' у повідомленні коміту без підтвердженого виконання сесії Copilot CLI."
                }
                print(json.dumps(res))
                return

        # Блокування фіктивних комітів ШІ-синтезу (Policy v0.9.1 / Anti-Shadow Gate)
        if "commit" in cmd_line and "generated:" in cmd_line.lower():
            prov_tool = os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/bin/phase4_provenance.py")
            if not os.path.exists(prov_tool):
                prov_tool = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "provenance", "phase4_provenance.py"))
            if not os.path.exists(prov_tool):
                prov_tool = os.path.abspath(os.path.join(SCRIPT_DIR, "phase4_provenance.py"))
            if os.path.exists(prov_tool):
                chk = subprocess.run([sys.executable, prov_tool, "--verify-commit", cmd_line], capture_output=True, text=True)
                if chk.returncode != 0:
                    err_msg = chk.stdout.strip() or chk.stderr.strip()
                    log(f"HARD DENY: unverified AI generation attribution: {err_msg}")
                    res = {
                        "decision": "deny",
                        "reason": f"HARD GATE VIOLATION (Provenance Ledger v0.9.1):\n{err_msg}\nЗаборонено заявляти '[generated: <model>]' у коміті без підтвердженої генерації файлів у сесійному реєстрі."
                    }
                    print(json.dumps(res))
                    return

        # ============================================================
        # COPILOT HEAVY-ONLY ESCALATION GATE (Policy v0.9.7):
        # Дозволено виключно при: (1) прапорці /tmp/antigravity_copilot_authorized.flag або brain (+ у чаті),
        # (2) /tmp/antigravity_audit_failed.flag, (3) цільовому рефакторингу кодової бази (--heavy-refactor).
        # ============================================================
        if "copilot" in cmd_line:
            is_copilot_cli = any(tok in ("copilot", os.path.expanduser("~/.local/bin/copilot")) for tok in cmd_line.split())
            if is_copilot_cli and not ("copilot help" in cmd_line or "copilot --version" in cmd_line or "copilot /login" in cmd_line):
                authorized = any(os.path.exists(f) for f in (brain_copilot_auth_flag, "/tmp/antigravity_copilot_authorized.flag") if f)
                audit_failed = any(os.path.exists(f) for f in (os.path.join(brain_state_dir, "audit_failed.flag") if brain_state_dir else None, "/tmp/antigravity_audit_failed.flag") if f)
                heavy_refactor = "--heavy-refactor" in cmd_line or "рефакторинг" in cmd_line.lower() or "wholesale" in cmd_line.lower()
                if not (authorized or audit_failed or heavy_refactor):
                    log(f"HARD DENY: Copilot invoked without authorization: {cmd_line}")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Copilot Heavy-Only Escalation Gate v0.9.7):\n"
                            "Виклик GitHub Copilot CLI заблоковано! Copilot дозволено виключно за:\n"
                            "1) Санкцією користувача (+ у чаті / /tmp/antigravity_copilot_authorized.flag)\n"
                            "2) Негативним вердиктом аудиту Sonnet (/tmp/antigravity_audit_failed.flag)\n"
                            "3) Монолітним рефакторингом ('--heavy-refactor')."
                        )
                    }
                    print(json.dumps(res))
                    return

        # ============================================================
        # RUNTIME CIRCUIT BREAKER GATE (Kernel v0.9.12 Session-Isolated): Зупинка після 2 збоїв
        # ============================================================
        fails = 0
        cb_candidates = all_cb_files + ["/tmp/antigravity_circuit_breaker_fails.txt"]
        for cbp in cb_candidates:
            if os.path.exists(cbp):
                try:
                    with open(cbp, "r") as f:
                        f_val = int(f.read().strip())
                        if f_val > fails:
                            fails = f_val
                except Exception:
                    pass

        if fails >= 2 and not ("git status" in cmd_line or "validate_general_policy" in cmd_line or "phase5_verify" in cmd_line or "--reset-breaker" in cmd_line):
            log(f"HARD DENY: Circuit Breaker triggered ({fails} consecutive failures for session {sess_id})")
            res = {
                "decision": "deny",
                "reason": (
                    "HARD GATE VIOLATION (Runtime Circuit Breaker Tripped v0.9.12):\n"
                    f"Зафіксовано {fails} послідовних збоїв виконання скрипта/команди у поточній сесії.\n"
                    "Автоматичний ReAct цикл зупинено для захисту токенів та запобігання зацикленню.\n"
                    "Опублікуйте проміжний звіт у чат та узгодьте план дій із користувачем."
                )
            }
            print(json.dumps(res))
            return


        # ============================================================
        # ZERO INLINE-EVAL GATE (v0.8.2): Повна заборона інлайн-коду та Here-docs
        # ============================================================
        inline_eval_patterns = [
            r"\bpython[0-9.]*\s+(-c|--eval)\b",
            r"\bdiagnostic_runner\.py\s+.*--eval\b",
            r"\b(bash|sh|zsh|dash)\s+-c\b",
            r"\b(eval|exec)\s+[\"']",
            r"<<\s*['\"]?EOF",
            r"\|\s*(python[0-9.]*|bash|sh)\b"
        ]
        for pat in inline_eval_patterns:
            if re.search(pat, cmd_line):
                log(f"HARD DENY: inline-eval detected in '{cmd_line}' matching '{pat}'")
                res = {
                    "decision": "deny",
                    "reason": (
                        "HARD GATE VIOLATION (Zero Inline-Eval Policy v0.8.2):\n"
                        "Антігравіті категорично заборонено самостійно писати або виконувати інлайн-скрипти чи Here-docs ('python3 -c', '--eval', 'bash -c', '<<EOF').\n"
                        "Усі операції з кодом обов'язково делегуються моделям ШІ:\n"
                        "1) Для синтезу діагностичного скрипта виконайте:\n"
                        "   python3 .agents/scripts/diagnostic_runner.py --synthesize-script \"<завдання>\" --out scratch/script.py\n"
                        "2) Для прямого запиту до Ollama:\n"
                        "   python3 .agents/scripts/diagnostic_runner.py --ollama-query \"<запит>\" --model qwen2.5-coder:1.5b\n"
                        "3) Для запуску готового файлу:\n"
                        "   python3 .agents/scripts/diagnostic_runner.py --run <шлях_до_файлу>\n"
                        "Не пишіть код самостійно!"
                    )
                }
                print(json.dumps(res))
                return

        # ============================================================
        # SHELL STATE ISOLATION & SECRET ISOLATION GATE (Kernel v0.9.12):
        # Повна заборона маніпуляцій та перегляду системних файлів і секретів через шелл (deny-by-reference)
        # ============================================================
        norm_cmd = cmd_line.replace("\\", "/").lower()
        protected_shell_targets = (
            "provenance_ledger",
            ".core_master_hmac.secret",
            ".system_generated/flags",
            "approved_plan.sha256"
        )
        has_protected_ref = any(target in norm_cmd for target in protected_shell_targets) or (".secret" in norm_cmd)
        if has_protected_ref:
            if ".core_master_hmac.secret" in norm_cmd or ".secret" in norm_cmd:
                log(f"HARD DENY: Secret Isolation Gate blocked shell reference to secret: {cmd_line}")
                res = {
                    "decision": "deny",
                    "reason": (
                        "HARD GATE VIOLATION (Secret Isolation Gate v0.9.12):\n"
                        f"Команда '{cmd_line}' заблокована! Доступ до криптографічних секретів ядра через шелл категорично заборонено."
                    )
                }
                print(json.dumps(res))
                return

            shell_verbs = (
                "cat", "cp", "mv", "rm", "sed", "dd", "truncate", "tar", "awk", "perl",
                "rsync", "touch", "ln", "base64", "install", "chmod", "tee", ">", ">>", "python"
            )
            is_shell_manipulation = any(verb in norm_cmd for verb in shell_verbs)
            if is_shell_manipulation and not ("test_provenance_security.py" in norm_cmd or "phase5_verify.py" in norm_cmd):
                log(f"HARD DENY: Shell State Isolation Gate blocked manipulation of state file: {cmd_line}")
                res = {
                    "decision": "deny",
                    "reason": (
                        "HARD GATE VIOLATION (Shell State Isolation Gate v0.9.12):\n"
                        f"Шелл-маніпуляція захищеними файлами ('{cmd_line}') заблокована!\n"
                        "Зміна стану сесії, леджера провененсу та секретів через шелл категорично заборонена."
                    )
                }
                print(json.dumps(res))
                return

        shell_redirect_matches = re.findall(r"(?:>|>>|\|\s*tee\s+-?a?)\s*([^\s;&|]+)", cmd_line)
        for target_match in shell_redirect_matches:
            clean_target = target_match.strip("\"'")
            if not clean_target:
                continue
            abs_redirect_target = os.path.realpath(os.path.abspath(clean_target))
            if (
                "/.system_generated" in abs_redirect_target or
                "provenance_ledger" in abs_redirect_target or
                "/flags/" in abs_redirect_target or
                "/core/" in abs_redirect_target or
                "approved_plan.sha256" in abs_redirect_target or
                ".secret" in abs_redirect_target.lower()
            ):
                log(f"HARD DENY: Shell State Isolation Gate blocked shell write to '{clean_target}' in '{cmd_line}'")
                res = {
                    "decision": "deny",
                    "reason": (
                        "HARD GATE VIOLATION (Shell State Isolation Gate v0.9.12):\n"
                        f"Спроба запису/перенаправлення виводу шеллу у захищені системні файли ('{clean_target}') заборонена!\n"
                        "Зміна стану сесії, леджера провененсу та вихідного коду фреймворку через шелл категорично заблокована. "
                        "Всі мутації коду повинні здійснюватися виключно через штатні інструменти IDE з валідацією криптографічних паспортів."
                    )
                }
                print(json.dumps(res))
                return

    # ============================================================
    # 1. HARD DENY GATE: Блокування сліпого обходу дисків (Git & Index First)
    # ============================================================
    if name in ("list_dir", "find_by_name", "grep_search"):
        log(f"HARD DENY: Attempted blind crawler tool '{name}'")
        res = {
            "decision": "deny",
            "reason": f"HARD GATE VIOLATION (Git & Index First): Використання '{name}' заборонено регламентом v0.7.1. Дослідження кодової бази має виконуватися виключно через 'git status', 'git log -n 5', 'git show HEAD:<файл>' або готові маніфести знань у docs/knowledge/index/."
        }
        print(json.dumps(res))
        return

    # ============================================================
    # 2. POLICY v0.7.2: Git-First Pipeline замість сліпого лічильника
    # ============================================================
    # Згідно з Регламентом v0.7.2 («Пиляти через Антігравіті зась!»), читання
    # файлів виконується через Git/Index First, а синтез коду — через Ollama/Groq.
    if name == "view_file":
        target = args.get("AbsolutePath", "")
        clean_target = target.strip().removeprefix("file://")
        abs_target = os.path.realpath(os.path.abspath(os.path.expanduser(clean_target)))
        norm_target = abs_target.replace("\\", "/").lower()
        if ".core_master_hmac.secret" in norm_target or ".secret" in norm_target:
            log(f"HARD DENY: Secret Isolation Gate blocked view_file on secret: {target}")
            res = {
                "decision": "deny",
                "reason": (
                    "HARD GATE VIOLATION (Secret Isolation Gate v0.9.12):\n"
                    f"Прямий перегляд файлів секретів ('{target}') через view_file суворо заборонено!\n"
                    "Криптографічні ключі ядра ізольовані та доступні виключно in-process внутрішніми функціями Python."
                )
            }
            print(json.dumps(res))
            return
        log(f"view_file invoked for: {args.get('AbsolutePath', '')}")

    # ============================================================
    # 3. HARD DENY GATE: Dynamic Plan-Aware Metric & Semantic Loop Gate (v0.9.4 / v0.9.8)
    # ============================================================
    # ІЗОЛЯЦІЯ СТАНУ ЗА СЕСІЄЮ ТА ВОРКСПЕЙСОМ (Kernel v0.9.8 Session Namespace):
    # Змінні sess_id, phase4_flag, step_file, contract_file, history_file, telemetry_flag ініціалізовано на початку main()


    # Авто-скидання застарілого лічильника кроків (TTL 15 хв бездіяльності)
    for s_file in all_step_files:
        if os.path.exists(s_file):
            try:
                if (time.time() - os.path.getmtime(s_file)) > 900:
                    os.remove(s_file)
            except Exception:
                pass

    # Завантаження динамічного контракту плану
    contract = {}
    dynamic_budget = 50  # Базовий динамічний поріг збільшено до 50 дій
    planned_files = []
    loop_window = 4
    max_identical = 2

    # 1. Спроба завантаження з json-контракту
    for c_file in all_contract_files:
        if os.path.exists(c_file):
            try:
                with open(c_file, "r", encoding="utf-8") as cf:
                    contract = json.load(cf)
                    dynamic_budget = contract.get("dynamic_step_budget", 50)
                    planned_files = contract.get("planned_files", [])
                    loop_window = contract.get("semantic_loop_window", 4)
                    max_identical = contract.get("max_identical_actions", 2)
                    break
            except Exception:
                pass

    # 2. Якщо json-контракту немає, динамічний розрахунок із найновішого implementation_plan.md
    if dynamic_budget == 50:
        brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
        if os.path.exists(brain_dir):
            cands = []
            for sdir in os.listdir(brain_dir):
                c_plan = os.path.join(brain_dir, sdir, "implementation_plan.md")
                if os.path.isfile(c_plan):
                    cands.append((os.path.getmtime(c_plan), c_plan))
            if cands:
                cands.sort(key=lambda x: x[0], reverse=True)
                latest_plan = cands[0][1]
                try:
                    with open(latest_plan, "r", encoding="utf-8") as pf:
                        p_txt = pf.read()
                        mods = len(re.findall(r"\[(MODIFY|NEW|DELETE)\]", p_txt))
                        if mods > 0:
                            dynamic_budget = max(50, mods * 10)
                except Exception:
                    pass

    # А. Семантичний детектор циклів (Semantic Loop Detector, W=4)
    try:
        norm_args = json.dumps(args, sort_keys=True)
    except Exception:
        norm_args = str(args)
    action_key = f"{name}:{norm_args}"
    action_hash = hashlib.sha256(action_key.encode("utf-8")).hexdigest()[:12]

    action_history = []
    for h_file in all_history_files:
        if os.path.exists(h_file):
            try:
                with open(h_file, "r", encoding="utf-8") as hf:
                    action_history = json.load(hf)
                    break
            except Exception:
                action_history = []

    recent_hashes = [item.get("hash") for item in action_history[-loop_window:]]
    if recent_hashes:
        if len(recent_hashes) >= 1 and recent_hashes[-1] == action_hash:
            log(f"HARD DENY: Semantic Loop Gate intercepted immediate duplicate action ({name})")
            res = {
                "decision": "deny",
                "reason": (
                    f"HARD GATE VIOLATION (Semantic Loop Gate v0.9.4):\n"
                    f"Виявлено зациклення агента на ідентичній дії: [{name}] '{action_key[:70]}'!\n"
                    "Дія щойно викликалася без зміни стану середовища. ReAct-ланцюг негайно зупинено "
                    "для захисту контексту та запобігання спалюванню токенів (перехоплення на 2-му кроці)."
                )
            }
            print(json.dumps(res))
            return
        elif recent_hashes.count(action_hash) >= max_identical:
            log(f"HARD DENY: Semantic Loop Gate intercepted loop in sliding window ({name})")
            res = {
                "decision": "deny",
                "reason": (
                    f"HARD GATE VIOLATION (Semantic Loop Gate v0.9.4):\n"
                    f"Виявлено циклічне повторення дії [{name}] ({recent_hashes.count(action_hash)} разів у вікні W={loop_window})!\n"
                    "ReAct-ланцюг зупинено для аналізу та зміни стратегії."
                )
            }
            print(json.dumps(res))
            return

    action_history.append({"hash": action_hash, "action": action_key[:80], "time": time.time()})
    for h_file in all_history_files:
        try:
            with open(h_file, "w", encoding="utf-8") as hf:
                json.dump(action_history[-20:], hf)
        except Exception:
            pass

    # Б. Контроль відхилення від плану (Plan Divergence Gate)
    if name in ("write_to_file", "replace_file_content"):
        t_file = args.get("TargetFile", "")
        if t_file:
            abs_t_file = os.path.abspath(t_file)
            base_t_file = os.path.basename(t_file)
            is_exempt = (
                base_t_file in ("walkthrough.md", "implementation_plan.md") or
                "/brain/" in abs_t_file or
                "/scratch/" in abs_t_file or
                not planned_files
            )
            if not is_exempt:
                in_plan = False
                for pf in planned_files:
                    if not pf or len(pf) < 3:
                        continue
                    clean_pf = pf.lstrip("/")
                    if abs_t_file == os.path.abspath(pf) or abs_t_file.endswith(clean_pf) or os.path.basename(pf) == base_t_file:
                        in_plan = True
                        break
                if not in_plan:
                    log(f"HARD DENY: Plan Divergence Gate blocked write to '{t_file}'")
                    res = {
                        "decision": "deny",
                        "reason": (
                            f"HARD GATE VIOLATION (Plan Divergence Gate v0.9.4):\n"
                            f"Спроба модифікації файлу '{t_file}', який ВІДСУТНІЙ у затвердженому контракті плану Фази 2!\n"
                            "Згідно з регламентом v0.9.4, зміна об'єктів поза затвердженим планом заборонена. "
                            "Оновіть implementation_plan.md та отримайте нове схвалення користувача."
                        )
                    }
                    print(json.dumps(res))
                    return

    # В. Динамічний ліміт кроків Фази 4 (Dynamic Step Budget v0.9.12)
    # Життєвий цикл Фази 5.2 Auto-Reset: якщо в сесії вже є walkthrough.md або запечатаний коміт
    has_walkthrough = False
    if brain_state_dir:
        b_parent = os.path.dirname(brain_state_dir)
        if os.path.isfile(os.path.join(b_parent, "walkthrough.md")):
            has_walkthrough = True
    if has_walkthrough:
        for f_clean in (all_phase4_flags + all_step_files):
            if os.path.exists(f_clean):
                try:
                    os.remove(f_clean)
                except Exception:
                    pass

    is_phase4_active = any(os.path.exists(pf) for pf in all_phase4_flags)
    if is_phase4_active:
        # Автоматичне скидання прапорців Фази 4 при створенні коміту
        if name == "run_command":
            cmd = args.get("CommandLine", "").strip()
            if cmd.startswith("git commit"):
                for f_clean in (all_phase4_flags + all_step_files):
                    if os.path.exists(f_clean):
                        try:
                            os.remove(f_clean)
                        except Exception:
                            pass

        step_count = 0
        for sf in all_step_files:
            if os.path.exists(sf):
                try:
                    with open(sf, "r") as f:
                        step_count = int(f.read().strip())
                        break
                except Exception:
                    pass

        is_diag_cmd = False
        if name == "run_command":
            cmd = args.get("CommandLine", "").strip()
            diag_prefixes = (
                "git status", "git diff", "git log", "git show", "sha256sum",
                "python3 -m py_compile", "readlink", "diff", "find",
                "python3 core/verify/chat_context_auditor.py",
                "python3 core/enclave/enclave_daemon.py",
                "python3 core/inspect/phase1_inspect.py",
                "python3 core/verify/phase5_verify.py"
            )
            if any(cmd.startswith(p) or f"/{p}" in cmd for p in diag_prefixes):
                is_diag_cmd = True
        is_read_only = (name in ("view_file", "list_dir", "grep_search", "find_by_name")) or is_diag_cmd

        # Kernel v0.9.12: Read-only та діагностичні команди мають безумовний імунітет
        if not is_read_only:
            step_count += 1
            for sf in all_step_files:
                try:
                    with open(sf, "w") as f:
                        f.write(str(step_count))
                except Exception:
                    pass

            if step_count > dynamic_budget:
                log(f"Phase 4 dynamic step budget pause (steps={step_count} > {dynamic_budget})")
                res = {
                    "decision": "ask",
                    "reason": (
                        f"DYNAMIC 2D-TELEMETRY & STEP BUDGET PAUSE (Kernel v0.9.12):\n"
                        f"Досягнуто планового порогу дій Фази 4 ({step_count} > {dynamic_budget} дій для поточного плану).\n"
                        "Зупинка ReAct-ланцюга для звіту про статус об'єктів. "
                        "Надішліть '+' для подовження бюджету (+30 дій) або використайте /bridge."
                    )
                }
                print(json.dumps(res))
                return

    needs_prompt = False

    # 1. Interactive questions tool
    if name == "ask_question":
        needs_prompt = True
        play_sound()
        res = {"decision": "allow"}
        log(f"tool={name} needs_prompt=True, returning allow")
        print(json.dumps(res))
        return

    # 2. run_command with sandbox bypass:
    # HOST-FIRST EXECUTION PROTOCOL (v0.8.3):
    # Довірені префікси команд, які вимагають доступу до хоста (Ollama loopback, Git, Wine, аудіо, раннери),
    # авторизовані регламентом і виконуються БЕЗ модального запиту з боку pre_tool_hook.py.
    if name == "run_command":
        cmd_line = args.get("CommandLine", "").strip()
        cmd_cwd = args.get("Cwd", os.getcwd())
        # Санітизація лапок (Policy v0.9.7): зняття зовнішніх лапок та нормалізація внутрішніх шляхів
        cmd_clean = cmd_line.strip("\"'")
        cmd_norm = cmd_clean
        if cmd_clean.startswith("python3 \"") or cmd_clean.startswith("python3 '"):
            cmd_norm = "python3 " + cmd_clean[8:].strip("\"'")

        # ПЕРЕВІРКА ЦІЛІСНОСТІ СКРИПТІВ ПЕРЕД ЗАПУСКОМ (Policy v0.9.8)
        # Захист від запуску неавторизованого DIY-коду проєкту
        script_to_check = None
        cmd_parts = cmd_norm.split()
        if cmd_parts and cmd_parts[0] in ("python", "python3") and len(cmd_parts) > 1:
            arg1 = cmd_parts[1].strip("\"'")
            if not arg1.startswith("-") and (arg1.endswith(".py") or arg1.endswith(".sh") or arg1.endswith(".bash")):
                script_to_check = arg1

        if script_to_check:
            abs_script = os.path.abspath(os.path.join(cmd_cwd, script_to_check) if not os.path.isabs(script_to_check) else script_to_check)
            script_base = os.path.basename(abs_script)
            framework_tools = (
                "diagnostic_runner.py", "enclave_daemon.py", "phase5_verify.py", "validate_general_policy.py",
                "verify_remote_ci.py", "phase4_provenance.py", "phase2_router.py",
                "phase1_inspect.py", "check_rag_health.py", "chat_context_auditor.py"
            )
            is_framework_tool = script_base in framework_tools or "/core/" in abs_script

            if not is_framework_tool and os.path.isfile(abs_script):
                # Обчислення поточного хешу на диску
                try:
                    with open(abs_script, "rb") as sf:
                        curr_disk_hash = hashlib.sha256(sf.read()).hexdigest()
                except Exception:
                    curr_disk_hash = ""

                ledger_paths = [p for p in (
                    brain_ledger,
                    "/tmp/antigravity_provenance_ledger.json",
                    os.path.expanduser("~/Documents/.agents/.provenance_ledger.json")
                ) if p]
                run_ledger = {}
                for lp in ledger_paths:
                    if os.path.exists(lp):
                        try:
                            with open(lp, "r", encoding="utf-8") as lf:
                                run_ledger.update(json.load(lf))
                        except Exception:
                            pass

                script_authorized = False
                if abs_script in run_ledger:
                    reg_hash = run_ledger[abs_script].get("sha256")
                    if reg_hash and reg_hash == curr_disk_hash:
                        script_authorized = True
                    else:
                        log(f"HARD DENY: Script integrity mismatch for '{abs_script}' (disk={curr_disk_hash} != reg={reg_hash})")
                        res = {
                            "decision": "deny",
                            "reason": (
                                "HARD GATE VIOLATION (Zero DIY Coding / Script Integrity Mismatch v0.9.8):\n"
                                f"Хеш скрипта на диску '{abs_script}' ({curr_disk_hash[:16]}...) не збігається із зареєстрованим у леджері ({str(reg_hash)[:16]}...). "
                                "Скрипт був модифікований без повторного санкціонованого синтезу ШІ або валідації."
                            )
                        }
                        print(json.dumps(res))
                        return

                if not script_authorized:
                    for flag_p in ("/tmp/antigravity_ollama_synthesized.flag", "/tmp/antigravity_provenance_valid.flag"):
                        if os.path.exists(flag_p):
                            try:
                                with open(flag_p, "r", encoding="utf-8") as vff:
                                    if abs_script in vff.read():
                                        script_authorized = True
                                        break
                            except Exception:
                                pass

                if not script_authorized:
                    log(f"HARD DENY: Unregistered script execution attempt: '{abs_script}'")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Zero DIY Coding / Unregistered Script Execution Gate v0.9.8):\n"
                            f"Запуск скрипта '{abs_script}' відхилено: файл не зареєстрований у сесійному чи персистентному реєстрі провененсу ШІ. "
                            "Виконуваний код має бути згенерований через Ollama/Groq або валідований через Phase 4 Provenance."
                        )
                    }
                    print(json.dumps(res))
                    return

        bypass = args.get("BypassSandbox")
        if bypass is True or bypass == "true":
            home = os.path.expanduser("~")
            trusted_host_prefixes = (
                "git ",
                "copilot ",
                "copilot",
                os.path.join(home, ".local/bin/copilot"),
                "python3 .agents/scripts/diagnostic_runner.py",
                f"python3 {home}/Documents/.agents/scripts/diagnostic_runner.py",
                "python3 core/engine/diagnostic_runner.py",
                f"python3 {home}/Documents/Hybrid-IDE-for-contributors/core/engine/diagnostic_runner.py",
                "python3 core/enclave/enclave_daemon.py",
                f"python3 {home}/Documents/Hybrid-IDE-for-contributors/core/enclave/enclave_daemon.py",
                f"python3 {home}/.gemini/config/plugins/hybrid-ide/bin/",
                "python3 .agents/tools/",
                f"python3 {home}/Documents/.agents/tools/",
                "aplay "
            )
            is_trusted = any(cmd_clean.startswith(p) or cmd_norm.startswith(p) for p in trusted_host_prefixes)
            if not is_trusted:
                needs_prompt = True

    # ============================================================
    # 3. SELECTIVE CODE GUARD (v0.9.1): Захист від самостійного написання коду
    # ============================================================
    if name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
        target_file = args.get("TargetFile", "")
        if target_file:
            clean_tf = target_file.strip().removeprefix("file://")
            abs_norm = os.path.realpath(os.path.abspath(os.path.expanduser(clean_tf)))
            normalized = abs_norm.replace("\\", "/").lower()
            base_name = os.path.basename(normalized)

            # ============================================================
            # LEDGER IMMUTABILITY & SECRET ISOLATION GATE (Kernel v0.9.12)
            # ============================================================
            is_ledger_file = (
                "provenance_ledger" in normalized or
                base_name.startswith("provenance_ledger")
            )
            is_secret_file = (
                ".core_master_hmac.secret" in normalized or
                ".secret" in normalized
            )
            is_flag_state = (
                "/.system_generated/flags/" in normalized or
                normalized.endswith("/.system_generated/flags")
            )
            
            if is_ledger_file or is_secret_file or is_flag_state:
                log(f"HARD DENY: Ledger Immutability Gate blocked {name} on protected state file '{target_file}'")
                res = {
                    "decision": "deny",
                    "reason": (
                        "HARD GATE VIOLATION (Ledger Immutability Gate v0.9.12):\n"
                        f"Пряма модифікація захищених системних файлів ('{target_file}') через інструмент '{name}' суворо заборонена!\n"
                        "Реєстр провененсу, криптографічні секрети та прапорці сесії оновлюються ВИКЛЮЧНО "
                        "внутрішніми модулями ядра Python (apply_passport / save_ledger). "
                        "Спроба фальсифікації паспортів або стану сесії відхилена."
                    )
                }
                print(json.dumps(res))
                return

            # ============================================================
            # PHASE 1 TELEMETRY GATE (Kernel v0.9.8): Блокування Фази 2 та мутацій без телеметрії
            # ============================================================
            controlled_code_exts = (".py", ".sh", ".bash", ".ts", ".js", ".pas", ".cpp", ".h", ".go", ".rs", ".java", ".psc")
            is_code_file = any(normalized.endswith(ext) for ext in controlled_code_exts)
            is_plan_artifact = base_name == "implementation_plan.md"

            if is_plan_artifact or is_code_file:
                has_telemetry = False
                for tf_path in all_telemetry_flags:
                    if os.path.exists(tf_path):
                        try:
                            if (time.time() - os.path.getmtime(tf_path)) < 1800:
                                has_telemetry = True
                                break
                        except Exception:
                            pass
                if not has_telemetry:
                    log(f"HARD DENY: Telemetry Gate blocked {name} on '{target_file}' - telemetry not inspected")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Phase 1 Telemetry Gate v0.9.8):\n"
                            f"Виклик '{name}' для '{target_file}' заблоковано!\n"
                            "Згідно з Регламентом v0.9.8, перехід до планування (Фаза 2) або модифікація файлів коду "
                            "вимагає попереднього обов'язкового виміру 2D-телеметрії контексту сесії.\n"
                            "Виконайте обов'язкову команду:\n"
                            "python3 core/inspect/phase1_inspect.py --telemetry\n"
                            "після чого повторіть дію."
                        )
                    }
                    print(json.dumps(res))
                    return

            # 1. Документація, плани, звіти, конфігурації та системні артефакти (Policy v0.9.3)

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
                    ledger_paths = [brain_ledger] if brain_ledger else []
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
                        log(f"HARD DENY: Repository Docs Hygiene Gate blocked DIY doc synthesis on '{target_file}' ({content_len} bytes)")
                        res = {
                            "decision": "deny",
                            "reason": (
                                "HARD GATE VIOLATION (Repository Docs Hygiene Gate v0.9.3):\n"
                                f"Заборонено прямий DIY-синтез великої проєктної документації ({target_file}, {content_len} байт > 1.5 КБ) оркестратором!\n"
                                "Для захисту контексту від роздуття (Context Bloat) та збереження бюджету дій, великі посібники та шаблони зобов'язані генеруватися моделями ШІ (Tier 1 Ollama або Tier 2 Groq) через:\n"
                                f"python3 .agents/scripts/diagnostic_runner.py --groq-query \"<ТЗ>\" --out {target_file}\n"
                                "або вноситися точковими латками (<1.5 КБ) через replace_file_content."
                            )
                        }
                        print(json.dumps(res))
                        return

            is_doc = is_lifecycle_artifact or is_config_file or (is_repo_doc and not is_code_file)

            # Автоматичне керування життєвим циклом Фази 4 через ключові артефакти
            if base_name == "implementation_plan.md":
                try:
                    for pf_path in all_phase4_flags:
                        with open(pf_path, "w") as pf:
                            pf.write("active")
                    for sf_path in all_step_files:
                        with open(sf_path, "w") as sf:
                            sf.write("0")
                    for hf_path in all_history_files:
                        if os.path.exists(hf_path):
                            os.remove(hf_path)
                except Exception:
                    pass
            elif base_name == "walkthrough.md":
                try:
                    for f_to_clean in (all_phase4_flags + all_step_files + all_contract_files + all_history_files):
                        if os.path.exists(f_to_clean):
                            os.remove(f_to_clean)
                except Exception:
                    pass

            if not is_doc:
                # 2. Контрольовані файли коду (*.py, *.sh, *.bash, *.ts, *.js, *.pas, *.cpp, *.h, *.go)
                # HARD GATE: Вимагається обов'язкова реєстрація в реєстрі провененсу
                abs_target = os.path.realpath(os.path.abspath(target_file))
                baseline_sha256 = None
                if os.path.isfile(abs_target):
                    try:
                        h = hashlib.sha256()
                        with open(abs_target, "rb") as bf:
                            while chunk := bf.read(65536):
                                h.update(chunk)
                        baseline_sha256 = h.hexdigest()
                    except Exception:
                        pass

                target_sha256 = None
                prov_hooks = _import_provenance_hooks()
                reserve_fn, sim_fn = prov_hooks[0], prov_hooks[1]

                if name == "write_to_file":
                    code_content = args.get("CodeContent", "")
                    target_sha256 = hashlib.sha256(code_content.encode("utf-8")).hexdigest()
                elif name == "replace_file_content":
                    target_content = args.get("TargetContent", "")
                    replacement_content = args.get("ReplacementContent", "")
                    start_line = args.get("StartLine")
                    end_line = args.get("EndLine")
                    allow_multiple = args.get("AllowMultiple", False)

                    try:
                        with open(abs_target, "rb") as f:
                            content_bytes = f.read()
                    except Exception as e:
                        content_bytes = b""

                    if sim_fn:
                        ok_sim, sim_bytes, sim_err = sim_fn(
                            content_bytes=content_bytes,
                            target_bytes=target_content.encode("utf-8"),
                            replacement_bytes=replacement_content.encode("utf-8"),
                            start_line=start_line,
                            end_line=end_line,
                            allow_multiple=allow_multiple
                        )
                        if not ok_sim:
                            log(f"HARD DENY: In-memory replacement simulation failed for '{target_file}': {sim_err}")
                            res = {
                                "decision": "deny",
                                "reason": (
                                    "HARD GATE VIOLATION (In-Memory Replacement Simulation Gate v0.9.12):\n"
                                    f"Симуляція заміни для '{target_file}' завершилася помилкою: {sim_err}.\n"
                                    "Заміна відхилена через невідповідність межам або порожній TargetContent."
                                )
                            }
                            print(json.dumps(res))
                            return
                        target_sha256 = hashlib.sha256(sim_bytes).hexdigest()

                authorized = False
                reserve_reason = ""
                passport_id = None

                # Спроба резервування криптографічного паспорта (Policy v0.9.12)
                if reserve_fn and target_sha256:
                    ok_res, p_id, p_msg = reserve_fn(
                        session_id=sess_id,
                        file_path=abs_target,
                        baseline_sha256=baseline_sha256,
                        target_sha256=target_sha256,
                        tool_name=name
                    )
                    if ok_res:
                        authorized = True
                        passport_id = p_id
                        log(f"Passport {p_id} RESERVED for {name} on {target_file}")
                    else:
                        reserve_reason = p_msg

                # Перевірка структурованих прапорців сесії у brain_state_dir
                if not authorized and brain_state_dir:
                    flags_dir = os.path.join(brain_state_dir, "flags")
                    if os.path.isdir(flags_dir):
                        for fj in os.listdir(flags_dir):
                            if fj.endswith(".json"):
                                try:
                                    with open(os.path.join(flags_dir, fj), "r", encoding="utf-8") as f_json:
                                        meta = json.load(f_json)
                                        if meta.get("meta", {}).get("file_path") == abs_target:
                                            if meta.get("meta", {}).get("target_sha256") == target_sha256:
                                                authorized = True
                                                break
                                except Exception:
                                    pass

                # Перевірка Contributor Mode для ядра (Kernel v0.9.12)
                if not authorized:
                    is_core_maintenance = (
                        "/core/" in abs_target or
                        "/.agents/" in abs_target or
                        "/Antigravity_Mgr/" in abs_target or
                        abs_target.endswith("AGENTS.md") or
                        abs_target.endswith("setup_and_verify.sh") or
                        abs_target.endswith("build_dist.sh") or
                        abs_target.endswith("push_to_github.sh")
                    )
                    if is_core_maintenance:
                        if verify_contributor_plan_sanction(brain_state_dir, abs_target, base_name):
                            authorized = True
                            log(f"Contributor Mode SANCTION verified for core maintenance on '{target_file}'")

                if not authorized:
                    log(f"HARD DENY: Selective Code Guard blocked unauthenticated edit on '{target_file}' via {name}")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Cryptographic Hash Passport Integrity Gate v0.9.12):\n"
                            f"Заборонено несанкціоноване створення/редагування коду через {name} на '{target_file}'.\n"
                            f"Причина відхилення паспорта: {reserve_reason or 'відсутній валідний MINTED паспорт у леджері'}.\n"
                            "Код зобов'язаний попередньо генеруватися ШІ-моделями (Tier 1 Ollama / Tier 2 Groq) через diagnostic_runner.py, "
                            "яка випускає активний криптографічний паспорт провененсу, або мати санкцію Contributor Mode (approved_plan.sha256)."
                        )
                    }
                    print(json.dumps(res))
                    return

            # Перевірка довірених просторів
            home = os.path.expanduser("~")
            trusted_host_roots = (
                os.path.join(home, "Documents"),
                os.path.join(home, ".gemini/antigravity/brain"),
                os.path.join(home, ".gemini/config")
            )
            in_trusted = any(target_file.startswith(tr) for tr in trusted_host_roots) or (
                workspace_paths and any(target_file.startswith(wp) for wp in workspace_paths)
            )
            if not in_trusted:
                needs_prompt = True

    if needs_prompt:
        play_sound()
        res = {
            "decision": "ask",
            "reason": f"Access request for tool: {name}"
        }
        log(f"tool={name} needs_prompt=True, returning ask")
    else:
        res = {
            "decision": "allow"
        }
        log(f"tool={name} needs_prompt=False, returning allow")

    print(json.dumps(res))

if __name__ == "__main__":
    main()

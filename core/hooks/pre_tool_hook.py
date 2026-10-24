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
    SOUND_PATH = "/home/hills/.gemini/config/sounds/access_request.wav"

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
    if artifact_dir and os.path.exists(artifact_dir):
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

    # Fallback /tmp шляхи
    phase4_flag = f"/tmp/antigravity_phase4_{sess_id}.flag"
    legacy_phase4_flag = "/tmp/antigravity_phase4_active.flag"
    contract_file = f"/tmp/antigravity_phase4_contract_{sess_id}.json"
    legacy_contract_file = "/tmp/antigravity_phase4_contract.json"
    history_file = f"/tmp/antigravity_action_history_{sess_id}.json"
    step_file = f"/tmp/antigravity_phase4_steps_{sess_id}.txt"
    legacy_step_file = "/tmp/antigravity_phase4_steps.txt"
    telemetry_flag = f"/tmp/antigravity_telemetry_{sess_id}.flag"
    legacy_telemetry_flag = "/tmp/antigravity_telemetry_inspected.flag"

    all_telemetry_flags = [f for f in (brain_telemetry_flag, telemetry_flag, legacy_telemetry_flag) if f]
    all_phase4_flags = [f for f in (brain_phase4_flag, phase4_flag, legacy_phase4_flag) if f]
    all_contract_files = [f for f in (brain_contract_file, contract_file, legacy_contract_file) if f]
    all_history_files = [f for f in (brain_history_file, history_file, "/tmp/antigravity_action_history.json") if f]
    all_step_files = [f for f in (brain_step_file, step_file, legacy_step_file) if f]
    all_claude_flags = [f for f in (brain_claude_flag, "/tmp/antigravity_claude_verified.flag") if f]
    all_copilot_flags = [f for f in (brain_copilot_flag, brain_copilot_auth_flag, "/tmp/antigravity_copilot_executed.flag", "/tmp/antigravity_copilot_authorized.flag") if f]

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
            prov_tool = "/home/hills/Documents/Antigravity_Mgr/tools/phase4_provenance.py"
            if not os.path.exists(prov_tool):
                prov_tool = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "provenance", "phase4_provenance.py"))
            if not os.path.exists(prov_tool):
                prov_tool = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "tools", "phase4_provenance.py"))
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
            is_copilot_cli = any(tok in ("copilot", "/home/hills/.local/bin/copilot") for tok in cmd_line.split())
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
        # RUNTIME CIRCUIT BREAKER GATE (v0.8.2): Зупинка після 2 збоїв
        # ============================================================
        cb_file = "/tmp/antigravity_circuit_breaker_fails.txt"
        if os.path.exists(cb_file) and not ("git status" in cmd_line or "validate_general_policy" in cmd_line):
            try:
                with open(cb_file, "r") as f:
                    fails = int(f.read().strip())
                if fails >= 2:
                    log(f"HARD DENY: Circuit Breaker triggered ({fails} consecutive failures)")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Runtime Circuit Breaker Tripped v0.8.2):\n"
                            f"Зафіксовано {fails} послідовних збоїв виконання скрипта/команди.\n"
                            "Автоматичний ReAct цикл зупинено для захисту токенів та запобігання зацикленню.\n"
                            "Опублікуйте проміжний звіт у чат та узгодьте план дій із користувачем."
                        )
                    }
                    print(json.dumps(res))
                    return
            except Exception:
                pass

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

    # В. Динамічний ліміт кроків Фази 4 (Dynamic Step Budget)
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
            if any(cmd.startswith(p) for p in ("git status", "git diff", "git log", "git show", "sha256sum", "python3 -m py_compile", "readlink", "diff", "find")):
                is_diag_cmd = True
        is_read_only = (name in ("view_file", "list_dir", "grep_search", "find_by_name")) or is_diag_cmd
        if not is_read_only:
            step_count += 1
            for sf in all_step_files:
                try:
                    with open(sf, "w") as f:
                        f.write(str(step_count))
                except Exception:
                    pass

        if step_count > dynamic_budget:
            log(f"HARD DENY: Phase 4 dynamic step budget exceeded (steps={step_count} > {dynamic_budget})")
            res = {
                "decision": "deny",
                "reason": (
                    f"HARD GATE VIOLATION (Dynamic Plan-Aware Metric & Semantic Loop Gate v0.9.4):\n"
                    f"Перевищено динамічний бюджет дій Фази 4 ({step_count} > {dynamic_budget} дій для плану).\n"
                    "Необхідно зупинити ReAct-ланцюг та опублікувати проміжний звіт у чат."
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
                "diagnostic_runner.py", "phase5_verify.py", "validate_general_policy.py",
                "verify_remote_ci.py", "phase4_provenance.py", "phase2_router.py",
                "phase1_inspect.py", "check_rag_health.py"
            )
            is_framework_tool = script_base in framework_tools or "/core/" in abs_script

            if not is_framework_tool and os.path.isfile(abs_script):
                # Обчислення поточного хешу на диску
                try:
                    with open(abs_script, "rb") as sf:
                        curr_disk_hash = hashlib.sha256(sf.read()).hexdigest()
                except Exception:
                    curr_disk_hash = ""

                ledger_paths = [
                    "/tmp/antigravity_provenance_ledger.json",
                    "/home/hills/Documents/.agents/.provenance_ledger.json"
                ]
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
            trusted_host_prefixes = (
                "git ",
                "copilot ",
                "copilot",
                "/home/hills/.local/bin/copilot",
                "python3 .agents/scripts/diagnostic_runner.py",
                "python3 /home/hills/Documents/.agents/scripts/diagnostic_runner.py",
                "python3 core/engine/diagnostic_runner.py",
                "python3 /home/hills/Documents/Hybrid-IDE-for-contributors/core/engine/diagnostic_runner.py",
                "python3 Antigravity_Mgr/tools/",
                "python3 /home/hills/Documents/Antigravity_Mgr/tools/",
                "python3 .agents/tools/",
                "python3 /home/hills/Documents/.agents/tools/",
                "python3 F4 modding/",
                "python3 /home/hills/Documents/fallaut/F4 modding/",
                "python3 fallaut/",
                "aplay "
            )
            is_trusted = any(cmd_clean.startswith(p) or cmd_norm.startswith(p) for p in trusted_host_prefixes)
            if not is_trusted:
                needs_prompt = True

    # ============================================================
    # 3. SELECTIVE CODE GUARD (v0.9.1): Захист від самостійного написання коду
    # ============================================================
    if name in ("write_to_file", "replace_file_content"):
        target_file = args.get("TargetFile", "")
        if target_file:
            normalized = target_file.replace("\\", "/").lower()
            base_name = os.path.basename(normalized)

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
                    ledger_paths = [p for p in (
                        brain_ledger,
                        "/tmp/antigravity_provenance_ledger.json",
                        "/home/hills/Documents/.agents/.provenance_ledger.json"
                    ) if p]
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
                abs_target = os.path.abspath(target_file)
                code_content = args.get("CodeContent", "")
                repl_content = args.get("ReplacementContent", "")

                content_hashes = []
                if code_content:
                    content_hashes.append(hashlib.sha256(code_content.encode("utf-8")).hexdigest())
                if repl_content:
                    content_hashes.append(hashlib.sha256(repl_content.encode("utf-8")).hexdigest())

                ledger_paths = [p for p in (
                    brain_ledger,
                    "/tmp/antigravity_provenance_ledger.json",
                    "/home/hills/Documents/.agents/.provenance_ledger.json"
                ) if p]
                ledger = {}
                for lp in ledger_paths:
                    if os.path.exists(lp):
                        try:
                            with open(lp, "r", encoding="utf-8") as lf:
                                ledger.update(json.load(lf))
                        except Exception:
                            pass

                authorized = False

                # ЛІКВІДАЦІЯ SHORT-CIRCUIT & STRICT TARGET BINDING (Kernel v0.9.8):
                # Для write_to_file: хеш нового контенту зобов'язаний збігатися з зареєстрованим хешем САМЕ ЦЬОГО файлу в леджері
                if name == "write_to_file":
                    if abs_target in ledger:
                        reg_hash = ledger[abs_target].get("sha256")
                        if reg_hash and reg_hash in content_hashes:
                            authorized = True

                # Для replace_file_content: прямий DIY-патч коду оркестратором заборонено.
                # Дозволяється лише за наявності активного сесійного прапорця авторизації
                # або якщо це файл ядра/інструментів у межах затвердженого плану.
                elif name == "replace_file_content":
                    pass

                # Перевірка сесійних прапорців валідації/синтезу
                if not authorized:
                    for flag_path in (
                        os.path.join(brain_state_dir, "provenance_valid.flag") if brain_state_dir else None,
                        os.path.join(brain_state_dir, "ollama_synthesized.flag") if brain_state_dir else None,
                        brain_copilot_flag,
                        "/tmp/antigravity_provenance_valid.flag",
                        "/tmp/antigravity_ollama_synthesized.flag",
                        "/tmp/antigravity_copilot_executed.flag"
                    ):
                        if flag_path and os.path.exists(flag_path):
                            try:
                                with open(flag_path, "r", encoding="utf-8") as vf:
                                    flag_txt = vf.read()
                                    if abs_target in flag_txt:
                                        authorized = True
                                        break
                            except Exception:
                                pass

                # Для файлів ядра фреймворку (Hybrid-IDE / .agents / Antigravity_Mgr):
                # якщо Фаза 4 активна за затвердженим планом (implementation_plan.md)
                if not authorized and any(os.path.exists(pf) for pf in all_phase4_flags):
                    is_core_maintenance = (
                        "/core/" in abs_target or
                        "/.agents/" in abs_target or
                        "/Antigravity_Mgr/" in abs_target or
                        abs_target.endswith("AGENTS.md")
                    )
                    if is_core_maintenance:
                        plan_path = None
                        brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
                        if os.path.exists(brain_dir):
                            # Знаходимо найновіший implementation_plan.md за mtime
                            candidates = []
                            for sdir in os.listdir(brain_dir):
                                cand = os.path.join(brain_dir, sdir, "implementation_plan.md")
                                if os.path.isfile(cand):
                                    candidates.append((os.path.getmtime(cand), cand))
                            if candidates:
                                candidates.sort(key=lambda x: x[0], reverse=True)
                                plan_path = candidates[0][1]
                        if plan_path and os.path.exists(plan_path):
                            try:
                                with open(plan_path, "r", encoding="utf-8") as pf:
                                    plan_content = pf.read()
                                    if base_name in plan_content or abs_target in plan_content:
                                        authorized = True
                            except Exception:
                                pass

                if not authorized:
                    log(f"HARD DENY: Selective Code Guard blocked DIY code edit on '{target_file}' via {name}")
                    res = {
                        "decision": "deny",
                        "reason": (
                            "HARD GATE VIOLATION (Zero DIY Coding / Strict Hash Integrity Gate v0.9.8):\n"
                            f"Заборонено несанкціоноване створення/редагування виконуваного коду через {name} на '{target_file}'.\n"
                            "Хеш контенту не збігається із зареєстрованим ШІ-хешем у леджері, або відсутній активний сесійний прапорець генерації.\n"
                            "Код має бути синтезований локальною Ollama (python3 .agents/scripts/diagnostic_runner.py --synthesize-script \"<task>\" --out <file>) або узгоджений через Phase 4 Provenance."
                        )
                    }
                    print(json.dumps(res))
                    return

            # Перевірка довірених просторів
            trusted_host_roots = (
                "/home/hills/Documents",
                "/home/hills/.gemini/antigravity/brain",
                "/home/hills/.gemini/config"
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

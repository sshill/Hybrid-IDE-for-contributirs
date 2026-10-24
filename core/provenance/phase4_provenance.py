#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фаза 4: Сесійний реєстр провененсу та Anti-Shadow Execution Gate.
Шлях: /home/hills/Documents/Antigravity_Mgr/tools/phase4_provenance.py
Стандарт: SLSA / in-toto Cryptographic Attestation (Zero-Dep stdlib).
Гарантує, що жоден виконуваний скрипт не підкинуто в обхід моделей ШІ.
"""

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True

LEDGER_PATH = "/tmp/antigravity_provenance_ledger.json"
PERSISTENT_LEDGER_PATH = os.environ.get("HYBRID_IDE_LEDGER", "/home/hills/Documents/.agents/.provenance_ledger.json")

def resolve_brain_state_dir() -> str:
    """Визначає персистентний Brain-First каталог стану сесії."""
    brain_root = os.path.expanduser("~/.gemini/antigravity/brain")
    if os.path.exists(brain_root):
        try:
            cands = [os.path.join(brain_root, d) for d in os.listdir(brain_root) if os.path.isdir(os.path.join(brain_root, d))]
            if cands:
                cands.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                sg = os.path.join(cands[0], ".system_generated")
                os.makedirs(sg, exist_ok=True)
                return sg
        except Exception:
            pass
    return None

def resolve_brain_ledger_path() -> str:
    """Визначає персистентний Brain-First шлях леджера провененсу."""
    sg = resolve_brain_state_dir()
    if sg:
        return os.path.join(sg, "provenance_ledger.json")
    return None

def get_file_sha256(path: str) -> str:
    """Обчислення SHA256 хешу файлу."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_content_sha256(content: str) -> str:
    """Обчислення SHA256 хешу текстового рядка."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def load_ledger() -> dict:
    """Завантаження реєстру з Brain-First сховища, /tmp та автоматичним відновленням із персистентного сховища."""
    ledger = {}
    if os.path.exists(PERSISTENT_LEDGER_PATH):
        try:
            with open(PERSISTENT_LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger.update(json.load(f))
        except Exception:
            pass

    brain_ledger = resolve_brain_ledger_path()
    if brain_ledger and os.path.exists(brain_ledger):
        try:
            with open(brain_ledger, "r", encoding="utf-8") as f:
                ledger.update(json.load(f))
        except Exception:
            pass

    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger.update(json.load(f))
        except Exception:
            pass
    return ledger

def save_ledger(ledger: dict):
    """Синхронне атомарне збереження реєстру в Brain-First, /tmp та у персистентне сховище .agents/."""
    targets = [PERSISTENT_LEDGER_PATH, LEDGER_PATH]
    brain_ledger = resolve_brain_ledger_path()
    if brain_ledger:
        targets.insert(0, brain_ledger)

    for path in targets:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = path + f".tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    json.dump(ledger, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"⚠️ Попередження: не вдалося зберегти реєстр у {path}: {e}", file=sys.stderr)

def register_provenance(
    script_path: str,
    model: str = "qwen2.5-coder:1.5b",
    sha256_hash: str = None,
    source_prompt: str = None,
    eval_count: int = None,
    prompt_eval_duration_ms: float = None
) -> bool:
    """Реєстрація хешу та метаданих ШІ-синтезу в сесійному та персистентному реєстрі."""
    abs_path = os.path.abspath(script_path)
    if sha256_hash is None:
        if not os.path.isfile(abs_path):
            print(f"❌ Файл для реєстрації не знайдено: {abs_path}", file=sys.stderr)
            return False
        sha256_hash = get_file_sha256(abs_path)

    # АНТИ-ФАЛЬСИФІКАЦІЙНИЙ ШЛЮЗ (Anti-Forgery Provenance Gate v0.9.8):
    # Забороняє фіктивну реєстрацію без реальних метрик або прапорця генератора
    is_ollama_model = any(k in model.lower() for k in ("qwen", "llama", "coder", "deepseek", "mistral", "gemma", "ollama"))
    if is_ollama_model:
        has_metrics = (eval_count is not None and eval_count > 0 and 
                       prompt_eval_duration_ms is not None and prompt_eval_duration_ms > 0)
        has_valid_flag = False
        flag_p = "/tmp/antigravity_ollama_synthesized.flag"
        if os.path.exists(flag_p):
            try:
                if (time.time() - os.path.getmtime(flag_p)) < 900:
                    with open(flag_p, "r", encoding="utf-8") as f_fl:
                        if abs_path in f_fl.read():
                            has_valid_flag = True
            except Exception:
                pass

        if not (has_metrics or has_valid_flag):
            print(
                f"❌ [HARD REJECT] Фальсифікація провененсу виявлена!\n"
                f"   Спроба зареєструвати файл {os.path.basename(abs_path)} за моделлю '{model}' без реального інференсу.\n"
                f"   Відсутні обов'язкові поля eval_count / prompt_eval_duration_ms або активний сесійний прапорець генерації.\n"
                f"   Код має генеруватися через канонічний раннер: diagnostic_runner.py --synthesize-script",
                file=sys.stderr
            )
            return False

    entry = {
        "sha256": sha256_hash,
        "model": model,
        "registered_at": time.time(),
        "path": abs_path
    }
    if source_prompt is not None:
        entry["source_prompt"] = source_prompt
    if eval_count is not None:
        entry["eval_count"] = eval_count
    if prompt_eval_duration_ms is not None:
        entry["prompt_eval_duration_ms"] = prompt_eval_duration_ms

    try:
        ledger = load_ledger()
        ledger[abs_path] = entry
        save_ledger(ledger)

        # Створення сесійного прапорця валідації (Brain-First + /tmp)
        valid_text = f"PROVENANCE_VALID: {abs_path} at {time.time()} by {model}\n"
        sg = resolve_brain_state_dir()
        if sg:
            try:
                with open(os.path.join(sg, "provenance_valid.flag"), "w", encoding="utf-8") as bf:
                    bf.write(valid_text)
            except Exception:
                pass
        try:
            with open("/tmp/antigravity_provenance_valid.flag", "w", encoding="utf-8") as flag_f:
                flag_f.write(valid_text)
        except Exception:
            pass

        print(f"🔒 [PROVENANCE REGISTERED] Файл {os.path.basename(abs_path)} зареєстровано (SHA256: {sha256_hash[:16]}..., Model: {model})")
        return True
    except Exception as e:
        print(f"❌ Помилка запису в реєстр провененсу: {e}", file=sys.stderr)
        return False

def verify_provenance(script_path: str) -> tuple[bool, str]:
    """Верифікація цілісності та походження скрипта перед виконанням."""
    abs_path = os.path.abspath(script_path)
    if not os.path.isfile(abs_path):
        return False, f"Файл не існує: {abs_path}"

    ledger = load_ledger()
    if not ledger:
        return False, "Реєстр провененсу порожній або відсутній (перевірено /tmp та .agents/.provenance_ledger.json)."

    record = ledger.get(abs_path)
    if not record:
        return False, f"Файл не зареєстровано в сесійному реєстрі ШІ-генерації: {abs_path}"

    current_hash = get_file_sha256(abs_path)
    if current_hash != record.get("sha256"):
        return False, f"Порушення цілісності: хеш на диску ({current_hash[:16]}...) не збігається із зареєстрованим ШІ ({record.get('sha256', '')[:16]}...)"

    # Авто-реплікація в /tmp якщо там запису ще не було
    if not os.path.exists(LEDGER_PATH):
        try:
            save_ledger(ledger)
        except Exception:
            pass

    return True, f"OK (Model: {record.get('model')})"

def verify_content_sha256(sha256_hash: str) -> tuple[bool, str, dict]:
    """Пошук відповідності контенту за SHA256 хешем у сесійному/персистентному реєстрі."""
    if not sha256_hash:
        return False, "Порожній хеш для перевірки.", {}

    ledger = load_ledger()
    for path, entry in ledger.items():
        if entry.get("sha256") == sha256_hash:
            return True, f"OK (Model: {entry.get('model')}, Path: {path})", entry

    return False, f"Хеш {sha256_hash[:16]}... не знайдено в реєстрі провененсу ШІ.", {}

def run_verified_script(script_path: str, script_args: list) -> int:
    """Безпечне виконання скрипта суворо за умови проходження перевірки провененсу."""
    abs_path = os.path.abspath(script_path)
    is_valid, reason = verify_provenance(abs_path)

    if not is_valid:
        print(f"\n🛑 HARD GATE VIOLATION (Anti-Shadow Gate v0.8.2 / v0.9.1):", file=sys.stderr)
        print(f"   {reason}", file=sys.stderr)
        print("   Ручне створення скриптів через write_to_file в обхід моделей ШІ категорично заборонено.", file=sys.stderr)
        print("   Використовуйте канонічний синтез:", file=sys.stderr)
        print(f"   python3 .agents/scripts/diagnostic_runner.py --synthesize-script \"<завдання>\" --out {script_path}\n", file=sys.stderr)
        return 126

    print(f"\n🚀 Запуск валідованого скрипта ({reason}): {os.path.basename(abs_path)}")
    print("=" * 60)
    cmd = [sys.executable, abs_path] + script_args
    start_time = time.time()
    try:
        res = subprocess.run(cmd)
        elapsed = round(time.time() - start_time, 3)
        print(f"\n⏱️ Час виконання: {elapsed} с. Код виходу: {res.returncode}")
        return res.returncode
    except Exception as e:
        print(f"❌ Помилка виконання: {e}", file=sys.stderr)
        return 1

def verify_commit_attribution(commit_msg: str) -> tuple[bool, str]:
    """Перевірка атрибуції ШІ-моделі у повідомленні коміту на основі реєстру провененсу (v0.9.1 / v0.9.7)."""
    import re
    # 1. Перевірка audited: copilot-cli (Policy v0.9.7 / v0.9.8)
    audit_match = re.search(r"audited:\s*([a-zA-Z0-9_\-.:]+)", commit_msg, re.IGNORECASE)
    if audit_match:
        auditor = audit_match.group(1).strip().lower()
        if "copilot" in auditor:
            copilot_flag = "/tmp/antigravity_copilot_executed.flag"
            if not os.path.exists(copilot_flag):
                return False, f"Фальсифікація аудиту: задекларовано '[audited: {auditor}]', але виконання Copilot CLI не зафіксовано в сесії (відсутній прапорець виконання copilot_executed.flag)."

    # 2. Перевірка generated: <model>
    match = re.search(r"generated:\s*([a-zA-Z0-9_\-.:]+)", commit_msg, re.IGNORECASE)
    if not match:
        return True, "Атрибуція ШІ відсутня в коміті (ручний або структурний коміт)."

    model_claimed = match.group(1).strip().lower()
    if not model_claimed:
        return False, "Фальсифікація авторства: назва моделі у [generated: ...] порожня."

    ledger = load_ledger()
    if not ledger:
        return False, f"Реєстр провененсу порожній: генерацію моделлю '{model_claimed}' не підтверджено."

    matched_entries = []
    for path, entry in ledger.items():
        entry_model = entry.get("model", "").strip().lower()
        if entry_model and (model_claimed == entry_model or entry_model in model_claimed or model_claimed in entry_model):
            matched_entries.append(path)

    if not matched_entries:
        return False, (
            f"Фальсифікація авторства коміту: задекларовано '[generated: {model_claimed}]', "
            f"але в реєстрі провененсу немає жодного файлу, згенерованого цією моделлю."
        )

    return True, f"OK (Знайдено {len(matched_entries)} зареєстрованих файлів для моделі {model_claimed})"

def main():
    parser = argparse.ArgumentParser(description="Phase 4 Provenance Ledger & Anti-Shadow Gate (Policy v0.9.1)")
    parser.add_argument("--register", type=str, help="Зареєструвати ШІ-скрипт у сесійному реєстрі")
    parser.add_argument("--model", type=str, default="qwen2.5-coder:1.5b", help="Модель, яка згенерувала код")
    parser.add_argument("--hash", type=str, default=None, help="SHA256 хеш для прямої реєстрації")
    parser.add_argument("--prompt", type=str, default=None, help="Промпт задачі, переданий моделі")
    parser.add_argument("--eval-count", type=int, default=None, help="Кількість згенерованих токенів")
    parser.add_argument("--duration-ms", type=float, default=None, help="Тривалість оцінки промпту у мс")
    parser.add_argument("--verify", type=str, help="Перевірити валідність провененсу файлу")
    parser.add_argument("--verify-hash", type=str, help="Перевірити валідність SHA256 хешу")
    parser.add_argument("--verify-commit", type=str, help="Перевірити валідність атрибуції моделі в повідомленні коміту")
    parser.add_argument("--run", type=str, help="Запустити валідований скрипт")
    parser.add_argument("script_args", nargs="*", help="Аргументи для скрипта")

    args = parser.parse_args()

    if args.register:
        success = register_provenance(
            args.register,
            model=args.model,
            sha256_hash=args.hash,
            source_prompt=args.prompt,
            eval_count=args.eval_count,
            prompt_eval_duration_ms=args.duration_ms
        )
        return 0 if success else 1
    elif args.verify:
        valid, msg = verify_provenance(args.verify)
        print(f"Верифікація: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.verify_hash:
        valid, msg, entry = verify_content_sha256(args.verify_hash)
        print(f"Верифікація хешу: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.verify_commit:
        valid, msg = verify_commit_attribution(args.verify_commit)
        print(f"Верифікація коміту: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.run:
        return run_verified_script(args.run, args.script_args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

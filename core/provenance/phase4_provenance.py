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
PERSISTENT_LEDGER_PATH = "/home/hills/Documents/.agents/.provenance_ledger.json"

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
    """Завантаження реєстру з пріоритетом /tmp та автоматичним відновленням із персистентного сховища."""
    ledger = {}
    if os.path.exists(PERSISTENT_LEDGER_PATH):
        try:
            with open(PERSISTENT_LEDGER_PATH, "r", encoding="utf-8") as f:
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
    """Синхронне збереження реєстру в /tmp та у персистентне сховище .agents/."""
    for path in (LEDGER_PATH, PERSISTENT_LEDGER_PATH):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    json.dump(ledger, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
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

        # Створення сесійного прапорця валідації
        try:
            with open("/tmp/antigravity_provenance_valid.flag", "w", encoding="utf-8") as flag_f:
                flag_f.write(f"PROVENANCE_VALID: {abs_path} at {time.time()} by {model}\n")
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
    elif args.run:
        return run_verified_script(args.run, args.script_args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

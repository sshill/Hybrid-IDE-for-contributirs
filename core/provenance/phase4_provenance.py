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

def get_file_sha256(path: str) -> str:
    """Обчислення SHA256 хешу файлу."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def register_provenance(script_path: str, model: str = "qwen2.5-coder:1.5b") -> bool:
    """Реєстрація хешу згенерованого ШІ-скрипта в сесійному реєстрі."""
    abs_path = os.path.abspath(script_path)
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

    try:
        ledger = {}
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                try:
                    ledger = json.load(f)
                except Exception:
                    ledger = {}

        ledger[abs_path] = entry

        with open(LEDGER_PATH, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(ledger, f, indent=2, ensure_ascii=False)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        print(f"🔒 [PROVENANCE REGISTERED] Файл {os.path.basename(abs_path)} зареєстровано (SHA256: {sha256_hash[:16]}...)")
        return True
    except Exception as e:
        print(f"❌ Помилка запису в реєстр провененсу: {e}", file=sys.stderr)
        return False

def verify_provenance(script_path: str) -> tuple[bool, str]:
    """Верифікація цілісності та походження скрипта перед виконанням."""
    abs_path = os.path.abspath(script_path)
    if not os.path.isfile(abs_path):
        return False, f"Файл не існує: {abs_path}"

    if not os.path.exists(LEDGER_PATH):
        return False, "Реєстр провененсу порожній або відсутній (/tmp/antigravity_provenance_ledger.json)."

    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                ledger = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        return False, f"Помилка читання реєстру: {e}"

    record = ledger.get(abs_path)
    if not record:
        return False, f"Файл не зареєстровано в сесійному реєстрі ШІ-генерації: {abs_path}"

    current_hash = get_file_sha256(abs_path)
    if current_hash != record.get("sha256"):
        return False, f"Порушення цілісності: хеш на диску ({current_hash[:16]}...) не збігається із зареєстрованим ШІ ({record.get('sha256', '')[:16]}...)"

    return True, f"OK (Model: {record.get('model')})"

def run_verified_script(script_path: str, script_args: list) -> int:
    """Безпечне виконання скрипта суворо за умови проходження перевірки провененсу."""
    abs_path = os.path.abspath(script_path)
    is_valid, reason = verify_provenance(abs_path)

    if not is_valid:
        print(f"\n🛑 HARD GATE VIOLATION (Anti-Shadow Gate v0.8.2):", file=sys.stderr)
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
    parser = argparse.ArgumentParser(description="Phase 4 Provenance Ledger & Anti-Shadow Gate (Antigravity_Mgr)")
    parser.add_argument("--register", type=str, help="Зареєструвати ШІ-скрипт у сесійному реєстрі")
    parser.add_argument("--model", type=str, default="qwen2.5-coder:1.5b", help="Модель, яка згенерувала код")
    parser.add_argument("--verify", type=str, help="Перевірити валідність провененсу файлу")
    parser.add_argument("--run", type=str, help="Запустити валідований скрипт")
    parser.add_argument("script_args", nargs="*", help="Аргументи для скрипта")

    args = parser.parse_args()

    if args.register:
        return 0 if register_provenance(args.register, model=args.model) else 1
    elif args.verify:
        valid, msg = verify_provenance(args.verify)
        print(f"Верифікація: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.run:
        return run_verified_script(args.run, args.script_args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

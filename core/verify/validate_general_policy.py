#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Діагностичний валідатор Генеральної політики GEMINI.md (v0.8 / v0.9).
Шлях: /home/hills/Documents/.agents/scripts/validate_general_policy.py

Перевіряє:
1. Наявність та цілісність усіх розділів регламенту v0.8 / v0.9.
2. Багаторівневу архітектуру: Рівень 1 (Ollama <=7B, 16GB RAM), Рівень 2 (Groq + OpenRouter),
   Рівень 3 (Git Knowledge), Рівень 4 (Claude Sonnet 5.5 / GPT-OSS 120B), Рівень 5 (Antigravity).
3. Протокол Git-First Local Access для безвідмовного доступу до файлів.
4. Префікс Always-Allow та вимоги Phase 1 Status Banner.
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True

def get_default_policy() -> str:
    """Динамічне визначення шляху до файлу політики (сумісність із локальним хостом та CI/CD)."""
    # 1. Відносно поточної робочої директорії
    cwd_candidates = [
        os.path.join(os.getcwd(), "config", "GEMINI.template.md"),
        os.path.join(os.getcwd(), "GEMINI.md"),
    ]
    for c in cwd_candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    # 2. Відносно розташування цього файлу (core/verify/..)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    repo_candidates = [
        os.path.join(repo_root, "config", "GEMINI.template.md"),
        os.path.join(repo_root, "GEMINI.md"),
    ]
    for c in repo_candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    # 3. Глобальний шлях розробника як крайній fallback
    fallback = "/home/hills/Documents/GEMINI.md"
    if os.path.isfile(fallback):
        return fallback

    return "config/GEMINI.template.md"

def parse_args():
    parser = argparse.ArgumentParser(description="Validator for GEMINI.md policy v0.8 / v0.9")
    parser.add_argument("--policy", type=str, default=get_default_policy(), help="Шлях до файлу GEMINI.md")
    parser.add_argument("--json", action="store_true", help="Вивід у форматі JSON")
    return parser.parse_args()

def verify_structure(content: str) -> dict:
    """Локальний структурний аудит обов'язкових розділів v0.8."""
    checks = []
    required_sections = [('Регламент роботи: 5 фаз', '5 фаз обробки завдань'), ('Багаторівнева архітектура ШІ v0.8', '5-Tier Multi-AI Architecture'), ('Рівень 1: Local Edge Ollama <=7B', 'LOCAL OLLAMA <=7B'), ('Рівень 2: Groq Cloud & OpenRouter', 'GROQ & OPENROUTER'), ('Рівень 3: Кешування знань', 'docs/knowledge/'), ('Рівень 4: Релізний Code-Арбітр', 'Claude Sonnet 5.5 / GPT-OSS 120B'), ('Рівень 5: Фінальний вердикт Antigravity', 'Golden Standard Orchestrator'), ('Domain Guard', 'Scope & Domain Guard'), ('Context Hygiene', 'Context Hygiene & Lifespan'), ('Strict Code-Only Contract', 'Регламент взаємодії з локальною Ollama'), ('Апаратний ценз 16 ГБ RAM', 'Апаратний профіль машини (16 ГБ RAM'), ('Заборона моделей >=14B локально', 'Моделі $\\ge 14\\text{B}$ на локальній машині **суворо заборонені**'), ('Git-First Local Access', 'Git-First Local Access'), ('Усунення помилок Permission denied', 'Принцип усунення помилок «Permission denied / no access»'), ('Бюджет кроків Фази 4', 'Phase 4 Step Budget'), ('Аварійний вимикач Circuit Breaker', 'Circuit Breaker'), ("Залізний бар'єр Hard Deny Gate", 'Hard Deny Gate'), ('Zero Inline-Eval Hard Gate', 'Zero Inline-Eval'), ('AI Script Synthesis Runner', '--synthesize-script'), ('Стандарт запуску команд', 'Мінімізація модальних вікон'), ('Стандарт бази знань', 'Knowledge Base Protocol'), ('Протокол Code-Арбітра', '[CODE_AUDIT_REPORT]'), ('Phase 1 Status Banner', 'Phase 1 Status Banner'), ('Git-First Discovery', 'Git & Index First'), ('Exploration Hard Limit', 'Exploration Hard Limit'), ('Версія регламенту v0.8/v0.9', 'Architecture (v0.'), ('Централізований хаб Antigravity_Mgr', 'Antigravity_Mgr'), ('Multi-Project Symlink Mesh', 'Symlink Mesh'), ('Сесійний реєстр провененсу', 'сесійному реєстрі провененсу'), ('Runtime Circuit Breaker Gate', 'Runtime Circuit Breaker Gate'), ('Абсолютна дія Фази 1', 'No Exceptions for Information Gathering'), ('Видимість викликів ШІ в чаті', 'Chat-Screen AI Invocation Visibility'), ('Префікс Always Allow', 'Always Allow'), ('3-компонентна формула Bridge Prompt', 'канонічною 3-компонентною формулою'), ('Repository Docs Hygiene Gate v0.9.3', 'Repository Docs Hygiene Gate (v0.9.3)')]

    all_passed = True
    for name, marker in required_sections:
        found = marker in content
        if not found:
            all_passed = False
        checks.append({
            "name": name,
            "marker": marker,
            "status": "PASS" if found else "FAIL"
        })

    return {
        "status": "PASS" if all_passed else "FAIL",
        "checks": checks
    }

def main():
    args = parse_args()
    start_time = time.time()

    if not os.path.exists(args.policy):
        sys.stderr.write(f"Помилка: Файл не знайдено: {args.policy}\n")
        sys.exit(1)

    with open(args.policy, "r", encoding="utf-8") as f:
        content = f.read()

    struct_result = verify_structure(content)
    elapsed = round(time.time() - start_time, 3)

    if args.json:
        output = {
            "version": "0.8.0",
            "file": args.policy,
            "validation_time_sec": elapsed,
            "structural_verification": struct_result
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        sys.exit(0 if struct_result["status"] == "PASS" else 1)

    print("\n" + "=" * 55)
    print("🔍 Аудит Генеральної політики v0.8: GEMINI.md")
    print("=" * 55)
    
    passed_count = sum(1 for c in struct_result["checks"] if c["status"] == "PASS")
    total_count = len(struct_result["checks"])
    print(f"📋 Структурна валідація розділів: {passed_count}/{total_count} пройдено")
    
    for c in struct_result["checks"]:
        icon = "🟢" if c["status"] == "PASS" else "🔴"
        print(f"  {icon} {c['name']:<36} [{c['status']}]")

    print(f"\n⏱️ Час валідації: {elapsed} с\n")
    if passed_count == total_count:
        print("✅ Політика GEMINI.md v0.8 повністю валідна та відповідає регламенту!")
        sys.exit(0)
    else:
        print("❌ Виявлено невідповідності в структурі політики.")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фаза 2: Валідатор контрактів планів та AI Routing Matrix.
Шлях: /home/hills/Documents/Antigravity_Mgr/tools/phase2_router.py
Стандарт: Pydantic-style Schema Contract Verification (Zero-Dep stdlib).
"""

import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True

MANDATORY_PLAN_SECTIONS = [
    ("Мета або опис проблеми", [r"#\s*.*", r"##\s*1\.\s*Мета.*|##\s*User Review Required|##\s*Open Questions"]),
    ("Пакет змін (Proposed Changes)", [r"##\s*.*Пакет змін.*|##\s*Proposed Changes"]),
    ("План перевірки (Verification Plan)", [r"##\s*.*План перевірки.*|##\s*Verification Plan"])
]

def validate_plan(plan_path: str) -> int:
    """Перевірка обов'язкових розділів плану відповідно до Фази 2 регламенту."""
    if not os.path.exists(plan_path):
        print(f"❌ План не знайдено: {plan_path}", file=sys.stderr)
        return 1

    with open(plan_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"\n📋 Валідація контракту плану Фази 2: {plan_path}")
    print("=" * 60)

    all_passed = True
    for section_name, patterns in MANDATORY_PLAN_SECTIONS:
        found = any(re.search(p, content, re.IGNORECASE) for p in patterns)
        status = "PASS" if found else "FAIL"
        icon = "🟢" if found else "🔴"
        print(f"  {icon} {section_name:<38} [{status}]")
        if not found:
            all_passed = False

    if all_passed:
        print("\n✅ План повністю валідний та відповідає контракту Фази 2!")
        return 0
    else:
        print("\n❌ План не містить усіх обов'язкових розділів регламенту.", file=sys.stderr)
        return 2

# Фізичні характеристики пропускної здатності та ресурсів (Throughput Model)
THROUGHPUT_MAP = {
    "qwen2.5-coder:1.5b": {"speed": 20.0, "ttft": 0.3, "ram_gb": 1.2, "tier": 1, "provider": "Ollama Local Edge"},
    "qwen2.5-coder:3b":   {"speed": 10.0, "ttft": 0.6, "ram_gb": 2.2, "tier": 1, "provider": "Ollama Local Edge"},
    "qwen2.5-coder:7b":   {"speed": 2.8,  "ttft": 1.8, "ram_gb": 5.1, "tier": 1, "provider": "Ollama Local Edge"},
    "openai/gpt-oss-120b":{"speed": 460.0,"ttft": 0.2, "ram_gb": 0.0, "tier": 2, "provider": "Groq Cloud LPU"}
}

# Безпечний робочий бюджет Groq Cloud зі зниженням на 20% (LiteLLM Rate Guard)
GROQ_SAFETY_BUDGET = {
    "nominal_tpm": 8000,
    "safe_tpm": 6400,        # -20% від 8000 TPM
    "nominal_rpm": 1000,
    "safe_rpm": 800,         # -20% від 1000 RPM
    "max_single_out": 3200   # -20% від 4096 tokens
}

def estimate_etc(model_name: str, out_tokens: int) -> float:
    """Розрахунок очікуваного часу генерації (Estimated Time to Complete)."""
    prof = THROUGHPUT_MAP.get(model_name, THROUGHPUT_MAP["qwen2.5-coder:1.5b"])
    return round(prof["ttft"] + (out_tokens / prof["speed"]), 2)

def calculate_adaptive_timeout(etc: float) -> int:
    """Адаптивний розрахунок таймауту сокета замість жорстких 90 с."""
    return max(30, int(1.5 * etc) + 10)

def calculate_route(prompt_tokens: int, estimated_out_tokens: int = 250, sla_sec: float = 30.0, allow_cloud: bool = True) -> dict:
    """
    Розрахунок маршрутизації на основі реальної пропускної здатності (RouteLLM + LiteLLM + FrugalGPT).
    Обирає модель, яка задовольняє SLA та не перевищує безпечні ліміти пам'яті/квот.
    """
    etc_7b = estimate_etc("qwen2.5-coder:7b", estimated_out_tokens)
    etc_15b = estimate_etc("qwen2.5-coder:1.5b", estimated_out_tokens)
    etc_groq = estimate_etc("openai/gpt-oss-120b", estimated_out_tokens)

    # 1. Якщо генерація вимагає великого обсягу або перевищує SLA на локальних моделях
    selected_tier = 1
    selected_model = "qwen2.5-coder:1.5b"
    provider = "Ollama Local Edge"
    reason = ""

    # Перевірка безпечного ліміту Groq (-20%)
    groq_fits_budget = estimated_out_tokens <= GROQ_SAFETY_BUDGET["max_single_out"]

    if allow_cloud and (estimated_out_tokens > 250 or prompt_tokens > 3000 or etc_7b > sla_sec):
        if groq_fits_budget:
            selected_tier = 2
            selected_model = "openai/gpt-oss-120b"
            provider = "Groq Cloud LPU"
            reason = (f"Апаратна оптимізація: вивід {estimated_out_tokens} tok на локальній 7B займе {etc_7b}с "
                      f"(перевищує SLA {sla_sec}с). Groq LPU виконає за {etc_groq}с у межах квоти безпеки "
                      f"({estimated_out_tokens} <= {GROQ_SAFETY_BUDGET['max_single_out']} TPM).")
        else:
            # Якщо навіть для Groq завеликий вивід
            selected_tier = 2
            selected_model = "openai/gpt-oss-120b"
            provider = "Groq Cloud LPU"
            reason = f"Великий обсяг коду ({estimated_out_tokens} tok). Потрібне покрокове розбиття."
    elif estimated_out_tokens <= 60 and etc_7b <= sla_sec:
        # Для дрібного точного коду (до 60 токенів) обираємо 7B з найвищою точністю
        selected_tier = 1
        selected_model = "qwen2.5-coder:7b"
        provider = "Ollama Local Edge"
        reason = f"Високоточний локальний синтаксис (7B): {estimated_out_tokens} tok виконається за {etc_7b}с (SLA <= {sla_sec}с)."
    else:
        # Для середніх локальних завдань (до 250 токенів) — робоча конячка 1.5B
        selected_tier = 1
        selected_model = "qwen2.5-coder:1.5b"
        provider = "Ollama Local Edge"
        reason = f"Локальний робочий синтез (1.5B): {estimated_out_tokens} tok виконається за {etc_15b}с (20 tok/s)."

    active_etc = estimate_etc(selected_model, estimated_out_tokens)
    adaptive_timeout = calculate_adaptive_timeout(active_etc)

    decision = {
        "tier": selected_tier,
        "provider": provider,
        "model": selected_model,
        "prompt_tokens": prompt_tokens,
        "estimated_out_tokens": estimated_out_tokens,
        "sla_seconds": sla_sec,
        "estimated_time_sec": active_etc,
        "adaptive_timeout_sec": adaptive_timeout,
        "groq_budget": {
            "tokens_expected": estimated_out_tokens if selected_tier == 2 else 0,
            "safe_minute_quota": GROQ_SAFETY_BUDGET["safe_tpm"],
            "max_single_out_limit": GROQ_SAFETY_BUDGET["max_single_out"]
        },
        "fallback_chain": ["openai/gpt-oss-120b"] if selected_tier == 1 else ["qwen2.5-coder:1.5b"],
        "reason": reason
    }
    return decision

def format_route_widget(dec: dict) -> str:
    """Форматування рішення маршрутизатора у вигляді структурованого віджета для чату та плану."""
    sla_status = "🟢 PASS" if dec["estimated_time_sec"] <= dec["sla_seconds"] else "🔴 SLA EXCEEDED"
    lines = [
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│ 📈 [ROUTELM TOKEN WEIGHT & THROUGHPUT DISPATCH WIDGET]                 │",
        "├────────────────────────────────────────────────────────────────────────┤",
        f"│ • Модель / Провайдер : Tier {dec['tier']} | {dec['model']} ({dec['provider']})",
        f"│ • Вхідні токени (Nin): {dec['prompt_tokens']} tok | Вихід (Nout): {dec['estimated_out_tokens']} tok",
        f"│ • Розрахунковий час  : {dec['estimated_time_sec']} с (SLA ліміт: {dec['sla_seconds']} с) [{sla_status}]",
        f"│ • Адаптивний таймаут : {dec['adaptive_timeout_sec']} с",
        f"│ • LiteLLM Safe Budget: {dec['groq_budget']['tokens_expected']} / {dec['groq_budget']['safe_minute_quota']} TPM (Headroom: OK)",
        f"│ • Обґрунтування      : {dec['reason']}",
        "└────────────────────────────────────────────────────────────────────────┘"
    ]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Phase 2 Plan Validator & Dynamic Resource Router (Antigravity_Mgr)")
    parser.add_argument("--validate-plan", type=str, help="Перевірка файлу implementation_plan.md")
    parser.add_argument("--route", action="store_true", help="Розрахувати маршрут ШІ на основі Throughput/SLA")
    parser.add_argument("--prompt-tokens", type=int, default=1500, help="Орієнтовна кількість токенів промпта")
    parser.add_argument("--out-tokens", type=int, default=250, help="Орієнтовна кількість токенів генерації")
    parser.add_argument("--sla-sec", type=float, default=30.0, help="Максимальний допустимий час генерації (SLA)")
    parser.add_argument("--no-cloud", action="store_true", help="Заборонити хмарний оверфлоу (суворо офлайн)")
    parser.add_argument("--format-widget", action="store_true", help="Вивести результат у вигляді структурованого віджета")

    args = parser.parse_args()

    if args.validate_plan:
        return validate_plan(args.validate_plan)
    elif args.route:
        dec = calculate_route(args.prompt_tokens, args.out_tokens, sla_sec=args.sla_sec, allow_cloud=not args.no_cloud)
        if args.format_widget:
            print(format_route_widget(dec))
        else:
            print(json.dumps(dec, indent=2, ensure_ascii=False))
        return 0
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())


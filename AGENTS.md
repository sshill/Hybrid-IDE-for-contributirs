# AGENTS.md — Hybrid IDE Core & Contributor Overlay

Доповнює глобальне ядро Hybrid-IDE (`rules/AGENTS.md`). Фази, ШІ-матриця та системні заборони ядра діють автоматично і тут не повторюються.

## Проєкт та призначення
- **Призначення:** Відкрите ядро Hybrid-IDE, інструменти Antigravity_Mgr та регламентна документація.
- **Мови:** Python 3.13 (stdlib only, zero third-party deps), POSIX Bash.
- **Точки входу:** `.agents/scripts/diagnostic_runner.py`, `.agents/scripts/validate_general_policy.py`, `Antigravity_Mgr/tools/`.

## Правила коду
- **Zero-Dep:** Жодних сторонніх бібліотек; суворо stdlib (`sys`, `os`, `json`, `fcntl`, `hashlib`, `urllib`).
- **Bytecode:** `sys.dont_write_bytecode = True` у всіх Python-файлах.
- **Bash:** `set -euo pipefail` та коментарі опису на початку кожного скрипта.

## Верифікація (Фаза 5)
- **Валідація політики:** `python3 .agents/scripts/validate_general_policy.py` (37/37 PASS).
- **Синтаксис:** `python3 -m py_compile <шлях_до_файлу.py>` на змінених Python-файлах.

## Стиль комітів
- `<type>(<scope>): <опис> [generated: <model> | verified: antigravity]`

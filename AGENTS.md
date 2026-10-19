# AGENTS.md — Hybrid IDE Core & Contributor Overlay (v0.9.7)

Доповнює глобальне ядро Hybrid-IDE (`~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`). Загальні 5 фаз та OS Hard Gates діють автоматично.

## 1. Проєкт та кодова база
- **Призначення:** Відкрита кодова база фреймворку Hybrid-IDE, інструменти Antigravity та регламент.
- **Мови:** Python 3.10–3.13 (суворо stdlib only, zero-dep), POSIX Bash.
- **Архітектура модулів:**
  * `core/engine/diagnostic_runner.py` — діагностичний інференс ШІ (Tier 1 Ollama, Tier 2 Groq, Tier 4.5 Copilot CLI, Semantic Constraint Checker & Pre-Audit Gate).
  * `core/router/phase2_router.py` — маршрутизація моделей (Throughput Model v0.9.7) та бюджет токенів.
  * `core/provenance/phase4_provenance.py` — подвійний SLSA-реєстр цілісності коду та валідація атрибуції `[audited: copilot-cli]`.
  * `core/verify/phase5_verify.py` — детерміністична локальна Фаза 5 (AST + політика).
  * `core/verify/verify_remote_ci.py` — опитування GitHub Actions CI.

## 2. Матриця арбітражу та розробки (Tier 4 vs Tier 4.5)
- **Повсякденна розробка:** Генерація коду — Tier 1 (Ollama) / Tier 2 (Groq); локальний аудит процедур — Tier 4 (Claude Sonnet).
- **Pre-Release E2E Arbiter Gate:** Перед релізом версії регламенту весь пакет коду інструментів `core/*`, скілів та зв'язка з оточенням Antigravity проходять обов'язковий e2e-аудит / рефакторинг через **Tier 4.5: GitHub Copilot CLI** (`diagnostic_runner.py --copilot-audit` або `--copilot-refactor`).
- **Approval Gate на Copilot:** Будь-який інференс-виклик `copilot -p` вимагає обов'язкового окремого підтвердження користувача в чаті (`+`), яке створює тимчасовий прапорець авторизації `/tmp/antigravity_copilot_authorized.flag`. Діагностичний зонд версії `copilot --version` (0 кредитів) дозволений при старті сесії за протоколом Host-First.

## 3. Правила коду та гігієни
- **Zero-Dep:** Жодних сторонніх PyPI бібліотек.
- **Bytecode:** Обов'язково `sys.dont_write_bytecode = True` у всіх `.py`.
- **Bash:** `set -euo pipefail` та коментарі на початку скрипта.

## 4. Верифікація та реліз (Фаза 5)
- **Локальна:** `python3 core/verify/phase5_verify.py` (37/37 перевірок).
- **Синтаксис:** `python3 -m py_compile <шлях_до_файлу.py>`.
- **CI перевірка:** `python3 core/verify/verify_remote_ci.py`.
- **Публікація:** `./push_to_github.sh` (суворо після команди `++`).

## 5. Стиль комітів
- `<type>(<scope>): <опис> [generated: <model> | verified: antigravity]`
- Передрелізний аудит: `chore(release): ... [audited: copilot-cli | verified: antigravity]`


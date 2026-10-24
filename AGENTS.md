# AGENTS.md — Hybrid IDE Core & Contributor Overlay (v0.9.9)

Доповнює глобальне ядро Hybrid-IDE (`~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`). Загальні 5 фаз та OS Hard Gates діють автоматично.

## 1. Проєкт та кодова база
- **Призначення:** Відкрита кодова база фреймворку Hybrid-IDE, інструменти Antigravity та регламент.
- **Мови:** Python 3.10–3.13 (суворо stdlib only, zero-dep), POSIX Bash.
- **Архітектура модулів:**
  * `core/engine/diagnostic_runner.py` — діагностичний інференс ШІ: Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet (`--sonnet-query`, `--sonnet-audit`, `--sonnet-precheck`), Tier 4.5 Copilot CLI, Semantic Constraint Checker & Pre-Audit Gate.
  * `core/hooks/pre_invocation_hook.py` (.sh) — PreInvocation Lifecycle Hook: авто-старт нових чатів (`invocationNum == 1`), ініціалізація Brain-First телеметрії та ін'єкція ephemeral-настанов регламенту.
  * `core/hooks/pre_tool_hook.py` — OS Hard Gates: Zero Inline-Eval, Brain-First Session State Isolation, Strict Hash Integrity Gate, Script Provenance Gate та Dynamic Plan-Aware Step Budget.
  * `core/provenance/phase4_provenance.py` — Brain-First SLSA-реєстр цілісності коду (`<brain>/.system_generated/`), Anti-Forgery Gate, атомарне збереження леджера та валідація атрибуцій `[audited: copilot-cli]`, `[verified: claude]`.
  * `core/router/phase2_router.py` — маршрутизація моделей (Throughput Model) та бюджет токенів.
  * `core/inspect/phase1_inspect.py` — 2D-телеметрія контексту та AST-інспектор.
  * `core/verify/phase5_verify.py` — детерміністична локальна Фаза 5 (AST + політика 37/37).
  * `core/verify/verify_remote_ci.py` — опитування GitHub Actions CI.

## 2. Реструктуризований конвеєр обробки завдань (v0.9.9)
1. **Фаза 1: Діагностика** — лише читання (`git status -sb`, `git ls-files`, `view_file`). Авто-ініціалізація телеметрії через PreInvocation або вимір `phase1_inspect.py --telemetry`.
2. **Фаза 2: Репорт та план** — формування `implementation_plan.md` з повним переліком змін та AI Routing Matrix.
3. **Фаза 2.5: Pre-Approval Gate (Tier 4 Claude Sonnet)** — поглиблений аудит плану на відповідність регламенту та відсутність прогалин (`diagnostic_runner.py --sonnet-audit implementation_plan.md`) перед поданням користувачеві.
4. **Фаза 3: Схвалення користувача** — обов'язкова зупинка (`+` — санкція на Фазу 4, `+!` — Attention Gate, `++` — санкція на реліз у Фазі 5).
5. **Фаза 4.1: Pre-Execution Context Assembly & Pre-Check** — збірка всієї інформації за планом та пре-чек на Claude Sonnet (`diagnostic_runner.py --sonnet-precheck implementation_plan.md`) перед мутацією коду.
6. **Фаза 4.3: Синтез коду** — генерація коду моделями ШІ (Tier 1 Ollama / Tier 2 Groq) за принципом «запит-перевірка синтаксису (AST)» та обов'язкова реєстрація у Brain-First реєстрі провененсу.
7. **Фаза 4.5: Pre-Release E2E Arbiter (Tier 4.5 Copilot CLI)** — повний аудит модифікованого пакета через GitHub Copilot CLI (`diagnostic_runner.py --copilot-audit` або `--copilot-refactor`).
8. **Фаза 5.1: Dual-Audit Report & Verification** — фінальний звіт `walkthrough.md` із протоколом 2 аудитів (Claude Sonnet + Copilot CLI), складом пакета та детерміністичними тестами `phase5_verify.py` (37/37 перевірок).

## 3. Правила коду та гігієни
- **Zero-Dep:** Жодних сторонніх PyPI бібліотек.
- **Bytecode:** Обов'язково `sys.dont_write_bytecode = True` у всіх `.py`.
- **Bash:** `set -euo pipefail` та коментарі на початку скрипта.
- **Brain-First Storage:** Усі сесійні файли (кроки, контракти, історія, прапорці, леджер) зберігаються у `<artifactDirectoryPath>/.system_generated/`, що гарантує захист від видалення при перезавантаженні ОС.

## 4. Верифікація та реліз (Фаза 5)
- **Локальна:** `python3 core/verify/phase5_verify.py` (37/37 перевірок).
- **Синтаксис:** `python3 -m py_compile <шлях_до_файлу.py>`.
- **CI перевірка:** `python3 core/verify/verify_remote_ci.py`.
- **Публікація:** `./push_to_github.sh` (суворо після команди `++`).

## 5. Стиль комітів
- `<type>(<scope>): <опис> [generated: <model> | verified: antigravity]`
- Передрелізний аудит: `chore(release): ... [audited: copilot-cli | verified: claude | verified: antigravity]`


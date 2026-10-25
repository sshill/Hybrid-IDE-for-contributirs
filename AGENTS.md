# AGENTS.md — Hybrid IDE Core & Contributor Overlay (v0.9.11)

Доповнює глобальне ядро Hybrid-IDE (`~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`). Загальні 5 фаз та OS Hard Gates діють автоматично.

## 1. Проєкт та кодова база
- **Призначення:** Відкрита кодова база фреймворку Hybrid-IDE, інструменти Antigravity та регламент.
- **Мови:** Python 3.10–3.13 (суворо stdlib only, zero-dep), POSIX Bash.
- **Архітектура модулів:**
  * `core/engine/diagnostic_runner.py` — діагностичний інференс ШІ: Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet (`--sonnet-query`, `--sonnet-audit`, `--sonnet-precheck`), Tier 4.5 Copilot CLI, Semantic Constraint Checker & Pre-Audit Gate, in-process паспортний емітент та 8-token shingle overlap checker.
  * `core/hooks/pre_invocation_hook.py` (.sh) — PreInvocation Lifecycle Hook: авто-старт нових чатів (`invocationNum == 1`), ініціалізація Brain-First телеметрії та ін'єкція ephemeral-настанов регламенту.
  * `core/hooks/pre_tool_hook.py` — OS Hard Gates: Zero Inline-Eval, Ledger Immutability Gate, Secret Isolation Gate, Deny-by-reference Shell State Isolation, Cryptographic Hash Passport Integrity Gate, In-Memory Replacement Simulation (`simulate_replacement`), Contributor Mode (`approved_plan.sha256`) та Dynamic Plan-Aware Step Budget.
  * `core/hooks/post_tool_hook.py` — Circuit Breaker (C4) та підтвердження криптографічних паспортів (`apply_passport` -> `APPLIED`).
  * `core/provenance/phase4_provenance.py` — Brain-First SLSA-реєстр цілісності коду (`<brain>/.system_generated/`), криптографічні HMAC-SHA256 паспорти Schema 1.2 (`MINTED -> RESERVED -> APPLIED / FAILED`), Master HMAC Secret (`~/.gemini/antigravity/.core_master_hmac.secret` mode 0600), атомарні блокування через `locked_ledger()` з `fsync`, єдиний авторизатор `plan_authorizes()`, `--verify-chain` аудит та валідація атрибуцій `[audited: copilot-cli]`, `[verified: claude]`.
  * `core/verify/test_provenance_security.py` — 30 детерміністичних unit-тестів безпеки провененсу, симулятора, міграційного цензора, Ledger Immutability Gate, конкурентності, ізоляції сесій та HMAC-підписів.
  * `core/router/phase2_router.py` — маршрутизація моделей (Throughput Model) та бюджет токенів.
  * `core/inspect/phase1_inspect.py` — 2D-телеметрія контексту та AST-інспектор.
  * `core/verify/phase5_verify.py` — детерміністична локальна Фаза 5 (AST + 30 unit-тестів провененсу + політика 37/37).
  * `core/verify/verify_remote_ci.py` — опитування GitHub Actions CI.

## 2. Реструктуризований конвеєр обробки завдань (v0.9.11)
1. **Фаза 1: Діагностика (Двоканальна)** — лише читання (Канал A: `git status -sb`, `git ls-files`, `view_file`, `phase1_inspect.py`; Канал B: `search_web`, `read_url_content` після Absence Verification). Шлюз якірних специфікацій (Anchored Grounding Gate) та захист від рекурсивного переказу здогадок (Anti-Echo Gate). Авто-ініціалізація телеметрії.
2. **Фаза 2: Репорт та план** — формування `implementation_plan.md` з повним переліком змін та AI Routing Matrix.
3. **Фаза 2.5: Pre-Approval Gate (Tier 4 Claude Sonnet)** — поглиблений аудит плану на відповідність регламенту та відсутність прогалин (`diagnostic_runner.py --sonnet-audit implementation_plan.md`) перед поданням користувачеві.
4. **Фаза 3: Схвалення користувача** — обов'язкова зупинка (`+` — санкція на Фазу 4, `+!` — Attention Gate, `++` — санкція на реліз у Фазі 5). Фіксація `approved_plan.sha256`.
5. **Фаза 4.1: Pre-Execution Context Assembly** — збірка всієї інформації та вихідного коду за планом оркестратором Antigravity (читання через `view_file`, `git -C <dir> status -sb`, zero-shell).
6. **Фаза 4.2: Pre-Check Audit Gate (Tier 4 Claude Sonnet)** — семантичний аудит плану та зібраного контенту (`diagnostic_runner.py --sonnet-precheck implementation_plan.md`) перед мутацією коду (Zero-Shell Constraint).
7. **Фаза 4.3: Синтез коду та випуск паспорта** — генерація коду моделями ШІ (Tier 1 Ollama / Tier 2 Groq з білого списку `GENERATIVE_MODELS_ALLOWLIST`), перевірка шинґлів (Anti-Echo), AST-валідація та випуск активного криптографічного паспорта з HMAC-SHA256 підписом (`mint_passport` -> `MINTED`).
8. **Фаза 4.4: Детерміністичний синтаксичний та компіляційний гейт** — резервування паспорта (`reserve_passport` -> `RESERVED`) через in-memory симуляцію заміни (`simulate_replacement`), верифікація після запису (`apply_passport` -> `APPLIED` з перепідписом), локальна валідація Python AST, `py_compile`. Contributor Mode захищає ядро через `approved_plan.sha256`.
9. **Фаза 4.5: Pre-Release E2E Arbiter (Tier 4.5 Copilot CLI)** — повний аудит модифікованого пакета через GitHub Copilot CLI (`diagnostic_runner.py --copilot-audit`) та верифікація ланцюга HMAC-паспортів (`phase4_provenance.py --verify-chain`).
10. **Фаза 5.1: Dual-Audit Report & Verification** — фінальний звіт `walkthrough.md` із протоколом 2 аудитів (Claude Sonnet + Copilot CLI), складом пакета та детерміністичними тестами `phase5_verify.py` (30/30 unit-тести + 37/37 перевірок).

## 3. Правила коду та гігієни
- **Zero-Dep:** Жодних сторонніх PyPI бібліотек.
- **Bytecode:** Обов'язково `sys.dont_write_bytecode = True` у всіх `.py`.
- **Bash:** `set -euo pipefail` та коментарі на початку скрипта.
- **Brain-First Storage:** Усі сесійні файли (кроки, контракти, історія, прапорці, леджер, паспорти) зберігаються у `<artifactDirectoryPath>/.system_generated/`, що гарантує захист від видалення при перезавантаженні ОС.

## 4. Верифікація та реліз (Фаза 5)
- **Локальна:** `python3 core/verify/phase5_verify.py` (30 unit-тестів + 37/37 перевірок).
- **Синтаксис:** `python3 -m py_compile <шлях_до_файлу.py>`.
- **CI перевірка:** `python3 core/verify/verify_remote_ci.py`.
- **Публікація:** `./push_to_github.sh` (суворо після команди `++`).

## 5. Стиль комітів
- `<type>(<scope>): <опис> [generated: <model> | verified: antigravity]`
- Передрелізний аудит: `chore(release): ... [audited: copilot-cli | verified: claude | verified: antigravity]`


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

## 2. Реструктуризований конвеєр обробки завдань Довіреного Анклаву (v0.9.11)
1. **Фаза 1: Діагностика (Двоканальна)** — лише читання (Канал A: `git status -sb`, `git ls-files`, `view_file`, `enclave_daemon.py --telemetry`; Канал B: `search_web`, `read_url_content` після Absence Verification). Авто-ініціалізація 2D-телеметрії.
2. **Фаза 2: Репорт та план** — формування `implementation_plan.md` з обов'язковим віджетом індикатора контексту (`[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]`) та AI Routing Matrix.
3. **Фаза 2.5: Pre-Approval Gate (Tier 4 Claude Sonnet)** — аудит плану через Анклав (`enclave_daemon.py --query <plan> --tier 4 --mode audit` або Antigravity Pool Attestation Gate `POST /attest`).
4. **Фаза 3: Схвалення користувача** — обов'язкова зупинка (`+` — санкція на Фазу 4, `+!` — Attention Gate, `++` — санкція на реліз у Фазі 5). Фіксація `approved_plan.sha256`.
5. **Фаза 4.1: Pre-Execution Context Assembly** — збірка всієї інформації та вихідного коду за планом оркестратором Antigravity (читання через `view_file`, `git show`, zero-shell).
6. **Фаза 4.2: Pre-Check Audit Gate (Tier 4 Claude Sonnet)** — семантичний аудит плану та контексту через Анклав (`enclave_daemon.py --query <context> --tier 4 --mode precheck`).
7. **Фаза 4.3: Синтез коду та первинний контроль Анклаву** — генерація коду суворо через Анклав на моделі Ollama (`1.5b`, `3b` або `7b`) відповідно до телеметрії Фази 1 (при оверфлоу $>3000$ tok або RAM $<6$ ГБ — автоматичний перехід на Groq `openai/gpt-oss-120b`, `llama-3.3-70b`). Анклав здійснює Anti-Echo ($ \le 0.25$), AST syntax gate, симуляцію заміни, обчислення SHA256 та випуск HMAC-SHA256 паспорта (`MINTED -> RESERVED -> APPLIED`).
8. **Фаза 4.4: Детерміністичний синтаксичний та компіляційний гейт** — резервування паспорта (`reserve_passport` -> `RESERVED`) через in-memory симуляцію заміни (`simulate_replacement`), верифікація після запису (`apply_passport` -> `APPLIED` з перепідписом), локальна валідація Python AST, `py_compile`. Contributor Mode захищає ядро через `approved_plan.sha256`.
9. **Фаза 4.5: Pre-Release E2E Arbiter з Failover Gate** — повний аудит модифікованого пакета через Copilot CLI (`enclave_daemon.py --query <diff> --tier 4.5 --mode audit`). Якщо Copilot недоступний (вичерпано квоту) — автоматичне перенаправлення на верифікацію до Claude Sonnet (Tier 4). Тільки після успішної верифікації публікується репорт Фази 4 з обов'язковою фіксацією SHA-256 та Passport ID від Анклаву.
10. **Фаза 5.1: Dual-Audit Report & Verification** — фінальний звіт `walkthrough.md`, перевірка ланцюга паспортів (`enclave_daemon.py --verify-chain`) та тести `phase5_verify.py` (35 unit-тестів + 37/37 перевірок).

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


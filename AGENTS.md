# AGENTS.md — Hybrid IDE Core & Contributor Overlay (v0.9.13)

Доповнює глобальне ядро Hybrid-IDE (`~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`). Загальні 5 фаз та OS Hard Gates діють автоматично.

## 1. Проєкт та кодова база
- **Призначення:** Відкрита кодова база фреймворку Hybrid-IDE, інструменти Antigravity та регламент.
- **Мови:** Python 3.10–3.13 (суворо stdlib only, zero-dep), POSIX Bash.
- **Архітектура модулів:**
  * `core/enclave/enclave_daemon.py` — Довірений Анклав: єдиний ШІ-шлюз (Ollama, Groq, Claude Sonnet, Copilot CLI), первинний контроль коду, FrugalGPT та Failover.
  * `core/enclave/ENCLAVE_INTERFACE.md` — інструментальний контракт Анклаву для Antigravity.
  * `core/engine/diagnostic_runner.py` — діагностичний інференс ШІ: Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet (`--sonnet-query`, `--sonnet-audit`, `--sonnet-precheck`), Tier 4.5 Copilot CLI, Semantic Constraint Checker & Pre-Audit Gate, in-process паспортний емітент та 8-token shingle overlap checker.
  * `core/hooks/pre_invocation_hook.py` (.sh) — PreInvocation Lifecycle Hook: авто-старт нових чатів (`invocationNum == 1`), ініціалізація Brain-First телеметрії та ін'єкція ephemeral-настанов регламенту.
  * `core/hooks/pre_tool_hook.py` — OS Hard Gates: Zero Inline-Eval, Ledger Immutability Gate, Secret Isolation Gate, Deny-by-reference Shell State Isolation, Cryptographic Hash Passport Integrity Gate, In-Memory Replacement Simulation (`simulate_replacement`), Contributor Mode (`approved_plan.sha256`), Session-isolated Step Budget та Diagnostic Immunity (Kernel v0.9.12).
  * `core/hooks/post_tool_hook.py` — Circuit Breaker (C4) та підтвердження криптографічних паспортів (`apply_passport` -> `APPLIED`).
  * `core/provenance/phase4_provenance.py` — Brain-First SLSA-реєстр цілісності коду (`<brain>/.system_generated/`), криптографічні HMAC-SHA256 паспорти Schema 1.2 (`MINTED -> RESERVED -> APPLIED / FAILED`), Master HMAC Secret (`~/.gemini/antigravity/.core_master_hmac.secret` mode 0600), атомарні блокування через `locked_ledger()` з `fsync`, єдиний авторизатор `plan_authorizes()`, `--verify-chain` аудит та валідація атрибуцій `[audited: copilot-cli]`, `[verified: claude]`.
  * `core/verify/test_provenance_security.py` — 40 детерміністичних unit-тестів безпеки провененсу, симулятора, міграційного цензора, Ledger Immutability Gate, конкурентності, ізоляції сесій та HMAC-підписів.
  * `core/router/phase2_router.py` — маршрутизація моделей (Throughput Model) та бюджет токенів.
  * `core/inspect/phase1_inspect.py` — 2D-телеметрія контексту та AST-інспектор.
  * `core/verify/phase5_verify.py` — детерміністична локальна Фаза 5 (AST + 40 unit-тестів провененсу + 10 unit-тестів аудитора чату + політика 37/37).
  * `core/verify/chat_context_auditor.py` — форензік-аудитор чату (Kernel v0.9.12) та Git State Seal Gate.
  * `core/verify/verify_remote_ci.py` — опитування GitHub Actions CI.

## 2. Реструктуризований конвеєр обробки завдань Довіреного Анклаву (v0.9.13)
1. **Фаза 1: Діагностика (Двоканальна)** — лише читання (Канал A: `git status -sb`, `git ls-files`, `view_file`, `enclave_daemon.py --telemetry`; Канал B: `search_web`, `read_url_content` після Absence Verification). Обов'язковий стартовий статус-банер сесії з виміряним віджетом 2D-телеметрії `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]` у блоці коду `text`.
2. **Фаза 2: Репорт та план** — формування `implementation_plan.md` з обов'язковим віджетом індикатора контексту (`[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]` у блоці коду `text`) та AI Routing Matrix.
3. **Фаза 2.5: Pre-Approval Gate (Tier 4 Claude Sonnet)** — аудит плану через Анклав (`enclave_daemon.py --query <plan> --tier 4 --mode audit` або Antigravity Pool Attestation Gate `POST /attest`).
4. **Фаза 3: Схвалення користувача** — обов'язкова зупинка (`+` — санкція на Фазу 4, `+!` — Attention Gate, `++` — санкція на реліз у Фазі 5). Звіт запиту на схвалення зобов'язаний містити актуальний віджет 2D-телеметрії у блоці коду `text`. Фіксація `approved_plan.sha256`.
5. **Фаза 4.1: Pre-Execution Context Assembly** — збірка всієї інформації та вихідного коду за планом оркестратором Antigravity (читання через `view_file`, `git show`, zero-shell).
6. **Фаза 4.2: Pre-Check Audit Gate (Tier 4 Claude Sonnet)** — семантичний аудит плану та контексту через Анклав (`enclave_daemon.py --query <context> --tier 4 --mode precheck`).
7. **Фаза 4.3: Синтез коду та первинний контроль Анклаву** — генерація коду суворо через Анклав на моделі Ollama (`1.5b`, `3b` або `7b`) відповідно до телеметрії Фази 1 (при оверфлоу $>3000$ tok або RAM $<6$ ГБ — автоматичний перехід на Groq `openai/gpt-oss-120b`, `llama-3.3-70b`). Анклав здійснює Anti-Echo ($ \le 0.25$), AST syntax gate, симуляцію заміни, обчислення SHA256 та випуск HMAC-SHA256 паспорта (`MINTED -> RESERVED -> APPLIED`).
8. **Фаза 4.4: Детерміністичний синтаксичний та компіляційний гейт** — резервування паспорта (`reserve_passport` -> `RESERVED`) через in-memory симуляцію заміни (`simulate_replacement`), верифікація після запису (`apply_passport` -> `APPLIED` з перепідписом), локальна валідація Python AST, `py_compile`. Contributor Mode захищає ядро через `approved_plan.sha256`.
9. **Фаза 4.5: Pre-Release E2E Arbiter з Failover Gate** — повний аудит модифікованого пакета через Copilot CLI (`enclave_daemon.py --query <diff> --tier 4.5 --mode audit`). Якщо Copilot недоступний (вичерпано квоту) — автоматичне перенаправлення на верифікацію до Claude Sonnet (Tier 4). Тільки після успішної верифікації публікується репорт Фази 4 з обов'язковою фіксацією SHA-256 та Passport ID від Анклаву.
10. **Фаза 5.1: Dual-Audit Report & Verification** — перевірка ланцюга паспортів (`enclave_daemon.py --verify-chain`) та тести `phase5_verify.py` (40 unit-тестів + 37/37 перевірок + тести `chat_context_auditor.py`). Фінальний звіт у чаті та шапка `walkthrough.md` зобов'язані містити актуальний віджет 2D-телеметрії у блоці коду `text`.
11. **Фаза 5.2: Git State Seal Gate** — після успішних тестів оркестратор ЗОБОВ'ЯЗАНИЙ АВТОНОМНО виконати `git add <файли>` та `git commit -m "<type>(<scope>): <опис> [verified: antigravity]"`, отримати Commit SHA та внести його у фінальний `walkthrough.md`. Санкція `+` покриває виконання Фази 4 та локальний коміт Фази 5; санкція `++` потрібна виключно для віддаленого пушу (`push_to_github.sh` / `git push`). Заборонено залишати репозиторій у незапечатаному стані.

## 3. Каталог інструментів Довіреного Анклаву та супутніх інтерфейсів (Tool Catalog)
- **Головні інструменти Анклаву (`~/.gemini/config/plugins/hybrid-ide/bin/enclave_daemon.py`, локально `core/enclave/enclave_daemon.py`):**
  * `POST /apply` (`--target <файл> --task <ТЗ> | --direct-code <код>`) — атомарний синтез/патч із первинним контролем.
  * `POST /query` (`--query <промпт>`) — суверенний ШІ-шлюз із підтримкою FrugalGPT та Failover.
  * `GET /battle-test` (`--battle-test`) — пакетний тест 4 рівнів ШІ (Ollama, Groq, Claude, Copilot probe).
  * `GET /telemetry` (`--telemetry`) — 2D-телеметрія (кроки, Nin/Nout, вільна RAM, зона контексту).
  * `GET /help` (`--help-tools`) — інструментальна схема викликів.
  * `GET /verify-chain` (`--verify-chain`) — перевірка ланцюга паспортів леджера.
  * `POST /attest` (`--attest-arbiter [VERDICT]`) — вердикт арбітра Antigravity Pool.
- **Супутні та інтеграційні інтерфейси:**
  * **LinkedIn Developer API:** OAuth 2.0 у `~/.env` (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`) для інтеграцій.
  * **Email & SMTP нотифікації:** модулі відправлення системних сповіщень та звітів.
  * **Контрактний довідник:** [`~/.gemini/config/plugins/hybrid-ide/bin/ENCLAVE_INTERFACE.md`](file:///home/hills/.gemini/config/plugins/hybrid-ide/bin/ENCLAVE_INTERFACE.md) (локально [`core/enclave/ENCLAVE_INTERFACE.md`](file:///home/hills/Documents/Hybrid-IDE-for-contributors/core/enclave/ENCLAVE_INTERFACE.md), читання через `view_file`).
  * **Верифікаційні інструменти:** [`~/.gemini/config/plugins/hybrid-ide/bin/phase5_verify.py`](file:///home/hills/.gemini/config/plugins/hybrid-ide/bin/phase5_verify.py) (локально `core/verify/phase5_verify.py`, 40 unit-тестів + 10 auditor + 37/37 перевірок політики).
- **Регламент інструментальних запитів до Анклаву (Anchored Instrumental Requests):**
  * Оркестратору заборонено надсилати неструктуровані чи сліпі промпти («зроби щось», «напиши код»).
  * Перед кожним викликом оркестратор зобов'язаний звіритися з інтерфейсом `core/enclave/ENCLAVE_INTERFACE.md` або викликом `enclave_daemon.py --help-tools`.
  * Усі запити мають бути суто параметризованими: точний шлях (`target_path`), конкретне ТЗ (`task_prompt`) або код (`direct_code`), при модифікації — точний рядок (`patch_target`) та номери рядків (`start_line`, `end_line`), режим (`synthesize` / `patch`), рівень моделі (`tier`).

## 4. Правила коду та гігієни
- **Zero-Dep:** Жодних сторонніх PyPI бібліотек.
- **Bytecode:** Обов'язково `sys.dont_write_bytecode = True` у всіх `.py`.
- **Bash:** `set -euo pipefail` та коментарі на початку скрипта.
- **Brain-First Storage:** Усі сесійні файли (кроки, контракти, історія, прапорці, леджер, паспорти) зберігаються у `<artifactDirectoryPath>/.system_generated/`, що гарантує захист від видалення при перезавантаженні ОС.

## 5. Верифікація, запечатування та реліз (Фаза 5)
- **Mandatory Proactive Telemetry Gate (Zero-Omission):** заборонено надсилати фазові звіти Фази 1 (стартовий банер), Фази 2/3 (запит на схвалення) та Фази 5 (фінальний звіт і `walkthrough.md`) без свіжого виміряного віджета 2D-телеметрії у блоці коду `text` (отриманого через `python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase1_inspect.py --telemetry` або `core/inspect/phase1_inspect.py --telemetry`).
- **Локальна верифікація:** `python3 core/verify/phase5_verify.py` (40 unit-тестів + 37/37 перевірок + тести аудитора).
- **Синтаксис:** `python3 -m py_compile <шлях_до_файлу.py>`.
- **Аудит контексту чату:** `python3 core/verify/chat_context_auditor.py --current-session --strict`.
- **Запечатування стану (Git State Seal Gate):** обов'язковий локальний `git commit` перед публікацією `walkthrough.md`.
- **CI перевірка:** `python3 core/verify/verify_remote_ci.py`.
- **Публікація:** `./push_to_github.sh` (суворо після команди `++`).

## 6. Стиль комітів
- `<type>(<scope>): <опис> [generated: <model> | verified: antigravity]`
- Передрелізний аудит: `chore(release): ... [audited: copilot-cli | verified: claude | verified: antigravity]`


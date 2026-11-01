---
name: reglament
description: >-
  Audits the current session for strict compliance with Hybrid IDE General
  Execution Policy (Kernel v0.9.12), performs the mandatory Trusted Enclave
  Battle Test (Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet, Tier 4.5 Copilot CLI),
  verifies Global Plugin rules, Tool Catalog, and domain overlay AGENTS.md policies,
  and outputs the structured Plugin & Overlay Integration Log.
  Triggered by /reglament [version] or /reglamet [version].
---

# 🛡️ Регламентний аудит та перевірка ШІ-матриці (/reglament, /reglamet) (Kernel v0.9.12)

Використовуйте цю навичку щоразу, коли користувач вводить `/reglament` або `/reglamet` (з опціональним аргументом версії, наприклад `/reglament v0.9.12`), просить «перевірити регламент», «налаштувати чат на регламент» або провести повну діагностику готовності сесії до розробки.

---

## 1. Залізні правила дисципліни (Anti-DIY Tenets)

1. **«Пиляти через Антігравіті зась!»:**  
   Агенту **суворо заборонено** самостійно кодити, писати реалізації функцій чи вигадувати правки «від себе». Будь-який код генерується виключно через моделі ШІ (Tier 1/2 з `GENERATIVE_MODELS_ALLOWLIST`) з випуском активного криптографічного паспорта (`mint_passport -> reserve_passport -> apply_passport`).
2. **Заборона інлайн-викликів (Zero Inline-Eval Hard Gate):**  
   Категорично заборонено `python3 -c '...'`, `--eval`, `bash -c '...'`, `eval`, `exec` або Here-docs (`<<EOF`).
3. **Ізоляція системного стану (Shell State Isolation Gate):**  
   Категорично заборонено перенаправлення виводу (`>`, `>>`, `tee`) у системні каталоги `.system_generated/**`, файли леджера `provenance_ledger*` та код ядра `core/**`.
4. **Заборона сліпого обходу дисків (Git & Index First):**  
   Категорично заборонено `ls`, `dir`, `find_by_name`, `list_dir`, `grep_search`. Усі перевірки структури беруться виключно через `git ls-files`, `git status -sb`, `git log -n 5` та маніфести знань.
5. **Якірний шлюз (Anchored Grounding & Anti-Echo Gate):**  
   Заборонено абстрактні запити («найди щось», «чому не працює»). Обов'язкова наявність тріади: `[0x.../символ] + [файл/розширення] + [точна сигнатура]`.
6. **Чисті форми команд (Zero Friction Command Shapes):**  
   Категорично заборонено поєднувати команди через `&&`, `||`, `|`, `$()`. Тільки окремі префіксні виклики (`BypassSandbox: true`).
7. **Вимога паритету чату та артефактів (Chat & Artifact Parity):**  
   Отримані віджети інференсу `[AI Invocation Event]` зобов'язані виводитися прямо у фінальне повідомлення чату.

---

## 2. Покроковий протокол виконання при виклику `/reglament`

### 🛑 Крок 1: Phase 1 Status Banner та 2D-телеметрія контексту
1. Виконати динамічне зняття метрик сесії:
   `python3 core/enclave/enclave_daemon.py --telemetry`
   *(Fallback: `python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase1_inspect.py --telemetry`)*
2. Вивести обов'язковий публічний статус разом із віджетом `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]`:
   - **Зафіксований домен:** `<Поточний домен робочого простору>`
   - **Індикатор контексту:** `<Реальна зона (🟢/🟡/🔴) за кроками S та токенами Nin/Nout>`
   - **Режим пісочниці:** `Bypass Sandbox: true (Host-First Protocol v0.9.12)`
   - **Статус Batch Access:** `Авторизовано регламентом`
   - **Цільова версія:** `v0.9.12` (Trusted Enclave Architecture, Multi-Tier AI Gateway, 2D-Telemetry, Phase 5.2 Git State Seal Gate)

### 🛑 Крок 2: Бойовий 4-Tier аудит ШІ-матриці через Довірений Анклав
Виконати єдиною пакетною командою (`BypassSandbox: true`):
`python3 core/enclave/enclave_daemon.py --battle-test`
*(Перевіряє Tier 1 Ollama 1.5b, Tier 2 Groq 120b, Tier 4 Claude Sonnet 3.5 та Tier 4.5 Copilot CLI probe. Fallback: `python3 ~/.gemini/config/plugins/hybrid-ide/bin/diagnostic_runner.py --battle-test`)*

*Обов'язково вивести віджети `[AI Invocation Event]` для всіх активних провайдерів у чат!*

### 🛑 Крок 3: Структурований лог інтеграції плагіна та оверлею
Сформувати та вивести докладний лог:

```text
======================================================================
📦 [PLUGIN & OVERLAY INTEGRATION LOG]
======================================================================
[Step 1: Global Plugin Discovery]
  - Шлях плагіна:   ~/.gemini/config/plugins/hybrid-ide/
  - Маніфест:       plugin.json (v1.0.0, Kernel v0.9.12)
  - Хуки безпеки:   hooks.json (PreToolUse OS Gates v0.9.12, PostToolUse Breaker, Stop)
  - Статус хуків:   🟢 Активно (єдиний глобальний обробник)

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md (Kernel v0.9.12)
  - OS Hard Gates:  Zero Inline-Eval, Shell State Isolation, Cryptographic Hash Passports, In-Memory Simulation
  - Дисципліна:     5 обов'язкових фаз, Anchored Grounding Gate, Anti-Echo Protocol

[Step 3: Domain Overlay Resolution & Core Policies]
  - Файл оверлею:   <workspace_root>/AGENTS.md
  - 5 фаз Анклаву:  1.Діагностика (телеметрія) -> 2.План -> 2.5.Pre-Approval (Claude Sonnet / Attest) -> 3.Схвалення (+/++) -> 4.1.Context Assembly -> 4.2.Pre-Check (Sonnet) -> 4.3.Синтез Анклавом (FrugalGPT Ollama 1.5b/3b/7b, Groq 120B overflow, Anti-Echo, HMAC Schema 1.2) -> 4.4.AST & Compile Gate -> 4.5.Pre-Release Arbiter (Copilot CLI -> Failover на Claude Sonnet) -> 5.Верифікація (40 unit + 10 auditor + 37/37)
  - Двогейтовий суверенітет: '+' для локальних змін/коміту; '++' для релізу/пушу
  - Zero-SHA:       Антігравіті суворо заборонено самостійно обчислювати хеші чи випускати паспорти

[Step 3.1: Tool Catalog & Satellite Interfaces]
  - Головні інструменти Анклаву (core/enclave/enclave_daemon.py):
    * POST /apply (--target, --task | --direct-code) — атомарний синтез/патч
    * POST /query (--query) — суверенний мульти-Tier ШІ-шлюз (FrugalGPT & Failover)
    * GET /battle-test (--battle-test) — бойовий 4-Tier тест
    * GET /telemetry (--telemetry) — 2D-телеметрія сесії та RAM
    * GET /help (--help-tools) — схема та параметри контрактів
    * GET /verify-chain (--verify-chain) — верифікація ланцюга паспортів
    * POST /attest (--attest-arbiter) — атестаційний гейт Antigravity Pool
  - Супутні та зовнішні інтерфейси:
    * LinkedIn Developer API: OAuth 2.0 у ~/.env (LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI)
    * Email & SMTP нотифікації: системні сповіщення та релізи
    * Контрактний довідник: core/enclave/ENCLAVE_INTERFACE.md (читання через view_file)
    * Верифікатор: core/verify/phase5_verify.py (40 unit + 10 auditor + 37/37 перевірок)

[Step 3.2: Anchored Instrumental Requests Protocol]
  - Обов'язкова звірка з ENCLAVE_INTERFACE.md або --help-tools перед запитом
  - Тільки параметризовані виклики (target_path, task_prompt, direct_code, patch_target, start_line, end_line, mode, tier)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Декупловано з підпроєктів (файли GEMINI.md вичищено)
  - Колізії хуків:  🟢 Локальні .agents/hooks.json деактивовано ({})
  - Валідатор:      40 unit-тестів + 37/37 перевірок пройдено (core/verify/phase5_verify.py)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано в активний контекст
======================================================================
```

### 🛑 Крок 4: Стан Git та підсумковий чек-лист
1. Перевірити `git status -sb` та `git log -n 3 --oneline`.
   * **Важливо для сесій без прив'язки до каталогу (відкритих у `$HOME`):** виконувати через `git -C "<шлях_до_проєкту>" status -sb` та `git -C "<шлях_до_проєкту>" log -n 3 --oneline`. Заборонено шукати каталоги наосліп.
2. Запустити системний валідатор політики (`python3 core/verify/phase5_verify.py`).
3. Вивести підсумковий вердикт готовності до розробки за регламентом 5 фаз.

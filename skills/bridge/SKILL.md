---
name: bridge
description: >-
  Generates a canonical Bridge Prompt to transition context to a new chat
  under Hybrid IDE Kernel v0.9.11, enforcing the Trusted Enclave Battle Test,
  complete Tool Catalog & Satellite Interfaces, Anchored Instrumental Requests,
  and domain overlay AGENTS.md binding. Invoked as /bridge [version].
---

# 🌉 Bridge Prompt Generator (Hybrid IDE Kernel v0.9.11)

Використовуйте цю навичку щоразу, коли користувач вводить `/bridge` (з версією або без), при вичерпанні контексту (🔴 Зона 3: >800 кроків або >160k токенів) або для безшовного переходу в нову сесію без втрати прогресу, галюцинацій та повторного сканування кодової бази.

## Синтаксис виклику та версії

- **`/bridge` (без аргументу):**
  Автоматично застосовує актуальний Регламент **`v0.9.11`** та доменні оверлеї `AGENTS.md`.
- **`/bridge <версія>`:**
  Активує цільову версію відповідно до архівних маніфестів.

---

## Інструкції для агента при виклику `/bridge`

1. **Детерміністична генерація через валідатор ядра (Рекомендовано):**
   Виконати окремою чистою командою (`BypassSandbox: true`):
   ```bash
   python3 core/engine/validate_migration_content.py --generate-bridge
   ```
   *Генератор автоматично зчитує робочий простір, активну гілку, останній коміт, шлях до `walkthrough.md` та проводить Fail-Closed валідацію контенту на відсутність інструкцій уникання чи протидії регламенту.*

2. **Ручна збірка (Fallback за відсутності генератора):**
   - Зібрати оперативний стан: `git status -sb` та `git log -n 3 --oneline`.
   - Зафіксувати найсвіжіший артефакт `walkthrough.md`.
   - Згенерувати канонічний Bridge Prompt та провести обов'язкову валідацію:
     `python3 core/engine/validate_migration_content.py --file <шлях_до_згенерованого_файлу>`.

3. **Канонічний шаблон Bridge Prompt (Kernel v0.9.11):**

````markdown
# 🌉 Регламентний старт: 4-Tier аудит ШІ-матриці та інтеграція AGENTS.md (v0.9.11)

## 1. Метадані стану та середовища
- **Версія Регламенту:** `v0.9.11` (Trusted Enclave Architecture, Multi-Tier AI Gateway, Schema 1.2 HMAC Passports)
- **Домен:** `<Назва домену>` (`<Повний шлях до робочого простору>`)
- **Parent Conversation ID:** `<Поточний Conversation ID>`
- **Active Git Branch:** `<Поточна гілка>` (коміт `<HEAD Commit SHA>`)
- **Чинне Конституційне ядро:** `~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`
- **Доменний оверлей проєкту:** `<project_root>/AGENTS.md` (всі файли `GEMINI.md` утилізовано)
- **Попередній Walkthrough:** [`walkthrough.md`](file://<шлях_до_walkthrough.md>)

---

## 2. Імперативний стартовий протокол (Strict Step-by-Step Gate)

### 🛑 Крок 1: Phase 1 Status Banner та 2D-телеметрія контексту
Виконати динамічний вимір метрик (`core/enclave/enclave_daemon.py --telemetry` або `core/inspect/phase1_inspect.py --telemetry`) та вивести обов'язковий статус:
`🎯 [DOMAIN: <Домен> | HOST: Linux/Debian]`
`<Індикатор 🟢/🟡/🔴> [CONTEXT: <S> кроків (~<tok>k tok) | SANDBOX: Host-First BypassSandbox | BATCH ACCESS: Authorized]`
*(Обов'язково вивести віджет `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]` у чат!)*

### 🛑 Крок 2: Бойова перевірка ШІ-матриці через Довірений Анклав
Виконати єдиною пакетною командою (`BypassSandbox: true`):
`python3 core/enclave/enclave_daemon.py --battle-test`
*(Перевіряє Tier 1 Ollama 1.5b, Tier 2 Groq 120b, Tier 4 Claude Sonnet 3.5 та Tier 4.5 Copilot CLI probe)*

### 🛑 Крок 3: Лог інтеграції плагіна та доменного оверлею
Сформувати та вивести структурований звіт:
```text
======================================================================
📦 [PLUGIN & OVERLAY INTEGRATION LOG]
======================================================================
[Step 1: Global Plugin Discovery]
  - Шлях плагіна:   ~/.gemini/config/plugins/hybrid-ide/
  - Маніфест:       plugin.json (v1.0.0, Kernel v0.9.11)
  - Хуки безпеки:   hooks.json (PreToolUse OS Gates, PostToolUse Breaker, Stop)
  - Статус хуків:   🟢 Активно (єдиний глобальний обробник)

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md (Kernel v0.9.11)
  - OS Hard Gates:  Zero Inline-Eval, Shell State Isolation, Cryptographic Hash Passports, In-Memory Simulation
  - Дисципліна:     5 обов'язкових фаз, Anchored Grounding Gate, Anti-Echo Protocol

[Step 3: Domain Overlay Resolution & Core Policies]
  - Файл оверлею:   <project_root>/AGENTS.md
  - 5 фаз Анклаву:  1.Діагностика (телеметрія) -> 2.План -> 2.5.Pre-Approval (Claude Sonnet / Attest) -> 3.Схвалення (+/++) -> 4.1.Context Assembly -> 4.2.Pre-Check (Sonnet) -> 4.3.Синтез Анклавом (FrugalGPT Ollama 1.5b/3b/7b, Groq 120B overflow, Anti-Echo, HMAC Schema 1.2) -> 4.4.AST & Compile Gate -> 4.5.Pre-Release Arbiter (Copilot CLI -> Failover на Claude Sonnet) -> 5.Верифікація (40 unit + 37/37)
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
    * Верифікатор: core/verify/phase5_verify.py (40 unit + 37/37 перевірок)

[Step 3.2: Anchored Instrumental Requests Protocol]
  - Обов'язкова звірка з ENCLAVE_INTERFACE.md або --help-tools перед запитом
  - Тільки параметризовані виклики (target_path, task_prompt, direct_code, patch_target, start_line, end_line, mode, tier)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Декупловано з підпроєктів (файли GEMINI.md вичищено)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано в активний контекст
======================================================================
```

### 🛑 Крок 4: Стан Git та перехід до Фази 1
Перевірити `git status -sb` та `git log -n 3 --oneline`. Зчитати попередній `walkthrough.md` та перейти до виконання завдань за 5-фазним регламентом.

> [!CAUTION]
> Доки Кроки 1–3 не виконано на 100% (PASS) з публікацією віджетів інференсу для всіх провайдерів, агенту категорично заборонено змінювати бойовий код!
````

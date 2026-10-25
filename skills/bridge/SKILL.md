---
name: bridge
description: >-
  Generates a canonical Bridge Prompt to transition context to a new chat
  under Hybrid IDE Kernel v0.9.10, enforcing the mandatory 4-Tier AI Battle Test,
  structured Plugin & Overlay Integration Log, Cryptographic Hash Passports,
  and domain overlay AGENTS.md binding. Invoked as /bridge [version].
---

# 🌉 Bridge Prompt Generator (Hybrid IDE Kernel v0.9.10)

Використовуйте цю навичку щоразу, коли користувач вводить `/bridge` (з версією або без), при вичерпанні контексту (🔴 Зона 3: >800 кроків або >160k токенів) або для безшовного переходу в нову сесію без втрати прогресу, галюцинацій та повторного сканування кодової бази.

## Синтаксис виклику та версії

- **`/bridge` (без аргументу):**
  Автоматично застосовує актуальний Регламент **`v0.9.10`** та доменні оверлеї `AGENTS.md`.
- **`/bridge <версія>`:**
  Активує цільову версію відповідно до архівних маніфестів.

---

## Інструкції для агента при виклику `/bridge`

1. **Детерміністична генерація через раннер ядра (Рекомендовано):**
   Виконати окремою чистою командою (`BypassSandbox: true`):
   ```bash
   python3 core/engine/diagnostic_runner.py --bridge
   ```
   *Раннер автоматично зчитує робочий простір, активну гілку, останній коміт, шлях до `walkthrough.md` та проводить Fail-Closed валідацію контенту на відсутність інструкцій уникання чи протидії регламенту.*

2. **Ручна збірка (Fallback за відсутності раннера):**
   - Зібрати оперативний стан: `git status -sb` та `git log -n 3 --oneline`.
   - Зафіксувати найсвіжіший артефакт `walkthrough.md`.
   - Згенерувати канонічний Bridge Prompt та провести обов'язкову валідацію:
     `python3 core/engine/validate_migration_content.py --file <шлях_до_згенерованого_файлу>`.

3. **Канонічний шаблон Bridge Prompt (Kernel v0.9.10):**

````markdown
# 🌉 Регламентний старт: 4-Tier аудит ШІ-матриці та інтеграція AGENTS.md (v0.9.10)

## 1. Метадані стану та середовища
- **Версія Регламенту:** `v0.9.10` (Cryptographic Hash Passports, Shell State Isolation & In-Memory Simulation)
- **Домен:** `<Назва домену>` (`<Повний шлях до робочого простору>`)
- **Parent Conversation ID:** `<Поточний Conversation ID>`
- **Active Git Branch:** `<Поточна гілка>` (коміт `<HEAD Commit SHA>`)
- **Чинне Конституційне ядро:** `~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`
- **Доменний оверлей проєкту:** `<project_root>/AGENTS.md` (всі файли `GEMINI.md` утилізовано)
- **Попередній Walkthrough:** [`walkthrough.md`](file://<шлях_до_walkthrough.md>)

---

## 2. Імперативний стартовий протокол (Strict Step-by-Step Gate)

### 🛑 Крок 1: Phase 1 Status Banner та 2D-телеметрія контексту
Виконати динамічний вимір метрик (`core/inspect/phase1_inspect.py --telemetry`) та вивести обов'язковий статус:
`🎯 [DOMAIN: <Домен> | HOST: Linux/Debian]`
`<Індикатор 🟢/🟡/🔴> [CONTEXT: <S> кроків (~<tok>k tok) | SANDBOX: Host-First BypassSandbox | BATCH ACCESS: Authorized]`
*(Обов'язково вивести віджет `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]` у чат!)*

### 🛑 Крок 2: Бойова перевірка ВСІХ 4 рівнів ШІ-матриці
Виконати окремими одиночними викликами (`BypassSandbox: true`) та вивести стандартизовані віджети `[AI Invocation Event]` для кожного провайдера:

1. **Tier 1 (Local Edge Ollama):**
   `python3 core/engine/diagnostic_runner.py --ollama-query "Ping: confirm status in 5 words" --model qwen2.5-coder:1.5b`
2. **Tier 2 (Cloud Fallback Hub Groq LPU):**
   `python3 core/engine/diagnostic_runner.py --groq-query "Ping: confirm status in 5 words"`
3. **Tier 4 (Claude Sonnet 5.5 / Arbiter):**
   Сформувати підтвердження готовності Шлюзу 2.5 та 4.2 до аудиту контрактів та сигнатур (`--sonnet-query`).
4. **Tier 4.5 (GitHub Copilot CLI — Pre-Release Arbiter Probe):**
   `copilot --version` (перевірка зв'язку та готовності CLI; запуск prompt `-p` потребує схвалення `+`).

### 🛑 Крок 3: Лог інтеграції плагіна та доменного оверлею
Сформувати та вивести структурований звіт:
```text
======================================================================
📦 [PLUGIN & OVERLAY INTEGRATION LOG]
======================================================================
[Step 1: Global Plugin Discovery]
  - Шлях плагіна:   ~/.gemini/config/plugins/hybrid-ide/
  - Маніфест:       plugin.json (v1.0.0, Kernel v0.9.10)
  - Хуки безпеки:   hooks.json (PreToolUse OS Gates, PostToolUse Breaker, Stop)
  - Статус хуків:   🟢 Активно (єдиний глобальний обробник)

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md
  - OS Hard Gates:  Zero Inline-Eval, Shell State Isolation, Cryptographic Hash Passports, In-Memory Simulation
  - Дисципліна:     5 обов'язкових фаз, Anchored Grounding Gate, Anti-Echo Protocol

[Step 3: Domain Overlay Resolution]
  - Файл оверлею:   <project_root>/AGENTS.md
  - Специфікація:   Шлюз 2.5 (Sonnet Pre-Approval), Шлюз 4.2 (Sonnet Pre-Check), Pre-Release Gate (Copilot CLI)

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

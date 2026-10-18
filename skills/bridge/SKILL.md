---
name: bridge
description: >-
  Generates a canonical Bridge Prompt to transition context to a new chat
  under Hybrid IDE policy v0.9.6, enforcing the mandatory 4-Tier AI Battle Test,
  structured Plugin & Overlay Integration Log, and domain overlay AGENTS.md binding.
  Invoked as /bridge [version].
---

# 🌉 Bridge Prompt Generator (Hybrid IDE Policy v0.9.6)

Використовуйте цю навичку щоразу, коли користувач вводить `/bridge` (з версією або без), при вичерпанні контексту або для безшовного переходу в нову сесію без втрати прогресу, галюцинацій та повторного сканування кодової бази.

## Синтаксис виклику та версії

- **`/bridge` (без аргументу):**
  Автоматично застосовує актуальний Регламент **`v0.9.6`** та доменні оверлеї `AGENTS.md`.
- **`/bridge <версія>` (наприклад `/bridge v0.9.5`, `/bridge v0.8`):**
  Активує цільову версію відповідно до архівних маніфестів.

---

## Інструкції для агента при виклику `/bridge`

1. **Збір оперативного стану (Git & Surface First):**
   Виконати окремими чистими командами (`BypassSandbox: true`):
   - `git status -sb`
   - `git log -n 3 --oneline`
2. **Визначення цільового робочого простору (`Lineage Target`):**
   - Зафіксувати поточний активний каталог (наприклад, `/home/hills/Documents/Hybrid-IDE-for-contributors` або `/home/hills/Documents/fallaut`).
   - Знайти найсвіжіший артефакт `walkthrough.md`.
3. **Генерація канонічного Bridge Prompt:**
   Вивести в чат готовий для копіювання блок markdown такого змісту:

````markdown
# 🌉 Регламентний старт: 4-Tier аудит ШІ-матриці та інтеграція AGENTS.md (v0.9.6)

## 1. Метадані стану та середовища
- **Версія Регламенту:** `v0.9.6` (Global Plugin Architecture & Domain Overlays)
- **Домен:** `<Назва домену>` (`<Повний шлях до робочого простору>`)
- **Parent Conversation ID:** `<Поточний Conversation ID>`
- **Active Git Branch:** `<Поточна гілка>` (коміт `<HEAD Commit SHA>`)
- **Чинне Конституційне ядро:** `~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`
- **Доменний оверлей проєкту:** `<project_root>/AGENTS.md` (всі файли `GEMINI.md` утилізовано)
- **Попередній Walkthrough:** [`walkthrough.md`](file://<шлях_до_walkthrough.md>)

---

## 2. Імперативний стартовий протокол (Strict Step-by-Step Gate)

### 🛑 Крок 1: Phase 1 Status Banner
Вивести обов'язковий банер:
`🎯 [DOMAIN: <Домен> | HOST: Linux/Debian]`
`🟢 [CONTEXT: Оптимальний | SANDBOX: Host-First BypassSandbox | BATCH ACCESS: Authorized]`

### 🛑 Крок 2: Бойова перевірка ВСІХ 4 рівнів ШІ-матриці
Виконати окремими одиночними викликами (`BypassSandbox: true`) та вивести стандартизовані віджети `[AI Invocation Event]` для кожного провайдера:

1. **Tier 1 (Local Edge Ollama):**
   `python3 core/engine/diagnostic_runner.py --ollama-query "Ping: confirm status in 5 words" --model qwen2.5-coder:1.5b`
2. **Tier 2 (Cloud Fallback Hub Groq LPU):**
   `python3 core/engine/diagnostic_runner.py --groq-query "Ping: confirm status in 5 words"`
3. **Tier 4 (Claude Sonnet 4.1 — Code Arbiter):**
   Сформувати підтвердження готовності Шлюзу 4.1 до аудиту сигнатур та контрактів.
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
  - Маніфест:       plugin.json (v1.0.0)
  - Хуки безпеки:   hooks.json (PreToolUse, PostToolUse, Stop)
  - Статус хуків:   🟢 Активно

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md (3.7 КБ)
  - Заборони:       Zero Inline-Eval, Git & Index First, Step Budget

[Step 3: Domain Overlay Resolution]
  - Файл оверлею:   <project_root>/AGENTS.md
  - Специфікація:   Шлюз 4.1 (Sonnet), Pre-Release Gate (Copilot CLI)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Декупловано з підпроєктів (fallaut/ та contributors вичищено)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано
======================================================================
```

### 🛑 Крок 4: Стан Git та перехід до Фази 1
Перевірити `git status -sb` та `git log -n 3 --oneline`. Зчитати попередній `walkthrough.md` та перейти до виконання завдань за 5-фазним регламентом.

> [!CAUTION]
> Доки Кроки 1–3 не виконано на 100% (PASS) з публікацією віджетів інференсу для всіх провайдерів, агенту категорично заборонено змінювати бойовий код!
````

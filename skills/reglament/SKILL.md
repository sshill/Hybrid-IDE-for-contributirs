---
name: reglament
description: >-
  Audits the current session for strict compliance with Hybrid IDE General
  Execution Policy v0.9.6, performs the mandatory 4-Tier AI Battle Test
  (Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet, Tier 4.5 Copilot CLI),
  verifies Global Plugin rules and domain overlay AGENTS.md, and outputs
  the structured Plugin & Overlay Integration Log.
  Triggered by /reglament [version] or /reglamet [version].
---

# 🛡️ Регламентний аудит та перевірка ШІ-матриці (/reglament, /reglamet)

Використовуйте цю навичку щоразу, коли користувач вводить `/reglament` або `/reglamet` (з опціональним аргументом версії, наприклад `/reglament v0.9.6`), просить «перевірити регламент», «налаштувати чат на регламент» або провести повну діагностику готовності сесії до розробки.

---

## 1. Залізні правила дисципліни (Anti-DIY Tenets)

1. **«Пиляти через Антігравіті зась!»:**  
   Агенту **суворо заборонено** самостійно кодити, писати реалізації функцій чи вигадувати правки «від себе». Код генерується виключно через моделі ШІ (Tier 1/2) з реєстрацією в SLSA Provenance Ledger.
2. **Заборона інлайн-викликів (Zero Inline-Eval Hard Gate):**  
   Категорично заборонено `python3 -c '...'`, `--eval`, `bash -c '...'`, `eval`, `exec` або Here-docs (`<<EOF`).
3. **Заборона сліпого обходу дисків (Git & Index First):**  
   Категорично заборонено `ls -la`, `find_by_name`, `list_dir`, `grep_search`. Усі перевірки структури беруться виключно через `git ls-files`, `git status -sb`, `git log -n 5` та маніфести знань.
4. **Чисті форми команд (Zero Friction Command Shapes):**  
   Категорично заборонено поєднувати команди через `&&`, `||`, `|`, `$()`. Тільки окремі префіксні виклики (`BypassSandbox: true`).
5. **Вимога паритету чату та артефактів (Chat & Artifact Parity):**  
   Отримані віджети інференсу `[AI Invocation Event]` зобов'язані виводитися прямо у фінальне повідомлення чату.

---

## 2. Покроковий протокол виконання при виклику `/reglament`

### 🛑 Крок 1: Phase 1 Status Banner
Вивести в чат обов'язковий публічний статус:
- **Зафіксований домен:** `<Поточний домен робочого простору>`
- **Індикатор контексту:** `🟢 Оптимальний`
- **Режим пісочниці:** `Bypass Sandbox: true (Host-First Protocol v0.9.6)`
- **Статус Batch Access:** `Авторизовано регламентом`
- **Цільова версія:** `v0.9.6` (Global Plugin Architecture)

### 🛑 Крок 2: Бойовий 4-Tier аудит ШІ-матриці
Виконати окремими одиночними командами (`BypassSandbox: true`):
1. **Tier 1 (Local Edge Ollama):**
   `python3 core/engine/diagnostic_runner.py --ollama-query "Ping: confirm status in 5 words" --model qwen2.5-coder:1.5b`
2. **Tier 2 (Cloud Fallback Hub Groq LPU):**
   `python3 core/engine/diagnostic_runner.py --groq-query "Ping: confirm status in 5 words"`
3. **Tier 4.5 (GitHub Copilot CLI — Pre-Release Arbiter):**
   `copilot --version`
4. **Tier 4 (Claude Sonnet 4.1 — Code Arbiter):**
   Сформувати вердикт готовності Шлюзу 4.1 до аудиту контрактів, сигнатур API та повного сетапу файлів.

*Обов'язково вивести віджети `[AI Invocation Event]` для всіх активних провайдерів у чат!*

### 🛑 Крок 3: Структурований лог інтеграції плагіна та оверлею
Сформувати та вивести докладний лог:

```text
======================================================================
📦 [PLUGIN & OVERLAY INTEGRATION LOG]
======================================================================
[Step 1: Global Plugin Discovery]
  - Шлях плагіна:   ~/.gemini/config/plugins/hybrid-ide/
  - Маніфест:       plugin.json (v1.0.0, Hybrid IDE Core & Regulation Kernel)
  - Хуки безпеки:   hooks.json (PreToolUse OS Gates, PostToolUse Breaker, Stop Chimes)
  - Статус хуків:   🟢 Активно (єдиний глобальний обробник)

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md
  - Розмір:         3.7 КБ (3,743 байт, ліміт < 4 КБ)
  - Дисципліна:     5 обов'язкових фаз, Zero Inline-Eval, Git & Index First, Step Budget

[Step 3: Domain Overlay Resolution]
  - Файл оверлею:   <workspace_root>/AGENTS.md
  - Розмір:         < 1.5 КБ (Repository Docs Hygiene Gate: PASS)
  - Доменні норми:  Специфікація стеку, правила Шлюзу 4.1 (Sonnet), Pre-Release Gate (Copilot CLI)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Повністю вичищено (0 посилань на старий моноліт 20 КБ)
  - Колізії хуків:  🟢 Локальні .agents/hooks.json деактивовано ({})
  - Валідатор:      37/37 структурних перевірок пройдено (core/verify/validate_general_policy.py)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано в активний контекст
======================================================================
```

### 🛑 Крок 4: Стан Git та підсумковий чек-лист
1. Перевірити `git status -sb` та `git log -n 3 --oneline`.
2. Запустити системний валідатор політики (`python3 core/verify/phase5_verify.py`).
3. Вивести підсумковий вердикт готовності до розробки за регламентом 5 фаз.

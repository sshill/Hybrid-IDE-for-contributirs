---
name: reglament
description: >-
  Audits the current session for strict compliance with Hybrid IDE General
  Execution Policy (Kernel v0.9.10), performs the mandatory 4-Tier AI Battle Test
  (Tier 1 Ollama, Tier 2 Groq, Tier 4 Claude Sonnet, Tier 4.5 Copilot CLI),
  verifies Global Plugin rules and domain overlay AGENTS.md, and outputs
  the structured Plugin & Overlay Integration Log.
  Triggered by /reglament [version] or /reglamet [version].
---

# 🛡️ Регламентний аудит та перевірка ШІ-матриці (/reglament, /reglamet)

Використовуйте цю навичку щоразу, коли користувач вводить `/reglament` або `/reglamet` (з опціональним аргументом версії, наприклад `/reglament v0.9.10`), просить «перевірити регламент», «налаштувати чат на регламент» або провести повну діагностику готовності сесії до розробки.

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
   `python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase1_inspect.py --telemetry`
2. Вивести обов'язковий публічний статус разом із віджетом `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]`:
   - **Зафіксований домен:** `<Поточний домен робочого простору>`
   - **Індикатор контексту:** `<Реальна зона (🟢/🟡/🔴) за кроками S та токенами Nin/Nout>`
   - **Режим пісочниці:** `Bypass Sandbox: true (Host-First Protocol v0.9.10)`
   - **Статус Batch Access:** `Авторизовано регламентом`
   - **Цільова версія:** `v0.9.10` (Cryptographic Hash Passports, Shell State Isolation & In-Memory Simulation)

### 🛑 Крок 2: Бойовий 4-Tier аудит ШІ-матриці
Виконати окремими одиночними командами (`BypassSandbox: true`):
1. **Tier 1 (Local Edge Ollama):**
   `python3 ~/.gemini/config/plugins/hybrid-ide/bin/diagnostic_runner.py --ollama-query "Ping: confirm status in 5 words" --model qwen2.5-coder:1.5b`
2. **Tier 2 (Cloud Fallback Hub Groq LPU):**
   `python3 ~/.gemini/config/plugins/hybrid-ide/bin/diagnostic_runner.py --groq-query "Ping: confirm status in 5 words"`
3. **Tier 4 (Claude Sonnet 5.5 / Arbiter):**
   Підтвердити готовність Шлюзу 2.5 (Pre-Approval) та Шлюзу 4.2 (Pre-Check) через `--sonnet-query`.
4. **Tier 4.5 (GitHub Copilot CLI — Pre-Release Arbiter Probe):**
   `copilot --version` (перевірка зв'язку та готовності CLI; запуск prompt `-p` потребує схвалення `+`).

*Обов'язково вивести віджети `[AI Invocation Event]` для всіх активних провайдерів у чат!*

### 🛑 Крок 3: Структурований лог інтеграції плагіна та оверлею
Сформувати та вивести докладний лог:

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
  - Файл оверлею:   <workspace_root>/AGENTS.md
  - Доменні норми:  Специфікація стеку, правила Шлюзу 2.5/4.2 (Sonnet), Pre-Release Gate (Copilot CLI)

[Step 3.1: Domain Tools Manifest]
  - Витягнути та вивести таблицю інструментів із розділу «Каталог інструментів» (Tool Catalog) активного AGENTS.md
    (Агент зобов'язаний зафіксувати точні шляхи інструментів стенда для запобігання сліпому синтезу скриптів)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Декупловано з підпроєктів (файли GEMINI.md вичищено)
  - Колізії хуків:  🟢 Локальні .agents/hooks.json деактивовано ({})
  - Валідатор:      37/37 перевірок пройдено (core/verify/phase5_verify.py)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано в активний контекст
======================================================================
```

### 🛑 Крок 4: Стан Git та підсумковий чек-лист
1. Перевірити `git status -sb` та `git log -n 3 --oneline`.
   * **Важливо для сесій без прив'язки до каталогу (відкритих у `$HOME`):** виконувати через `git -C "<шлях_до_проєкту>" status -sb` та `git -C "<шлях_до_проєкту>" log -n 3 --oneline`. Заборонено шукати каталоги наосліп.
2. Запустити системний валідатор політики (`python3 core/verify/phase5_verify.py`).
3. Вивести підсумковий вердикт готовності до розробки за регламентом 5 фаз.

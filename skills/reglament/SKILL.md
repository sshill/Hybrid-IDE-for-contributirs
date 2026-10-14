---
name: reglament
description: >-
  Audits the current session for strict compliance with Antigravity General
  Execution Policy (v0.9.0+), runs pre-flight healthchecks on AI tiers
  (Tier 1 Ollama + Tier 2 Groq Cloud), validates Antigravity_Mgr tools,
  enforces the Zero Inline-Eval Gate and Git & Index First protocol, and locks
  the chat against ad-hoc DIY anti-patterns. Triggered by /reglament or /reglamet.
---

# 🛡️ Регламентний аудит та Анти-самопальний замок (/reglament, /reglamet)

Використовуйте цю навичку щоразу, коли користувач вводить `/reglament` або `/reglamet`, просить «перевірити регламент», «налаштувати чат на регламент» або повернути агента до дисципліни після відхилень від стандартів.

---

## 1. Залізні правила проти «самопалу» (Anti-DIY Tenets)

Коли активовано цю навичку, агент зобов'язаний зафіксувати такі категоричні заборони:
1. **«Пиляти через Антігравіті зась!»:**  
   Агенту **суворо заборонено** самостійно кодити, писати реалізації функцій, інлайн-скрипти чи вигадувати правки «від себе».
2. **Заборона інлайн-викликів (Zero Inline-Eval Hard Gate):**  
   Категорично заборонено `python3 -c '...'`, `--eval`, `bash -c '...'`, `eval`, `exec` або Here-docs (`<<EOF`).  
   Будь-який синтез діагностичного або робочого скрипта обов'язково делегується моделям ШІ:
   `python3 .agents/scripts/diagnostic_runner.py --synthesize-script "<завдання>" --out <файл>`
3. **Заборона сліпого обходу дисків (Git & Index First):**  
   Категорично заборонено `ls -la`, `find_by_name`, `list_dir`, `grep_search` для дослідження репозиторію та індексованих зон.  
   Усі списки файлів та перевірки беруться виключно через:
   - `git ls-files`
   - `git status -sb`
   - `git log -n 5 --oneline`
   - `git show HEAD:<шлях>`
   - Маніфести у `docs/knowledge/index/` та хабі `Antigravity_Mgr/`
4. **Чисті форми команд (Zero Friction Command Shapes):**  
   Категорично заборонено поєднувати команди через `&&`, `||`, `|`, `$()`. Тільки окремі префіксні виклики (`BypassSandbox: true`).
5. **Вимога паритету чату та артефактів (Chat & Artifact Parity):**  
   Отримані віджети інференсу `[AI Invocation Event]` зобов'язані виводитися прямо у фінальне видиме повідомлення чату (не ховати у згорнуті логи інструментів) та дублюватися у відповідні звіти.

---

## 2. Покроковий протокол виконання при виклику `/reglament`

### 🛑 Крок 1: Обов'язковий статус-банер (Phase 1 Status Banner)
Вивести в чат публічний статус:
- **Зафіксований домен:** `Системна інфраструктура / Регламентний аудит`
- **Індикатор контексту:** `🟢 Оптимальний`
- **Режим пісочниці:** `Bypass Sandbox: true (Host-First Execution Protocol v0.9.0)`
- **Статус Batch Access:** `Авторизовано регламентом`
- **Цільове завдання:** Повний аудит готовності чату, моделей ШІ та інструментів ядра.

### 🛑 Крок 2: Бойовий аудит інференсу агентів (Tier 1 Ollama + Tier 2 Groq)
Виконати окрему одиночну команду:
`python3 .agents/scripts/diagnostic_runner.py --check-agents` (`BypassSandbox: true`).
> [!IMPORTANT]
> Отримані віджети `[AI Invocation Event]` для **Local Ollama** (`qwen2.5-coder:1.5b`) та **Groq Cloud LPU** (`openai/gpt-oss-120b`) агент **зобов'язаний обов'язково скопіювати у своє видиме повідомлення чату**.

### 🛑 Крок 3: Аудит хабу `Antigravity_Mgr` та валідація політики
1. Перевірити наявність та цілісність інструментів 5 фаз через `git ls-files`:
   `git ls-files Antigravity_Mgr/tools/`
   Повинні бути присутні:
   - `Antigravity_Mgr/tools/phase1_inspect.py`
   - `Antigravity_Mgr/tools/phase2_router.py`
   - `Antigravity_Mgr/tools/phase4_provenance.py`
   - `Antigravity_Mgr/tools/phase5_verify.py`
2. Запустити системний валідатор політики:
   `python3 .agents/scripts/validate_general_policy.py` (`BypassSandbox: true`).
3. Перевірити стан робочого дерева:
   `git status -sb`
   `git log -n 3 --oneline`

### 🛑 Крок 4: Фіксація стану та зведений чек-лист
Сформувати підсумковий звіт за такою структурою:
- **ШІ-провайдери:** Справжні віджети інференсу Tier 1 (Ollama) та Tier 2 (Groq) на екрані.
- **Статус політики:** Результат `validate_general_policy.py` (PASS/FAIL).
- **Інструменти `Antigravity_Mgr`:** Підтвердження наявності всіх 4 інструментів фаз.
- **Статус Git:** Поточна гілка, останній коміт, наявність незафіксованих змін.
- **Режим роботи:** Підтвердження активності анти-самопальних замків (Zero Inline-Eval, Git & Index First, Single Command Shapes).

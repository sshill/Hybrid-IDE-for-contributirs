---
name: reglament
description: >-
  Audits the current session for strict compliance with Antigravity General
  Execution Policy (v0.9.0+), runs pre-flight healthchecks on all AI tiers
  (Tier 1 Ollama + Tier 2 Groq Cloud + Tier 4 Claude Sonnet 5.5 + Tier 5 Validator),
  validates dynamic policy manifests, enforces the Zero Inline-Eval Gate and
  Git & Index First protocol, and locks the chat against ad-hoc DIY anti-patterns.
  Triggered by /reglament [version] or /reglamet [version].
---

# 🛡️ Регламентний аудит та Анти-самопальний замок (/reglament, /reglamet)

Використовуйте цю навичку щоразу, коли користувач вводить `/reglament` або `/reglamet` (з опціональним аргументом версії, наприклад `/reglament v0.9` або `/reglament v0.8`), просить «перевірити регламент», «налаштувати чат на регламент» або повернути агента до дисципліни після відхилень від стандартів.

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

## 2. Покроковий протокол виконання при виклику `/reglament [version]`

### 🛑 Крок 1: Обов'язковий статус-банер (Phase 1 Status Banner)
Вивести в чат публічний статус:
- **Зафіксований домен:** `Системна інфраструктура / Регламентний аудит`
- **Індикатор контексту:** `🟢 Оптимальний`
- **Режим пісочниці:** `Bypass Sandbox: true (Host-First Execution Protocol v0.9.0)`
- **Статус Batch Access:** `Авторизовано регламентом`
- **Цільова версія:** динамічно визначена актуальна версія політики (за замовчуванням `v0.9.0`) або вказана в аргументі (`v0.8` тощо).
- **Цільове завдання:** Повний аудит готовності чату, перевірка ВСІХ рівнів ШІ (Tier 1, 2, 4, 5) та валідація інструментів ядра.

### 🛑 Крок 2: Бойовий аудит інференсу ВСІХ агентів (Tier 1 Ollama + Tier 2 Groq + Tier 4 Claude Sonnet)
Виконати окрему одиночну команду:
`python3 .agents/scripts/diagnostic_runner.py --check-agents` (`BypassSandbox: true`).

> [!IMPORTANT]
> Отримані віджети `[AI Invocation Event]` для **ВСІХ трьох провайдерів**:
> 1. **Tier 1 (Local Edge):** Local Ollama (`qwen2.5-coder:1.5b`)
> 2. **Tier 2 (Cloud Fallback Hub):** Groq Cloud LPU (`openai/gpt-oss-120b`)
> 3. **Tier 4 (Pre-Implementation Arbiter):** Claude Sonnet 5.5 (`Antigravity Pool` / `/tmp/antigravity_claude_verified.flag`)
> 
> Агент **зобов'язаний обов'язково скопіювати у своє видиме повідомлення чату**.

### 🛑 Крок 3: Аудит хабу `Antigravity_Mgr` та валідація політики
1. Визначити цільовий маніфест:
   - Якщо вказано версію (наприклад, `/reglament v0.8`), перевірити `docs/knowledge/index/policy_v0.8_manifest.json`.
   - За замовчуванням перевірити актуальний маніфест: `docs/knowledge/index/policy_v0.9_manifest.json`.
2. Перевірити цілісність ядра `GEMINI.md`:
   - Розмір ядра повинен бути $\le 20\text{ KB}$ (цільовий ліміт 20 480 байт, 0 байт урізання).
3. Перевірити наявність та цілісність інструментів 5 фаз через `git ls-files`:
   `git ls-files Antigravity_Mgr/tools/`
   Повинні бути присутні:
   - `Antigravity_Mgr/tools/phase1_inspect.py`
   - `Antigravity_Mgr/tools/phase2_router.py`
   - `Antigravity_Mgr/tools/phase4_provenance.py`
   - `Antigravity_Mgr/tools/phase5_verify.py`
4. Запустити системний валідатор політики:
   `python3 .agents/scripts/validate_general_policy.py` (`BypassSandbox: true`).
5. Перевірити стан робочого дерева:
   `git status -sb`
   `git log -n 5 --oneline`

### 🛑 Крок 4: Фіксація стану та зведений чек-лист
Сформувати підсумковий звіт за такою структурою:
- **ШІ-провайдери:** Справжні віджети інференсу Tier 1 (Ollama), Tier 2 (Groq) та Tier 4 (Claude Sonnet 5.5) на екрані.
- **Статус політики:** Результат `validate_general_policy.py` (PASS/FAIL) та розмір ядра `GEMINI.md`.
- **Інструменти `Antigravity_Mgr`:** Підтвердження наявності всіх 4 інструментів фаз.
- **Статус Git:** Поточна гілка, останній коміт, наявність незафіксованих змін.
- **Режим роботи:** Підтвердження активності анти-самопальних замків (Zero Inline-Eval, Git & Index First, Single Command Shapes).

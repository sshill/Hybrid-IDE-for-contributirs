---
name: bridge
description: >-
  Generates a canonical Bridge Prompt to transition context to a new chat
  upon context exhaustion or milestone completion. Invoked as /bridge [version].
  By default (no argument), dynamically activates the latest settings and active
  policy version (v0.8.3+). If a version is explicitly specified after a space
  (e.g. /bridge v0.6), targets that specific version.
---

# Bridge Prompt Generator (Dynamic Latest Settings / Explicit Version)

Use this skill whenever the user types `/bridge` (with or without arguments) or asks to generate a bridge prompt to transition context to a new session without losing state, without hallucinations, and without re-scanning files.

## Command Syntax & Argument Resolution

- **`/bridge` (без аргументу):**
  Автоматично визначає та застосовує **найновіші активні налаштування**.
  Динамічно зчитує поточну активну гілку Git (`git branch --show-current`) та найсвіжіший маніфест знань у `Antigravity_Mgr/artifacts/policy_v0.8_manifest.json` (регламент v0.8.3).
- **`/bridge <версія>` (з аргументом через пробіл, наприклад `/bridge v0.6` або `/bridge v0.7`):**
  Активує та генерує міст суворо під зазначену версію політики з відповідного маніфесту (наприклад, `policy_v0.6_manifest.json`).

## Instructions for the Agent

When this skill is triggered:
1. **Argument Parsing & Resolution:**
   - Перевірити вхідний рядок виклику.
   - Якщо вказано версію через пробіл (наприклад, `v0.6`, `v0.7`): обрати цю версію як цільову.
   - Якщо версію не вказано: за замовчуванням обрати найновішу активну версію системи (наразі `v0.8.3` / активна гілка `v0.8`).
2. **Quick Git Snapshot (Git First & Pure Command Shapes):**
   Run strictly as separate single commands:
   `git status -sb`
   `git log -n 3 --oneline`
   (Do NOT use `&&`, `||`, pipes `|`, or raw crawlers `view_file`/`list_dir`).
3. **Collect Active State & Manifests:**
   - Active branch and latest commit hash.
   - Latest `walkthrough.md` location in `Antigravity_Mgr/artifacts/`.
   - Manifest corresponding to the resolved version (`policy_v0.8_manifest.json` v0.8.3).
4. **Generate Canonical Bridge Prompt:**
   Output immediately a ready-to-copy markdown block following this strict structure:
   - **Перший рядок (Recommended Directive Title):** Чітка, однозначна назва без двозначностей та простору для галюцинацій:
     `# 🌉 Регламентний старт: Аудит зв'язку з ШІ-агентами, статус Git та засвоєння контексту v0.8.3`
   - **1. Метадані стану та середовища:** Версія v0.8.3, Parent Conversation ID, маніфест, стан гілок.
   - **2. Імперативний поетапний протокол (Strict Step-by-Step Gate):**
     - **Крок 1 (Обов'язковий старт — ШІ-агенти та Git):**
       1. Вивести Phase 1 Status Banner.
       2. Перевірити середовище та сервіси:  
          `python3 .agents/scripts/diagnostic_runner.py --check-all` (`BypassSandbox: true`).
       3. **Комплексний бойовий тест інференсу агентів (Tier 1 Ollama + Tier 2 Groq):**  
          `python3 .agents/scripts/diagnostic_runner.py --check-agents` (`BypassSandbox: true`).
       4. Перевірити Git (окремими одиночними викликами):  
          `git status`  
          `git log -n 3 --oneline`
     - **Обов'язкова видимість віджетів ШІ на екрані:** Отримані віджети `[AI Invocation Event]` (для Local Ollama та Groq Cloud LPU) агент **зобов'язаний обов'язково процитувати безпосередньо у фінальне видиме повідомлення чату**, щоб користувач бачив їх на екрані, а не всередині згорнутих логів інструментів.
     - **Залізна заборона (Domain & Script Lock):** Доки Крок 1 не пройдено на 100% (PASS) з публікацією віджетів інференсу для обох провайдерів, агенту **категорично заборонено** чіпати прикладні скрипти Fallout 4, білдери чи будь-який бізнес-код!
     - **Правило одиночних команд (Zero Friction Command Shapes):** Категорично заборонено поєднувати команди через `&&`, `||`, `|`, `$()`. Тільки чисті префіксні одиночні виклики для гарантії автосхвалення без модальних вікон.
     - **Крок 2 (Лише після успіху Кроку 1):** Зчитати висновки попередника з `Antigravity_Mgr/artifacts/walkthrough.md` і перейти до роботи з прикладним кодом за 5-фазним регламентом.
5. **Stop Execution:**
   Do not run secondary tools. Yield immediately to the user with the generated prompt.


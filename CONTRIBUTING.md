# 🤝 Посібник контриб'ютора / Contributor Guide
## Hybrid Agentic IDE: Deterministic Multi-Tier AI Framework

[ 🇺🇦 **Українська версія** ](#ukrainian) &nbsp;|&nbsp; [ 🇬🇧 **English Version** ](#english)

---

<a name="ukrainian"></a>
# 🇺🇦 Українська версія

Ласкаво просимо до спільноти розробників **Hybrid Agentic IDE**!

Фреймворк створено як відкриту платформу інженерного емпаверменту: він усуває штучні фінансові та інфраструктурні бар'єри ($20–$300/міс за комерційні ШІ) та надає повноцінний інструментарій розробки надскладних систем із нульовими додатковими витратами на токени (**0$ Marginal Token Cost**) на звичайному процесорі лаптопа під Debian 13 Linux.

### 🌟 Для кого цей проєкт:
* **Джуніори та студенти:** Навчання системній інженерній культурі, роботі через Git-буфери, аналізу AST та контрактам замість сліпої віри в LLM («вайб-кодинг»).
* **Ветерани війни та світчери:** Безкоштовний практичний трамплін для опанування сучасної розробки без дорогих підписок на комерційні хмари.
* **Системні архітектори та сеньйори:** Детерміністичний контроль ШІ-оркестрації, запобігання деградації контексту та автоматизовані перевірки надійності.

---

## 🏛️ Архітектурні правила контриб'ютингу (Core Principles)

Кожен внесок до репозиторію має суворо дотримуватися 4 архітектурних принципів:

1. **5-Фазний детерміністичний життєвий цикл:**
   - **Фаза 1 (Діагностика):** Дослідження виключно через `git status`, `git log`, маніфести та `diagnostic_runner.py`. Сліпий обхід (`ls`, `find`, `grep`) заблоковано на рівні ОС.
   - **Фаза 2 (План):** Створення `implementation_plan.md` із розрахунком RouteLLM SLA ($\le 30$ с) та квот Safe Budget Groq (-20%) до внесення першого байту змін.
   - **Фаза 3 (Approval Gate):** Зупинка для явного схвалення (`+` або `+!`). Деструктивні дії з Git (`git reset`, `git revert`, `git push`) без команди заборонені.
   - **Фаза 4 (Виконання):** Суворий контроль Step Budget, запобігання зацикленню ($W=4$), реєстрація SHA256 у реєстрі SLSA/in-toto.
   - **Фаза 5 (Верифікація):** Обов'язковий прогін 37 правил політики (`validate_general_policy.py 37/37 PASS`).

2. **Zero Inline-Eval Gate:**
   - Категорично заборонено інлайн-код: `python -c`, `bash -c`, `eval`, Here-docs (`<<EOF`).
   - Усі діагностичні та допоміжні скрипти синтезуються у файли та запускаються через `python3 .agents/scripts/diagnostic_runner.py --run <файл>`.

3. **Багаторівнева маршрутизація ШІ (0$ OPEX):**
   - **Tier 1 (Local Edge Ollama):** Рутинний код, AST, регулярні вирази виконуються локально моделлю `qwen2.5-coder:1.5b` на CPU.
   - **Tier 2 (Groq Cloud LPU):** Оверфлоу для великих контекстів через `openai/gpt-oss-120b` (14 400 RPD безкоштовно).
   - **Tier 4 (Code-Arbiter):** Claude Sonnet 5.5 через Copilot CLI резервується виключно для монолітного рефакторингу або при збоях аудиту.

4. **Апаратні обмеження хоста:**
   - Робоче середовище: Debian 13 Linux, 16 ГБ RAM, CPU лаптопа.
   - Заборона запуску локальних моделей $\ge 14$B (захист від вичерпання RAM).

---

## 🛠️ Робочий процес контриб'ютора (Step-by-Step)

1. **Форкніть та клонуйте репозиторій:**
   ```bash
   git clone https://github.com/<your-username>/Hybrid-IDE-for-contributors.git
   cd Hybrid-IDE-for-contributors
   ```

2. **Налаштуйте середовище та ключі:**
   ```bash
   cp .env.example ~/.env
   # Вкажіть GROQ_API_KEY (безкоштовний) та за бажанням GEMINI_API_KEY
   chmod 600 ~/.env
   ```

3. **Запустіть комплексну автоматичну перевірку:**
   ```bash
   ./setup_and_verify.sh
   ```

4. **Створіть робочу гілку:**
   ```bash
   git checkout -b feat/my-new-feature
   ```

5. **Перевірте відповідність регламенту перед відкриттям PR:**
   ```bash
   python3 core/verify/validate_general_policy.py
   ```
   Усі 37 тестів повинні мати статус `[PASS]`.

6. **Оформлення коміту:**
   ```bash
   git commit -m "feat(scope): короткий опис [generated: <model> | verified: antigravity]"
   ```

---

<a name="english"></a>
# 🇬🇧 English Version

Welcome to the **Hybrid Agentic IDE** contributor community!

This framework is built as an open-access platform for engineering empowerment: it dismantles artificial financial and infrastructure barriers ($20–$300/mo commercial AI subscriptions) and provides a full-fledged environment for complex systems development with zero marginal token costs (**$0 Marginal Token Cost**) on a standard laptop CPU running Debian 13 Linux.

### 🌟 Who This Project Is For:
* **Juniors & Students:** Fosters disciplined systems engineering, Git-buffer access, AST analysis, and explicit contracts over blind reliance on LLM generation ("vibe-coding").
* **Veterans & Switchers:** A free, professional springboard to re-enter and master modern software engineering without expensive commercial paywalls.
* **Systems Architects & Leads:** Deterministic AI orchestration, context degradation safeguards, and automated reliability gates.

---

## 🏛️ Core Contributing Principles

All contributions must strictly uphold the 4 architectural tenets:

1. **5-Phase Deterministic Pipeline:**
   - **Phase 1 (Diagnosis):** Exploration exclusively via `git status`, `git log`, JSON manifests, and `diagnostic_runner.py`. Blind directory crawling (`ls`, `find`, `grep`) is hard-blocked at the OS level.
   - **Phase 2 (Plan):** Synthesizes `implementation_plan.md` with RouteLLM SLA ($\le 30$s) and Groq Safe Budget (-20%) calculations prior to mutating a single byte.
   - **Phase 3 (Approval Gate):** Execution halts for explicit user approval (`+` or `+!`). Destructive Git operations (`git reset`, `git revert`, `git push`) are blocked without explicit instruction.
   - **Phase 4 (Execution):** Governed by dynamic step budget, semantic loop interception ($W=4$), and SLSA/in-toto SHA256 cryptographic provenance registration.
   - **Phase 5 (Verification):** Mandatory validation against the 37-point policy suite (`validate_general_policy.py 37/37 PASS`).

2. **Zero Inline-Eval Gate:**
   - Strictly prohibits anonymous inline terminal code: `python -c`, `bash -c`, `eval`, Here-docs (`<<EOF`).
   - All scripts must be cleanly synthesized to disk and executed through `python3 .agents/scripts/diagnostic_runner.py --run <file>`.

3. **Multi-Tier AI Routing ($0 OPEX):**
   - **Tier 1 (Local Edge Ollama):** Routine coding and AST analysis run locally on CPU via `qwen2.5-coder:1.5b`.
   - **Tier 2 (Groq Cloud LPU):** Cloud overflow for deep contexts via `openai/gpt-oss-120b` (14,400 RPD free tier).
   - **Tier 4 (Code-Arbiter):** Claude Sonnet 5.5 via Copilot CLI is reserved exclusively for monolithic refactoring or failed audit triggers.

4. **Hardware Budget Bounds:**
   - Target baseline: Debian 13 Linux, 16 GB RAM, standard CPU.
   - Local models $\ge 14$B are strictly prohibited to prevent host OOM collisions.

---

## 🛠️ Contributor Workflow (Step-by-Step)

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/Hybrid-IDE-for-contributors.git
   cd Hybrid-IDE-for-contributors
   ```

2. **Configure environment credentials:**
   ```bash
   cp .env.example ~/.env
   # Add your free GROQ_API_KEY and optional GEMINI_API_KEY
   chmod 600 ~/.env
   ```

3. **Execute automated end-to-end environment validation:**
   ```bash
   ./setup_and_verify.sh
   ```

4. **Create a topic branch:**
   ```bash
   git checkout -b feat/my-new-feature
   ```

5. **Verify policy compliance before submitting a PR:**
   ```bash
   python3 core/verify/validate_general_policy.py
   ```
   All 37 checks must return `[PASS]`.

6. **Format commit messages:**
   ```bash
   git commit -m "feat(scope): description [generated: <model> | verified: antigravity]"
   ```

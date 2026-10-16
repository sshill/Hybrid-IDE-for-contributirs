# 🏛️ Генеральний Регламент Розробки Hybrid IDE v0.9.5

> [!IMPORTANT]
> **Core Kernel** — єдиний чинний нормативний закон (бюджет ядра ≤ 20 480 байт). Процедури, ліміти й бенчмарки див. у [`docs/knowledge/index/policy_v0.9_reference.md`](file:///home/hills/Documents/docs/knowledge/index/policy_v0.9_reference.md).
> Маніфест: `policy_v0.9.5_manifest.json`. Валідатор: `validate_general_policy.py`. Rollback baseline: `v0.9.4`.

---

## 1. Життєвий цикл: 5 фаз обробки завдань

### Фаза 1: Діагностика (Diagnosis & Research)
- **Безвинятковість:** діє на всі типи запитів (включно з довідковими й беклогом). Багатоетапний обхід директорій заборонено.
- **Phase 1 Status Banner (перша дія в чаті):** домен, індикатор контексту (🟢/🟡/🔴), режим пісочниці, статус Batch Access, цілі.
- **Git & Index First (Check 0):** сліпий обхід (`find_by_name`, `list_dir`, `grep_search`, `ls`/`dir`) заборонено.
  Пайплайн: `git status` + `git log -n 5` ➔ JSON-маніфести `docs/knowledge/index/` ➔ промпт Ollama/Groq ➔ верифікація.
- **Diagnostic Batch Access:** читання Git, Ollama через `diagnostic_runner.py` та `~/.env` авторизовані за замовчуванням.
- **Заборона мовчазного відкату:** якщо пісочниця блокує Ollama, його не підміняють ручним читанням. Запуск ведеться через `diagnostic_runner.py` з `BypassSandbox: true`. Зміни файлів у Фазі 1 заборонені.
- **Видимість аналізу:** обов'язкові картки **[Git Discovery & Surface Analysis]** (знайдені файли) і **[Ollama Context Dispatch Card]** (verbatim-промпт, час інференсу, кількість токенів).
- **Retry & Failover Logging:** при збої, таймауті або перевищенні SLA (30,0 с) публікується `🔁 [RETRY / FAILOVER ATTEMPT #N]` із причиною й текстом повторного запиту.

### Фаза 2: План змін (Proposed Changes Report)
- Артефакт `implementation_plan.md` з `RequestFeedback: true`. Паритет артефакту й чату обов'язковий.
- **Обов'язковий вміст:**
  1. Мета змін.
  2. AI Providers Pre-Flight Routing Matrix (вердикти Tier 1 Ollama і Tier 2 Groq) та RouteLLM Token Forecast.
  3. Пакет змін: `[NEW]`, `[MODIFY]`, `[DELETE]`.
  4. План перевірки.
- **RouteLLM Token Forecast:**

| Параметр | Вимога |
|---|---|
| $N_{\text{in}}$, $N_{\text{out}}$ | оцінка вхідних і вихідних токенів |
| ETC | розрахунковий час виконання |
| SLA | $\text******30{,}0$ с |
| LiteLLM Safe Budget | $B_{\text{safe}} = 0{,}8 \cdot B_{\text{limit}}$ (−20%) |

- **Verbatim Payload Logging:** повний текст промпту, сира відповідь моделі та її архітектурна інтерпретація з якірним посиланням.
- **Генерація контракту Фази 4:** `/tmp/antigravity_phase4_contract.json` (дозволені файли, $N_{\text{files}}$, $N_{\text{tests}}$).

### Фаза 3: Підтвердження та автономія Git (Approval Gate)
- Схвалення плану надає **Batch Execution Access** на Фазу 4.
- **Автономні локальні коміти** дозволені для фіксації прогресу.
- **Протокол схвалення:**

| Сигнал | Назва | Дія |
|---|---|---|
| `+` | Unconditional Batch Approval | Негайний перехід до Фази 4 |
| `+!` | Attention & Corrections Gate | Пауза, картка `⚠️ [ATTENTION GATE: USER CORRECTIONS DETECTED]`, кожна правка підтверджується як `[CONFIRMED & APPLIED]`, дельта фіксується в плані, лише потім Фаза 4 |

- **Заборонено без явного `+`/`+!`:** ⏪ `git reset`/`revert`/`restore`; 🔀 `git merge`/`rebase`; 🌐 `git push origin`/PR.

### Фаза 4: Виконання та звіт по об'єктах (Execution & Status Report)
- Виконання через **Git-First Local Access** строго в межах контракту Фази 2.
- **Dynamic Plan-Aware Step Budget:**
$$A_******bigl(25,\; 4\,N_{\text{files}} + 2\,N_****** + 10\bigr)$$
- **Semantic Loop Gate ($W=4$):** ідентичні дії в ковзному вікні перехоплюються на 2-му повторенні.
- **Plan Divergence Gate:** мутація файлів поза контрактом блокується.
- Оновлення `implementation_plan.md` або `walkthrough.md` скидає історію дій і перераховує бюджет.
- **Circuit Breaker:** 2 послідовні збої ➔ Hard Stop і запит допомоги.
- **Selective Code Guard та Repository Docs Hygiene Gate:** див. §6.2.
- **Code Lifecycle Stepper:** `[1. Синтез]` ➔ `[2. py_compile AST]` ➔ `[3. SLSA-хеш fcntl.flock]` ➔ `[4. Git Commit]` ➔ `[5. Шлюз Арбітра]`.
- У чаті публікується статус кожного зміненого об'єкта.

### Фаза 5: Верифікація та підсумковий звіт
- Тестування працездатності, фінальний `walkthrough.md` із чек-листом.
- **AI Providers Execution & Status Report:** відповіді та статуси всіх залучених моделей (Ollama, Groq, OpenRouter, Antigravity, Copilot, якщо він викликався).
- **Pre-Deployment Arbiter Gate** (лише при авторизованому релізному пуші, перед `push_to_github.sh`):
  - `+` — незалежний арбітраж Tier 4 з `[CODE_AUDIT_REPORT]`;
  - `-` — Fast-Track Push без арбітражу (дрібні правки документації, термінові фікси).
- **Віддалений пуш:** тільки для релізу версії за явної команди розробника. Автоматичний `git push` заборонено.
- Якщо пуш виконано, діють два обов'язкові елементи:
  - **GitHub Actions Live Tracker:** `[1. Push]` ➔ `[2. Trigger]` ➔ `[3. Init]` ➔ `[4. Validate]` ➔ `[5. Report]`.
  - **Remote CI Verification Gate:** декларативне «опубліковано» після самого `git push` заборонено. Обов'язкова перевірка workflow `policy_ci.yml` через GitHub Actions API з Original Provider Report (Run ID, Status, Conclusion, Jobs/Steps) до закриття задачі.

---

## 2. Багаторівнева архітектура ШІ (5-Tier, v0.9.5)

```
[ANTIGRAVITY — ОРКЕСТРАТОР (Tier 0)]  оцінка, 5 фаз, Git-буфер, контроль
  ├── [T1: LOCAL OLLAMA ≤7B]            Primary Workhorse (0$)
  ├── [T2: GROQ LPU & OPENROUTER]       Hardware Fallback Hub (free tier)
  ├── [T3: KNOWLEDGE CACHE]             docs/knowledge/ (Git, без мережі)
  ├── [T4: PRE-IMPLEMENTATION ARBITER]  Antigravity pool / GPT-OSS 120B → [CODE_AUDIT_REPORT]
  └── [T5: FINAL VERDICT]               Antigravity (Golden Standard: HIL, Caprica)
        ⤷ Copilot Heavy-Only Escalation Gate (див. §8.4) — поза рутинним потоком
```

### 2.0 Першість Оркестратора
«Пиляти через Антігравіті зась! Тільки оцінка, запити та контроль.»
- Antigravity веде 5 фаз, читає буфер `git show`, формує промпти.
- Самостійне кодування й правки «від себе» **категорично заборонені**.
- **Zero Inline-Eval Gate:** `python[0-9.]* -c`, `--eval`, `bash -c`, `eval`, `exec` блокуються фізично. Код генерується моделями у файли або через `diagnostic_runner.py --synthesize-script`.
- **Anti-Black-Box Inference:** фіктивні симуляції заборонені. `--synthesize-script` виконує реальний HTTP POST на `http://127.0.0.1:11434/api/generate` і перевіряє `response` ≠ ∅, `eval_count > 0`, `prompt_eval_duration > 0`. SHA256 реєструється у подвійному реєстрі провененсу. Коміт із `[generated: <model>]` без запису в реєстрі блокується.

### 2.1 Tier 1 — Local Edge Ollama (Primary Workhorse)
- Уся первинна робота: синтаксис, функції, diff, AST, PlantUML, синтез скриптів.
- Режим: `Stateless`, `temperature 0.1–0.2`, `num_predict 250..400`, контекст ≤ 3000 токенів.

| Модель | RAM | Умова |
|---|---|---|
| `qwen2.5-coder:1.5b` | ~1,2 ГБ | завжди |
| `qwen2.5-coder:3b` | ~2,2 ГБ | завжди |
| `qwen2.5-coder:7b` | ~4,7 ГБ | вільна RAM ≥ 6 ГБ |

- Моделі ≥ 14B локально **суворо заборонені**.

### 2.2 Tier 2 — Хмарний хаб (Groq & OpenRouter)
- Оверфлоу при контексті > 3000 токенів або для моделей 120B/27B.
- Groq LPU (~460 tok/s, free tier): `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`. OpenRouter: лише `:free`. Ключі беруться з `~/.env`.

### 2.3 Tier 3 — Кеш знань (`docs/knowledge/`)
- Протокол: (1) Local Git & Knowledge First ➔ (2) Absence Verification Gate ➔ (3) Targeted Online Search через Antigravity ➔ (4) Mandatory Knowledge Ingestion у Git.
- Повторний онлайн-пошук при наявності кешу заборонено.

### 2.4 Tier 4 — Pre-Implementation / Pre-Release Arbiter
- За замовчуванням: пул Antigravity (Google AI Studio / Pro) та GPT-OSS 120B (Groq). Результат: `[CODE_AUDIT_REPORT]`.
- Claude Sonnet 5.5 / o1 через Copilot CLI — **лише** за тригерами §8.4.

### 2.5 Tier 5 — Фінальний вердикт Antigravity
- Верифікація бінарників (Caprica, шина 1 мс, HIL), формування `walkthrough.md`, санкція на пуш.

### 2.6 Chat-Screen AI Invocation Visibility
- Кожен виклик моделі публікується віджетом **[AI Invocation Event]**: Провайдер/Модель, Етап, Модуль, Час, Вердикт.
- Результати бойових тестів дублюються в чат і в `implementation_plan.md` / `walkthrough.md`.

### 2.7 Dual-Layer Representation (віджети)
| Шар | Реалізація | Призначення |
|---|---|---|
| **A** | Native Markdown Cards у чаті (емодзі, таблиці, ліміт висоти знято) | Основний канал, надійність 100% |
| **B** | Generative UI HTML Sidecar Artifacts | Повнорозмірні дашборди бічної панелі |

Шар A обов'язковий. Шар B є доповненням і не замінює A.

---

## 3. Контроль домену (Project Scope & Domain Guard)
1. **Ідентифікація:** домен фіксується на старті сесії (*Fallout 4 Modding*, *Antigravity Governance* тощо) і виводиться в Status Banner.
2. **Антизабруднення:** при зміні теми виводиться обов'язкове попередження про зміну домену.

---

## 4. Життєвий цикл контексту (Context Hygiene & Lifespan)
1. **Індикатор навантаження:**

| Індикатор | Кроків | Зона | Дія |
|---|---|---|---|
| 🟢 | ≤ 600 | Оптимальна | Нормальна робота |
| 🟡 | 601–800 | Насичена | Попередження, пріоритет фіксації у Git |
| 🔴 | > 800 або після Фази 5 | Глибока сесія | Фіксація у Tier 3 Git-кеш, підготовка `/bridge` |

2. **Мостовий промпт (`/bridge [версія]`, або автоматично при 🔴):** (1) статус проєкту, коміти, `walkthrough.md`; (2) цільові маніфести `docs/knowledge/index/`; (3) канонічна 3-компонентна формула: тригер `diagnostic_runner.py`, анти-кроулінг `view_file`, контракт віджета `[AI Invocation Event]`.
3. **`/principal`:** профіль [`.agents/skills/principal/SKILL.md`](file:///home/hills/Documents/.agents/skills/principal/SKILL.md). Глибокий аудит (ICD / Protobuf v3, ценз 16 ГБ RAM, Hard Deny Gates). Вихід: `[ARCHITECTURAL VERDICT]` і `[GAP & DISCREPANCY MATRIX]`.
4. **`/reglament`, `/reglamet`:** [`.agents/skills/reglament/SKILL.md`](file:///home/hills/Documents/.agents/skills/reglament/SKILL.md). Phase 1 Status Banner, тест інференсу ШІ, перевірка тулбелту, запуск `validate_general_policy.py`.

---

## 5. Взаємодія з локальною Ollama та апаратний профіль
1. **Призначення:** `qwen2.5-coder` суто для коду (синтаксис, структури, FIM). Чат-запити заборонені.
2. **Профіль машини:** 16 ГБ RAM, Intel Core 3 100U, Intel i915 Graphics. При вільній RAM < 6 ГБ важкі моделі роутяться на Tier 2. Моделі ≥ 14B заборонені.
3. **Параметри:** `Stateless`, `num_predict 250..400`, `temperature 0.2`, ендпоінт `http://127.0.0.1:11434/api/generate`.

---

## 6. Git-First Local Access та залізні шлюзи

### 6.1 Принцип
- Файли й контекст читаються через буфер Git: `git show HEAD:<шлях>`, `git diff`, `git log -n 5`, `git status`. Помилки `Permission denied / no access` виключені.
- Усі дії запускаються через `python3 /home/hills/Documents/.agents/scripts/diagnostic_runner.py ...` (Always Allow).
- У пісочниці заборонені `$(...)`, `curl` та `&&`. Інлайн-код викорінено: генерація через `--synthesize-script`, запуск через `--run`.

### 6.2 OS Hard Deny Gates (`pre_tool_hook.py`)

| # | Шлюз | Дія |
|---|---|---|
| 0 | **Git & Index First** | Блокує сліпий обхід дисків (`ls`/`dir`/`find`) |
| 1 | **Zero Inline-Eval** | Блокує `python -c`, `bash -c`, `eval`, `exec` |
| 2 | **Runtime Circuit Breaker** | Зупиняє ReAct-цикл після 2 послідовних збоїв |
| 3 | **Git Safety** | Блокує `git reset/revert/restore/push/merge/rebase` без дозволу |
| 4 | **Selective Code Guard** | Див. нижче |
| 5 | **Repository Docs Hygiene** | Див. нижче |
| 6 | **Commit Provenance** | Блокує `[generated: <model>]` без запису в реєстрі (`/tmp` та `~/.agents/`) |
| 7 | **Dynamic Plan-Aware Step Budget** | $A_{\max}=\max(25,\,4N_{\text{files}}+2N_{\text{tests}}+10)$ за контрактом Фази 2 |
| 8 | **Semantic Loop Gate** | $W=4$, зупинка на 2-му повторенні |
| 9 | **Plan Divergence Gate** | Забороняє мутацію файлів поза контрактом |

**Selective Code Guard** (`write_to_file`, `replace_file_content`):
- Конфігурації `*.json`, `*.yaml`, `*.yml`, `*.txt`, `.gitignore`, `.cfg`, `.ini`, `.toml` редагуються без тертя.
- Контрольований код (`*.py`, `*.sh`, `*.bash`, `*.ts`, `*.js`, `*.pas`, `*.cpp`, `*.h`, `*.go`) дозволений лише в `scratch/` або з підтвердженим SHA256 у `/tmp/antigravity_provenance_ledger.json`. Інакше виноситься вердикт Hard Deny.

**Repository Docs Hygiene Gate (Правило 2 файлів):**
- Безумовні артефакти життєвого циклу: `walkthrough.md`, `implementation_plan.md` та `/brain/`.
- Репозиторні `*.md` поза цим списком мають бути ≤ 1,5 КБ (хірургічні латки). Більші генеруються моделями Tier 1/2 з реєстрацією провененсу. DIY-копірайтинг заборонений.

### 6.3 Antigravity_Mgr та Symlink Mesh
- Хаб: [`/home/hills/Documents/Antigravity_Mgr/`](file:///home/hills/Documents/Antigravity_Mgr/).
- Toolbelt (`tools/`): `phase1_inspect.py`, `phase2_router.py`, `phase4_provenance.py`, `phase5_verify.py`.
- Symlinks: `.agents/tools` ➔ `Antigravity_Mgr/tools`; `fallaut/Antigravity_Mgr` ➔ `../Antigravity_Mgr`. Змінна `ANTIGRAVITY_MGR_PATH` задається в `.env`.

### 6.4 Host-First Execution
- Пісочниця ізолює мережу (Ollama недоступний) і монтує `.git` як Read-Only. Запуск у пісочниці заборонений.
- `BypassSandbox: true` застосовується одразу до `diagnostic_runner.py`, `Antigravity_Mgr/tools/`, локального Git (`git add`, `git commit`), Caprica та `aplay`.
- Хук тримає білий список префіксів для Always Allow без модальних вікон.

---

## 7. Knowledge Base Protocol
1. **Шлях:** `/home/hills/Documents/docs/knowledge/<категорія>/<назва_теми>.md`.
2. **YAML-шапка:** `title`, `source_url`, `fetched_at`, `domain`, `tags`, `content_hash_sha256`.
3. **Порядок пошуку:** спочатку локально в `docs/knowledge/`. Зовнішній вихід через Antigravity дозволений лише після Absence Verification, з обов'язковим занесенням результату в Git.

---

## 8. Протокол Code-Арбітра та Copilot Heavy-Only Escalation Gate

### 8.1 Запит
Контекст файлу через Git-First Local Access, сигнатури, ТЗ рефакторингу.

### 8.2 Формат `[CODE_AUDIT_REPORT]`
`Engine` · `Syntax Verdict (PASS/WARN/FAIL)` · `Findings` · `Proposed Diff`.

### 8.3 Верифікація Antigravity
`py_compile` (Python), `protoc` (Protobuf ICD), детермінізм 1 мс у HIL, локальний коміт:
`feat(<scope>): <опис> [generated: <code_model> | verified: antigravity]`

### 8.4 Copilot Heavy-Only Escalation Gate
- **Субординація:** первинний аудит, діагностика, щоденні перевірки й синтаксичні дрібниці виконуються **виключно** на токенах Antigravity (Google AI Studio / Pro), Tier 1 Ollama (0$) і Tier 2 Groq LPU. Квоти Copilot на рутину, дрібниці й поодинокі файли не витрачаються.
- **GitHub Copilot CLI (Claude Sonnet 5.5 / o1)** дозволений лише в двох випадках:

| # | Тригер |
|---|---|
| 1 | Негативний вердикт аудиту Antigravity (`FAIL` / `REJECT`) |
| 2 | Пряма задача на монолітний рефакторинг усієї кодової бази під ключ (прапорець `--heavy-refactor`: весь регламент або мод Fallout 4 з деревом Papyrus-залежностей) |

- **Local Git First:** локальні коміти виконуються автономно, щоб зберегти стан проти компакції контексту. Автоматичний `git push` заборонений. Віддалений репозиторій оновлюється лише при релізі великої версії за явної команди розробника (`push_to_github.sh`).
- Маніфест: `copilot_heavy_only_escalation_gate.mode = heavy_refactoring_and_failed_audit_only`, `remote_push_policy = explicit_release_only`.

---

## 9. Policy Inheritance Tenet
1. **Base Kernel:** підпроєкти й доменні каталоги (наприклад, `fallaut/`) є оверлеями, що наслідують цей регламент як обов'язкове системне ядро.
2. **Незмінність бар'єрів:** оверлей може додавати правила рушія чи середовища. Він не може послаблювати 5 фаз циклу, залізні шлюзи `pre_tool_hook.py` (§6.2), Git-First Local Access, Heavy-Only Gate (§8.4) та апаратний ценз 16 ГБ RAM.

---

### Нотатки до рефакторингу
- Прибрано залишки v0.7/v0.8: «Routing Matrix v0.7.1» замінено на безверсійну Pre-Flight Routing Matrix, а `branch: v0.8` у маніфесті варто оновити на `v0.9`.
- Знято суперечність між Tier 4 «Claude Sonnet 5.5» і Heavy-Only Gate: Claude залишається лише за двома тригерами.
- Знято суперечність між Remote CI Gate і забороною автопушу: CI-перевірка діє лише при авторизованому релізі.
- Межі індикатора контексту уточнено: 🟡 = 601–800.
- Файл не збережено на диск і валідатор `validate_general_policy.py` не запускався. Розмір ядра слід звірити з `core_kernel_byte_limit` (20 480 байт) і оновити `core_kernel_current_bytes` у маніфесті.

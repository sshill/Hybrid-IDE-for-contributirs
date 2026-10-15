# 🏛️ Hybrid Agentic IDE: Системна Архітектура та 5-Фазний Пайплайн (v0.9.0)

Цей документ фіксує повну системну архітектуру, математичні моделі та інженерні рішення середовища **Hybrid-IDE-for-contributors**, створеного для залучення розробників до проєкту [fallaut4-STDFUA](https://github.com/sshill/fallaut4-STDFUA) із мінімальними операційними витратами (**Zero Marginal Token Cost**).

---

## 1. 💰 Фінансово-економічний профіль робочого місця (TCO)

Традиційні підходи до розробки з ШІ (Cursor, GitHub Copilot, комерційні API OpenAI/Anthropic) створюють постійний фінансовий бар'єр для контриб'юторів у розмірі \$20–\$300 щомісяця. Архітектура Hybrid IDE усуває ці витрати завдяки чіткому розподілу інференсу між локальним CPU та безкоштовними LPU-квотами:

| Компонент витрат | Тип | Вартість (UAH / EUR) | Опис та роль |
| :--- | :---: | :---: | :--- |
| **Робоча станція / Ноутбук** | CAPEX (одноразово) | **29 000 грн** (~637 €) | Intel Core 3 100U / i5 / Ryzen 5, 16 ГБ RAM, OS **Debian 13 (Trixie) Linux**. Робота без дискретної GPU. |
| **Мережеве підключення** | OPEX (щомісячно) | **300 грн/міс** (~6.6 €) | Стабільний доступ до мережі Інтернет для завантаження Git-зрізів та API Groq. |
| **Ліцензія середовища IDE** | IDE License | Комерційна ліцензія | **Google Antigravity** — перший за черговістю інтелектуальний оркестратор (Tier 0). |
| **Tier 1: Local Edge Ollama** | Token Cost | **0.00 грн / 0.00 $** | `qwen2.5-coder` (1.5B/3B/7B) виконує 80% рутинного кодингу, AST-перевірок та синтаксису локально. |
| **Tier 2: Groq Cloud LPU** | Token Cost | **0.00 грн / 0.00 $** | `openai/gpt-oss-120b` (14 400 RPD / 30 RPM безкоштовно) забезпечує швидкість 460 токенів/с під захистом LiteLLM Safe Budget. |
| **Tier 3: Git Knowledge Cache** | Token Cost | **0.00 грн / 0.00 $** | Локальне кешування знань у `docs/knowledge/` ліквідує повторний веб-пошук. |

---

## 2. 🛡️ Двоконтурна система валідації (Two-Validator Governance)

Система гарантує якість коду та відповідність архітектурним стандартам через два незалежні шлюзи контролю:

1. **Валідатор 1: Antigravity Primary Orchestrator & Policy Validator (Tier 0 & Tier 5)**
   - Здійснює оцінку завдання та структурування 5-фазного пайплайну.
   - Первинна фільтрація виводу провайдерів (Ollama / Groq).
   - Автоматизована перевірка 34 структурних правил регламенту через `validate_general_policy.py` (0.000 с).
   - Формування звіту змін `implementation_plan.md` до внесення першого байту в репозиторій.

2. **Валідатор 2: Claude Sonnet Pre-Implementation Code-Arbiter (Tier 4)**
   - Офіційний релізний Code-Арбітраж (`[CODE_AUDIT_REPORT]`).
   - Залучається суворо перед початком імплементації та релізом онлайн.
   - Перевіряє відсутність архітектурних розривів (радар компетенцій SEI/TOGAF $\ge 80\%$, поточний бал: **93.3%**) та відповідність нормам відкритого коду GitHub.

---

## 3. 🔄 5-Фазний детерміністичний життєвий цикл (The 5-Phase Pipeline)

### Інженерні челенджі та вирішені задачі за фазами:

```
Фаза 1: Діагностика ──► Фаза 2: План і Маршрут ──► Фаза 3: Гейт схвалення ──► Фаза 4: Застосування ──► Фаза 5: Верифікація
  (Git & Index First)    (RouteLLM & Safe Budget)    (Dual Git Policy)          (Zero Inline & Provenance) (34 тести & Multi-AI)
```

### Деталізація інженерних бар'єрів:

#### 🟢 Фаза 1: Діагностика (Diagnosis & Research)
* **Челендж:** Сліпий лінійний перебір файлів дисків (`find_by_name`, `list_dir`, `grep_search`) та спроби виклику `ls -la` у пісочниці, що повертають порожній результат через ізоляцію простору імен і спалюють ліміти токенів.
* **Рішення:** 
  - Імператив **«Git & Index First»**: аналіз починається суворо з `git status`, `git log` та читання готових JSON-маніфестів у `docs/knowledge/index/`.
  - **Hard Deny Gate на `ls` / `dir` у [`core/hooks/pre_tool_hook.py`](core/hooks/pre_tool_hook.py)**: OS-рівневий перехоплювач фізично блокує `ls` / `dir` з кодом повернення 1, направляючи агента на атомарні буфери Git (`git status -sb`, `git ls-files`, `git show HEAD:<файл>`).
  - **Віджет Git Discovery & Запиту контексту в Ollama (Віджет 1):** Публікація картки знайдених об'єктів Git та картки інференсу Ollama із verbatim-текстом промпту.
  - **Фіксація повторів та ретраїв (`🔁 RETRY / FAILOVER LOGGING`):** Якщо запит зазнав невдачі, перевищив квант SLA або впав за таймаутом, обов'язково публікується картка повторного запиту із зазначенням причини та зміненого промпту.
  - Обов'язковий публічний **Phase 1 Status Banner** фіксує контекст і унеможливлює приховані ланцюги викликів. На цій фазі заборонено змінювати робочі файли.

#### 🟢 Фаза 2: Репорт і Маршрутизація (Proposed Changes Report / Plan)
* **Челендж:** Непрозорість дій агента, зависання моделей та вичерпання лімітів запитів (Rate Limits).
* **Рішення:**
  - Обов'язкове формування артефакту `implementation_plan.md` із пре-флайт перевіркою моделей.
  - **Математичний прогноз ваги токенів (Віджет 2):**
    $$\text{Prompt Tokens} = \text{int}(\text{len}(\text{task\_prompt.split}()) \times 1.3) + 150$$
  - **RouteLLM Throughput Dispatcher:** Розрахунок очікуваного часу завершення ($\text{ETC}$):
    $$\text{ETC} = \text{TTFT} + \frac{N_{\text{out}}}{V_{\text{model}}}$$
    * Вивід $\le 60$ токенів: локальна Ollama 7B ($\text{ETC} \le 23.2\text{ с} \le 30.0\text{ с}$ квант SLA).
    * Вивід $\le 250$ токенів: локальна Ollama 1.5B ($\text{ETC} \le 12.8\text{ с} \le 30.0\text{ с}$).
    * Вивід $> 250$ токенів або $N_{\text{prompt}} > 3000$: Groq Cloud LPU ($\text{ETC} \le 1.0 - 2.0\text{ с}$).
  - **Verbatim Payload Logging:** План обов'язково містить повний текст запиту до провайдера, сиру відповідь моделі та її інженерну інтерпретацію в плані з якірним посиланням на цитату.
  - **LiteLLM Safe Budgeting Guard (-20% margin):** Обмеження безкоштовного API Groq до безпечного порогу **6400 TPM** (замість 8000), **800 RPM** та макс. **3200 токенів** на одиничний вивід.
  - **Адаптивний таймаут сокета:** $\text{Timeout} = \max(30, \text{int}(1.5 \times \text{ETC}) + 10)$ замість жорстких 90 с.

#### 🟢 Фаза 3: Підтвердження та Автономія Git (Approval Gate)
* **Челендж:** Випадкова втрата даних через деструктивні відкати (`git reset`, `git revert`), конфлікти злиття або несанкціонований віддалений пуш (`git push origin`).
* **Рішення:**
  - **Dual Git Policy:** Повна автономія локального Git вперед (створення нових версій та локальних комітів без зупинки).
  - **Протокол санкції `+!` (Attention & Corrections Gate — Віджет 3):**
    * `+` — безумовне схвалення плану, прямий перехід до виконання.
    * `+!` — схвалення з обов'язковим врахуванням правок. Агент зупиняється, публікує віджет `⚠️ [ATTENTION GATE: USER CORRECTIONS DETECTED]`, підтверджує взяття в роботу кожної правки (`[CONFIRMED & APPLIED]`) та фіксує дельту змін до Фази 4.
  - Залізний гейт підтвердження: фізичне блокування `git reset`, `git revert`, `git restore`, `git merge`, `git push` без явної згоди користувача («+» чи «+!»).
  - Надання пакетного доступу (Batch Access) на виконання Фази 4.

#### 🟢 Фаза 4: Застосування (Execution & Status Report)
* **Челендж:** Неконтрольоване виконання інлайн-скриптів (`python -c`, `bash -c`), синтаксичні дефекти та нескінченні цикли помилок (Runaway Agent).
* **Рішення:**
  - **Zero Inline-Eval Gate ([`core/hooks/pre_tool_hook.py`](core/hooks/pre_tool_hook.py)):** OS-перехоплювач блокує спроби виконання інлайн-коду з кодом 126.
  - **Візуальний степер життєвого циклу коду (Віджет 4):** Відображення прогресу: `[1. Синтез]` ➔ `[2. py_compile AST]` ➔ `[3. SLSA Хеш]` ➔ `[4. Git Commit]` ➔ `[5. Шлюз Арбітра]`.
  - **Zero-Friction Always Allow Protocol:** Довірені простори (`/home/hills/Documents`, `antigravity/brain`) та канонічні префікси команд виключають шторм модальних запитів `needs_prompt = True`.
  - **FrugalGPT Failover Cascade ([`core/engine/diagnostic_runner.py`](core/engine/diagnostic_runner.py)):** Автоматичне AST-тестування коду, згенерованого локальною Ollama; при `SyntaxError` або обриві сокета виконується безшовний failover на Groq 120B із строгою перевіркою `raw_cloud.startswith("ERROR:")` (усунено хибні збої при генерації коду з рядком `[ERROR]`).
  - **SLSA Session Provenance Ledger ([`core/provenance/phase4_provenance.py`](core/provenance/phase4_provenance.py)):** Реєстрація SHA256 хешів усіх згенерованих файлів; блокування запуску невідстежуваних скриптів.
  - **Step Budget:** Жорсткий ліміт $\le 20$ дій на ітерацію та Circuit Breaker після 2 збоїв.

#### 🟢 Фаза 5: Перевірка функціоналу (Functional Verification Checklist)
* **Челендж:** «Успіх за замовчуванням» (Assumed Correctness) без реального виконання перевірок або приховані помилки провайдерів.
* **Рішення:**
  - **Pre-Deployment Arbiter Gate (`+` / `-`):** Перед викликом `push_to_github.sh` агент зупиняється та пропонує вибір: `+` (запуск незалежного арбітражу Tier 4 Claude Sonnet 5.5 із формуванням `[CODE_AUDIT_REPORT]`) або `-` (Fast-Track Push без арбітражу для дрібних правок документації чи термінових фіксів).
  - **Візуальний трекер операцій Git та GitHub CI (Віджет 5):** Розподілене відображення локальних дій (`git add`, `git commit`) та етапів віддаленого пайплайну (`[Push]` ➔ `[Trigger]` ➔ `[Job Validate]` ➔ `[Report]`).
  - Автоматичний прогін 34 структурних перевірок через `validate_general_policy.py` (34/34 PASS за 0.000 с).
  - Комплексний синтаксичний аудит скриптів через `phase5_verify.py` (12/12 PASS).
  - Генерація підсумкового артефакту `walkthrough.md` із детальним чек-листом.
  - **Multi-Provider Report:** Обов'язкова публікація реальних віджетів інференсу всіх залучених моделей (Ollama, Groq, Claude, Antigravity) на екран чату.

---

## 4. 🧩 Специфікація модулів ядра (`core/` — Zero Dependencies)

1. **[`core/engine/diagnostic_runner.py`](core/engine/diagnostic_runner.py)** — Уніфікована точка входу: перевірка агентів, FrugalGPT-каскад, апаратний ценз RAM ($\ge 6$ GB для 7B, блокування $\ge 14$B на локалі), безпечний парсер `~/.env`, строга валідація помилок `raw_cloud.startswith("ERROR:")`.
2. **[`core/hooks/pre_tool_hook.py`](core/hooks/pre_tool_hook.py) & [`.sh`](core/hooks/pre_tool_hook.sh)** — OS-рівневий перехоплювач викликів інструментів: Hard Deny Gate на `ls`/`dir`, блокування деструктивних команд та інлайн-евалу (код 126).
3. **[`core/router/phase2_router.py`](core/router/phase2_router.py)** — Диспетчер пропускної здатності RouteLLM (SLA 30 с), калькулятор ваги токенів, адаптивний таймаут сокета та LiteLLM Safe Budgeting Guard (-20%).
4. **[`core/provenance/phase4_provenance.py`](core/provenance/phase4_provenance.py)** — Криптографічний сесійний реєстр походження коду SLSA/in-toto з блокуванням `fcntl.flock`.
5. **[`core/inspect/phase1_inspect.py`](core/inspect/phase1_inspect.py)** — Zero-dependency інспектор AST, JSON, XML та DOCX структур без сліпого обходу дисків.
6. **[`core/verify/phase5_verify.py`](core/verify/phase5_verify.py)** — Портативний генератор перевірочних чек-листів та AST-компілятор скриптів.
7. **[`core/verify/verify_remote_ci.py`](core/verify/verify_remote_ci.py)** — Автономний валідатор віддаленого GitHub Actions CI/CD (опитування API, вивід Original Provider Report).
8. **[`core/verify/validate_general_policy.py`](core/verify/validate_general_policy.py)** — 34-точковий валідатор структурних маркерів політики v0.8.3 / v0.9.0.

---

## 5. 🔬 Емпіричні рекорди надійності сесій (Proof of Concept)

- **Сесія `ee6e8ead-ba3b-4489-814f-d04ffdd435d6` (Абсолютний рекорд):** **1225 кроків**, **12.82 діб безперервної роботи**, **15.26 МБ логів**, **236 compaction events**, **0 деструктивних операцій Git**. Народження репозиторію `Hybrid-IDE` (кроки 789–839).
- **Сесія `c80fdbd3-7f36-4550-960c-6ce51de1741d` (Стрес-тест):** **822 кроки**, **5.80 діб**, 100% збереження когнітивної тверезості при компакції контексту.
- **Офіційна сертифікація Tier 4 Claude Sonnet 5.5 Arbiter:** **PASS / APPROVED (93.3% зрілості)**.

👉 Детальні звіти див. у **[`PoC/case_study_session_ee6e8ead_longevity.md`](../../PoC/case_study_session_ee6e8ead_longevity.md)** та **[`PoC/case_study_822_step_stress_test.md`](../../PoC/case_study_822_step_stress_test.md)**.

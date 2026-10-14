---
title: "Antigravity Multi-Tier AI Architecture & Policy Reference Guide (v0.9.0)"
source_url: "local://docs/knowledge/index/policy_v0.9_reference.md"
fetched_at: "2026-10-14T21:05:00"
domain: "Antigravity Governance / Policy Reference"
tags: [policy, v0.9.0, reference, multi-ai, benchmarks, limits, procedures]
content_hash_sha256: "auto"
---

# Antigravity Policy & Multi-Tier AI Architecture: Reference Guide (v0.9.0)

> [!NOTE]
> Цей документ є офіційним супутником компактного ядра [`GEMINI.md`](file:///home/hills/Documents/GEMINI.md).
> Він містить розширені процедурні інструкції, апаратні специфікації, таблиці лімітів хмарних провайдерів, шаблони віджетів та повний опис тулбелту `Antigravity_Mgr`.

---

## 1. Детальний регламент: 5 фаз життєвого циклу

### Фаза 1: Діагностика (Diagnosis & Research)
1. **Принцип «Git & Index First»:**  
   - Перша дія будь-якого розслідування — `git status` та `git log -n 5`.
   - Заборонено здійснювати сліпий обхід файлів (`find_by_name`, `list_dir`, `grep_search`), якщо відповідні структури вже індексовані у [`docs/knowledge/index/`](file:///home/hills/Documents/docs/knowledge/index/).
   - Дослідження виконується через читання цільових JSON-маніфестів або звернення до моделей ШІ через буфер `git show HEAD:<файл>`.
2. **Публічний чекпойнт (Phase 1 Status Banner):**  
   Обов'язкове повідомлення у чаті на старті завдання:
   ```markdown
   > [!NOTE]
   > ### 🛡️ Phase 1 Status Banner
   > - **Зафіксований домен:** [Назва домену]
   > - **Індикатор контексту:** [🟢 / 🟡 / 🔴]
   > - **Режим пісочниці:** [Standard Sandbox / Bypass Sandbox]
   > - **Статус Batch Access:** [Не потрібен / Запитується / Надано]
   > - **Цільові файли / завдання:** [Перелік цільових об'єктів]
   ```
3. **Регламентний пакетний доступ (Diagnostic Batch Access):**  
   Читання Git, локальне опитування Ollama через `diagnostic_runner.py` та читання `~/.env` дозволені регламентом без окремих покрокових дозволів.
4. **Заборона мовчазного відкату:**  
   Якщо звернення до Ollama блокується пісочницею, агент не переходить до ручного читання коду, а фіксує статус ізоляції та використовує `BypassSandbox: true`.

### Фаза 2: Репорт з пакетом змін (Implementation Plan)
1. Створення артефакту `implementation_plan.md` з прапорцем `RequestFeedback: true`.
2. **Паритет чату та артефакту (Artifact & Chat Parity):**  
   Обов'язкове дублювання пре-флайт матриці маршрутизації та віджетів тестування інференсу ШІ (`[AI Invocation Event]`) як у чаті, так і в тексті артефакту.
3. Обов'язкові розділи плану: мета змін, матриця ШІ, пакет змін (із мітками `[NEW]`, `[MODIFY]`, `[DELETE]`), план верифікації з командами.

### Фаза 3: Підтвердження та автономія локального Git (Approval Gate)
1. **Автономія локального Git:** Створення проміжних версій та локальних комітів у гілці задачі дозволено без зупинки, якщо це рух уперед.
2. **Суворі заборони без явної згоди («+»):**  
   - ⏪ Відкати (`git reset`, `git revert`, `git restore`, видалення файлів).
   - 🔀 Злиття (`git merge`, `git rebase`).
   - 🌐 Онлайн-операції (`git push origin`, створення PR на GitHub).

### Фаза 4: Застосування (Execution & Status Report)
1. Виконання узгодженого пакета дій через Git-First Local Access.
2. **Бюджет кроків:** $\le 20$ викликів інструментів на ітерацію. При вичерпанні — проміжний звіт у чат.
3. **Circuit Breaker:** 2 послідовні збої інструменту $\to$ негайний Hard Stop та запит допомоги.

### Фаза 5: Перевірка функціоналу та звіт (Walkthrough & Provider Report)
1. Тестування працездатності (валідація, лінти, компіляція).
2. Створення або оновлення артефакту `walkthrough.md`.
3. Обов'язкове включення фінального звіту статусів усіх залучених провайдерів ШІ.

---

## 2. Апаратні специфікації та бенчмарки заліза

### Робоча станція розробника:
- **Процесор:** Intel Core 3 100U (Raptor Lake Refresh, 6 ядер / 8 потоків: 2 P-ядра до 4.7 ГГц, 4 E-ядра до 3.3 ГГц).
- **Графічний адаптер:** Intel Graphics (i915 driver, інтегрована графіка).
- **Оперативна пам'ять:** 16 ГБ DDR5 (доступно системі: ~15.4 ГБ).

### Бенчмарки локальних моделей Ollama (Stateless Qwen2.5-Coder):

| Модель | Споживання RAM | Швидкість інференсу | HumanEval | Призначення |
| :--- | :---: | :---: | :---: | :--- |
| `qwen2.5-coder:1.5b` | ~1.2 ГБ | 80–110 tok/s | 68.3% | Швидкий синтаксис, regex, точкові скрипти, FIM |
| `qwen2.5-coder:3b` | ~2.2 ГБ | 45–65 tok/s | 76.2% | Проміжний аналіз логіки, валідатори, документація |
| `qwen2.5-coder:7b` | ~4.7 ГБ | 22–32 tok/s | 88.4% | Глибокий аналіз коду, AST, формування патчів та diff |

> [!CAUTION]
> **Апаратне обмеження:** Моделі розміром $\ge 14\text{B}$ на локальній машині **суворо заборонені**.
> Їх завантаження вимагає $> 10$ ГБ RAM, що неминуче виштовхує системні процеси в SWAP і спричиняє зависання ОС Linux.

---

## 3. Специфікації та ліміти хмарних провайдерів (Рівень 2)

### Groq Cloud (LPU Hardware Inference):
- **Призначення:** Аварійний оверфлоу при контексті $> 3000$ токенів або необхідності моделей 120B.
- **Швидкість інференсу:** 350–450 tok/s.
- **Ключові моделі:** `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile`.
- **Безкоштовний ліміт (Free Tier):**
  - Запити на добу (RPD): 14 400.
  - Запити на хвилину (RPM): 30.
  - Токени на хвилину (TPM): до 30 000.

### OpenRouter (Free Tier Hub):
- **Призначення:** Додатковий безкоштовний резервний канал (`:free`).
- **Ключові моделі:** `qwen/qwen-2.5-coder-32b-instruct:free`, `deepseek/deepseek-chat:free`.
- **Ліміти:** Залежать від завантаження публічного пулу, використовуються при збоях Groq.

---

## 4. Канонічні шаблони візуалізації інференсу та аудиту

### Шаблон 1: Віджет інференсу ШІ в чаті (AI Invocation Event)
```markdown
> [!NOTE]
> **Виклик ШІ-моделі (AI Invocation Event):**
> - **Провайдер / Модель:** [Local Ollama / Groq LPU / OpenRouter / Claude Sonnet / GPT-120B]
> - **Етап виклику:** [Чернетка / Експрес-перевірка / Релізний аудит коду]
> - **Цільова функція / модуль:** [Назва об'єкта або скрипта]
> - **Час інференсу:** [X.XX с]
> - **Отриманий вердикт / результат:** [PASS / WARN / FAIL / diff]
```

### Шаблон 2: Висновок релізного Code-Арбітра (Рівень 4)
```markdown
[CODE_AUDIT_REPORT]
- Engine: Claude Sonnet 5.5 | GPT-OSS 120B
- Scope: [Шлях до модуля або перелік функцій]
- Syntax Verdict: PASS | WARN | FAIL
- Determinism & Concurrency: PASS | FAIL
- Findings:
  1. [Опис виявленого дефекту або підтвердження чистоти]
- Proposed Patch / Diff:
  [Готовий уніфікований diff-блок]
- Recommendation: [RELEASE_APPROVED / REVISION_REQUIRED]
```

---

## 5. Модульний тулбелт Antigravity_Mgr (`Antigravity_Mgr/tools/`)

Всі операційні модулі розташовані у [`/home/hills/Documents/Antigravity_Mgr/tools/`](file:///home/hills/Documents/Antigravity_Mgr/tools/):

1. **`phase1_inspect.py`:**
   - Інспекція складних двійкових або структурованих форматів без запуску інтерпретатора.
   - Підтримка аргументів: `--json <файл>`, `--ast <файл>`, `--xml <файл>`, `--docx <файл>`.
2. **`phase2_router.py`:**
   - Аналіз розміру контексту завдання, розрахунок токенів та вибір оптимального провайдера (Ollama 1.5b/7b vs Groq LPU 120B) з урахуванням апаратних лімітів і SLA.
3. **`phase4_provenance.py`:**
   - Сесійний реєстр походження коду.
   - Фіксація SHA-256 хешів згенерованих скриптів у `/tmp/antigravity_provenance_ledger.json`.
   - Захист від тіньового самопалу (Anti-Shadow Gate).
4. **`phase5_verify.py`:**
   - Автоматичний прогін перевірочних скриптів, збір метрик пам'яті, контроль лінтів та валідація політики.

---

## 6. Протокол прямого виконання на хості (Host-First Execution v0.9.0)

1. **Причина використання `BypassSandbox: true`:**
   - Linux-пісочниця Antigravity створює ізольований `Network Namespace`, який блокує доступ до локального сокету `127.0.0.1:11434` (Ollama), викликаючи помилку `Connection Refused`.
   - Каталог `.git` монтується у пісочниці в режимі Read-Only, що блокує `git add` та `git commit`.
2. **Білий список префіксів Always-Allow у `pre_tool_hook.py`:**
   - `python3 /home/hills/Documents/.agents/scripts/diagnostic_runner.py`
   - `python3 /home/hills/Documents/Antigravity_Mgr/tools/`
   - `python3 /home/hills/Documents/.agents/scripts/validate_general_policy.py`
   - `git status`, `git log`, `git add`, `git commit`, `git diff`, `git show`
   - `aplay /usr/share/sounds/`

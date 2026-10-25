# Довідник інструментів та фаз Hybrid-IDE Kernel v0.9.10 (Static Help Cache)

> [!TIP]
> **Призначення:** Статичний кеш довідки для оркестратора та агентів.
> Читати через `view_file`. **Заборонено** запускати командний рядок з `--help` для економії токенів і часу сесії.

---

## 1. Регламент: Канонічні 5 фаз виконання

1. **Фаза 1: Діагностика (Двоканальна)** — лише читання (Канал A: `git status -sb`, `git ls-files`, `view_file`, `phase1_inspect.py`; Канал B: `search_web`, `read_url_content` після Absence Verification). Заборонено `ls`, `find`, `grep_search`.
2. **Фаза 2: Репорт та план** — формування `implementation_plan.md` з повним переліком змін та AI Routing Matrix.
   * **Фаза 2.5: Pre-Approval Gate (Tier 4 Claude Sonnet):** обов'язковий аудит плану (`--sonnet-audit`) перед поданням на схвалення.
3. **Фаза 3: Схвалення користувача** — обов'язкова зупинка (`+` — санкція на Фазу 4, `+!` — Attention Gate, `++` — санкція на реліз у Фазі 5). Фіксація `approved_plan.sha256`.
4. **Фаза 4: Виконання** — Фаза 4.1 Context Assembly, Фаза 4.2 Pre-Check Claude Sonnet (`--sonnet-precheck`), Фаза 4.3 AI Синтез з випуском паспорта (`mint_passport`), Фаза 4.4 Детерміністичний AST гейт і симуляція (`simulate_replacement`), Фаза 4.5 E2E Copilot CLI аудит (`--copilot-audit`) та верифікація ланцюга (`--verify-chain`).
5. **Фаза 5: Верифікація** — Фаза 5.1 Dual-Audit Report, тести `phase5_verify.py` (14 unit + 37/37) та чек-ліст у `walkthrough.md`.

---

## 2. `core/engine/diagnostic_runner.py` (ШІ-інференс та паспорти)

- `--check-agents`: Перевірка зв'язку (Tier 1 Ollama + Tier 2 Groq).
- `--check-all` / `--check-system`: Діагностика середовища.
- `--ollama-query "<промпт>"`: Запит до локальної Ollama (`qwen2.5-coder:1.5b`/:7b).
- `--ollama-audit <файл>`: Локальний Git-First аудит коду.
- `--groq-query "<промпт>"`: Швидкий запит до Groq Cloud LPU (`openai/gpt-oss-120b`).
- `--sonnet-query "<промпт>"`: Прямий запит до Tier 4 Claude Sonnet Arbiter.
- `--sonnet-audit <план>`: Фаза 2.5 Pre-Approval аудит плану.
- `--sonnet-precheck <план>`: Фаза 4.2 Pre-Execution перевірка.
- `--copilot-query "<промпт>"` / `--copilot-audit`: Tier 4.5 Copilot CLI аудит.
- `--copilot-refactor "<промпт>"`: Важкий монолітний рефакторинг (`--heavy-refactor`).
- `--synthesize-script "<ТЗ>" --out <файл>`: Синтез скрипта з випуском паспорта (`MINTED`).
- `--run <скрипт>`: Безпечний запуск скрипта за наявності запису в леджері.

---

## 3. Інструменти життєвого циклу ядра

### `core/inspect/phase1_inspect.py`
- `--telemetry`: Обов'язковий розрахунок 2D-телеметрії (кроки + токени).
- `--ast-inspect <файл>`: Детерміністичний синтаксичний аудит Python AST.

### `core/provenance/phase4_provenance.py`
- `--verify-chain`: Перевірка ланцюга паспортів для змінених файлів git.
- `--verify <файл>`: Перевірка валідності провененсу файлу на диску.
- `--verify-hash <sha256>`: Пошук запису за контрольним хешем.
- `--verify-commit "<коміт>"`: Перевірка відповідності моделі в тексті коміту.

### `core/router/phase2_router.py`
- `--tokens <кількість>`: Оцінка вартості та маршрутизація моделі (Throughput Model).

### `core/verify/phase5_verify.py`
- Локальна детерміністична перевірка: 14 unit-тестів паспортів + 37/37 правил політики.



# 🌐 Open-Source Референси з GitHub: Індустріальні Моделі Маршрутизації (v0.8.3)

Цей документ фіксує перелік та аналіз оригінальних відкритих проєктів і фреймворків із GitHub, архітектурні принципи яких було досліджено та адаптовано у вигляді легковажних zero-dependency модулів у репозиторії **`Hybrid-IDE-for-contributors`**.

---

## 1. Досліджені відкриті проєкти з GitHub

| Проєкт / Організація | Репозиторій на GitHub | Ключова концепція | Що запозичено в Hybrid IDE |
| :--- | :--- | :--- | :--- |
| **`RouteLLM`**<br>(LMSYS / UC Berkeley) | [github.com/lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | Оцінка складності запитів (Threshold Router, Matrix Factorization) для оптимізації вартості між слабкою моделлю (7B) та сильною моделлю (120B/Claude). | Формула Throughput / SLA розрахунку очікуваного часу ($\text{ETC}$) у [`core/router/phase2_router.py`](../../core/router/phase2_router.py): автоматичний вибір моделі на основі квоти виводу токенів. |
| **`LiteLLM Router`**<br>(BerriAI) | [github.com/BerriAI/litellm](https://github.com/BerriAI/litellm) | Уніфіковане проксі з відстеженням рейт-лімітів (RPM/TPM), чергами запитів та динамічним бюджетом. | Концепція **LiteLLM Safe Budgeting (-20% Margin)**: жорсткий поріг 6400 TPM / 800 RPM для Groq Cloud LPU для захисту від блокувань API. |
| **`FrugalGPT`**<br>(Stanford University) | [arxiv.org/abs/2305.05176](https://arxiv.org/abs/2305.05176) | Каскадна маршрутизація (LLM Cascade): запит спочатку надсилається дешевій моделі, якість відповіді валідується, і лише при помилці ескалюється до дорогої моделі. | **FrugalGPT Failover Cascade** у [`core/engine/diagnostic_runner.py`](../../core/engine/diagnostic_runner.py): синтаксична AST-валідація коду локальної Ollama; при `SyntaxError` чи обриві зв'язку — автоматична ескалація на Groq LPU 120B. |
| **`Semantic Router`**<br>(Aurelio Labs) | [github.com/aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router) | Надшвидка семантична класифікація намірів без звернення до важких LLM (нульова затримка). | Евристичний розрахунок маршруту в чистому Python stdlib без додаткових викликів мережі ($< 5$ мс на прийняття рішення). |

---

## 2. Реалізація у коді Hybrid IDE

Усі принципи реалізовано **без важких сторонніх залежностей (Zero-Dep stdlib)** для забезпечення миттєвого старту на будь-якому дистрибутиві Linux без `pip install`:

1. **`core/router/phase2_router.py`**:
   - Розрахунок $\text{ETC} = \text{TTFT} + \frac{N_{\text{out}}}{V_{\text{model}}}$.
   - Дотримання SLA $\le 30.0$ с (на Intel Core 3 100U модель 7B видає ~2.8 tok/s, тому генерації $>60$ токенів ескалюються на Groq LPU 120B).
   - Трекінг безпечного коридору Groq: $\le 6400$ TPM, $\le 3200$ токенів на одиничний вивід.
2. **`core/engine/diagnostic_runner.py`**:
   - Функція `--synthesize-script`: первинна спроба через локальну `qwen2.5-coder` (Tier 1);
   - AST-тестування (`ast.parse`);
   - У разі виявлення `SyntaxError` — автоматичний підхват задачі через Groq LPU (Tier 2).

---

## 3. Як сторонньому розробнику отримати доступ

1. **Локальні моделі:**
   ```bash
   ollama pull qwen2.5-coder:1.5b
   ollama pull qwen2.5-coder:7b
   ```
2. **Хмарний LPU (Groq):**
   - Безкоштовний акаунт на [console.groq.com](https://console.groq.com)
   - Додати ключ у `~/.env`:
     ```bash
     echo 'GROQ_API_KEY="gsk_..."' >> ~/.env
     ```
3. **Запуск валідації:**
   ```bash
   bash setup_and_verify.sh
   ```

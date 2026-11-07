# Google Gemini API & Cloud Project Recovery Profile

## 1. Реєстраційні реквізити проекту
- **Провайдер:** Google AI Studio / Vertex AI
- **Key Alias:** `API Key for my Hybrid IDE`
- **Resource ID:** `projects/270823236470`
- **Project Number:** `270823236470`
- **Змінні оточення:** `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`
- **Збереження секрету:** `~/.env` (mode 0600, поза Git-індексом)

## 2. Архітектурне призначення
- **Рівень:** Tier 4.5 Heavy Failover Gate (1M–2M токенів).
- **Моделі:** `gemini-2.0-flash` (1M tok), `gemini-1.5-pro` (2M tok).
- **Активація:** Автоматичне перемикання при вичерпанні квот Copilot CLI.

## 3. Регламент аварійного відновлення (DR)
У разі перевстановлення ОС чи втрати `~/.env`:
1. Відкрити [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Обрати проєкт `270823236470` (Hybrid IDE) та скопіювати ключ.
3. Додати до `~/.env`:
   ```bash
   GEMINI_API_KEY="<ключ>"
   GOOGLE_API_KEY="<ключ>"
   GOOGLE_CLOUD_PROJECT="270823236470"
   ```
4. Перевірити: `python3 core/enclave/enclave_daemon.py --probe-providers --provider gemini`.

---
name: '🐛 Bug Report'
about: Звіт про помилку у роботі модулів фреймворку (core/, hooks/, verify/, router/)
title: '[BUG]: '
labels: ['bug', 'triage']
assignees: ''
---

### 🔍 Опис дефекту / Bug Description
<!-- Стислий та точний опис проблеми -->

### 🧭 Кроки для відтворення / Steps to Reproduce
1. Виконати команду: `...`
2. Передати аргументи: `...`
3. Спостерігати поведінку: `...`

### 💥 Очікувана vs Фактична поведінка / Expected vs Actual
- **Очікувано:**
- **Фактично:**

### 🖥️ Середовище виконання / Environment
- **ОС:** Debian 13 (Trixie) Linux / Інший дистрибутив Linux
- **Версія Python:** `python3 --version`
- **Локальна модель Ollama:** `qwen2.5-coder:1.5b` / `3b` / `7b`
- **Доступність Groq Cloud LPU:** Так / Ні

### 📜 Діагностичний звіт / Diagnostic Output
- [ ] Вивід команди валідації:
  ```bash
  python3 core/verify/validate_general_policy.py
  ```
- [ ] Вивід скрипта перевірки:
  ```bash
  ./setup_and_verify.sh
  ```

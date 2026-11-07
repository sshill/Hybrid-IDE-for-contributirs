---
name: audit
description: >-
  Audits the current or specified session transcript for strict compliance with
  Hybrid IDE General Execution Policy (Kernel v0.9.12), detects any Phase 1-5 violations,
  and verifies Git Confirmation Gate status via chat_context_auditor.py.
  Triggered by /audit [session_id] or /audit.
---

# 🛡️ Аудит контексту чату на порушення регламенту (/audit) (Kernel v0.9.12)

Ця навичка активується, коли користувач вводить `/audit [session_id]` або `/audit`, просить «перевірити чат на порушення», «провести аудит контексту сесії» або зафіксувати статус перед підтвердженням на Git.

---

## 1. Протокол виконання при виклику `/audit`

### Крок 1: Запуск детерміністичного аудитора
Якщо вказано аргумент ID сесії (наприклад `/audit fc65b454-dbde-4ece-8f3e-d7fbd526c48e`):
```bash
python3 core/verify/chat_context_auditor.py --conversation-id "<session_id>"
```
*(Глобальний fallback: `python3 ~/.gemini/config/plugins/hybrid-ide/bin/chat_context_auditor.py --conversation-id "<session_id>"`)*

Якщо аргумент не вказано (`/audit`):
```bash
python3 core/verify/chat_context_auditor.py --current-session
```

Пакетний аудит усіх тредів / сесій (`/audit all` або `--scan-all`):
```bash
python3 core/verify/chat_context_auditor.py --scan-all
```
*(Аудит останніх N сесій: `python3 core/verify/chat_context_auditor.py --recent-sessions 5`)*


### Крок 2: Інтерпретація звіту та статус Git Confirmation Gate (Фаза 5)
Аудитор детерміністично перевіряє 8 залізних гейтів:
1. **Git-First Discovery Gate:** відсутність сліпих `list_dir`, `find_by_name`, `grep_search`.
2. **2D-Telemetry Initialization Gate:** обов'язковий вимір телеметрії перед створенням плану.
3. **Phase 3 Approval Gate:** заборона мутацій файлів коду до отримання явного схвалення (`+`, `+!`).
4. **Zero Inline-Eval Gate:** повна заборона `python -c`, `bash -c`, `eval`, Here-docs (`<<EOF`).
5. **Shell State Isolation Gate:** заборона шелл-перенаправлень у системні каталоги (`.system_generated`, `core/`, `flags/`, `.secret`).
6. **Secret Isolation Gate:** відсутність спроб несанкціонованого читання HMAC майстер-секретів.
7. **Git Provenance Attribution Gate:** відповідність заявлених у комітах моделей ШІ реальним записам у сесії.
8. **Git State Seal Gate (Фаза 5.2):** обов'язковий локальний `git commit` після будь-яких мутацій коду у Фазі 4 (заборонено залишати репозиторій у незапечатаному стані).

### Крок 3: Вердикт готовності до Фази 5
- Якщо статус **🟢 PASS**: сесія чиста, підтвердження на Git у Фазі 5 дозволено.
- Якщо статус **🔴 FAIL**: зафіксовано порушення на Фазі 4 чи раніше. Коміт та реліз у Фазі 5 автоматично блокуються валідатором `phase5_verify.py`.

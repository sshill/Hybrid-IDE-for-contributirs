# 🛡️ Політика безпеки / Security Policy

[ 🇺🇦 **Українська версія** ](#ukrainian) &nbsp;|&nbsp; [ 🇬🇧 **English Version** ](#english)

---

<a name="ukrainian"></a>
# 🇺🇦 Українська версія

## Підтримувані версії
Безпекові оновлення та виправлення надаються для останньої стабільної версії політики та ядра:

| Версія | Статус підтримки |
| :---: | :---: |
| v0.9.x (v0.9.5) | 🟢 Активна підтримка |
| < v0.9.0 | 🔴 Застаріла |

## Принципи безпеки фреймворку
1. **Захист облікових даних:** Усі ключі API (`GEMINI_API_KEY`, `GROQ_API_KEY`) зберігаються локально у файлі `~/.env` з правами доступу `600`. Файл `~/.env` ніколи не відстежується у Git.
2. **Локальна обробка:** Первинний аналіз файлів, Git-індексація та AST-перевірки виконуються локально без відправлення коду в хмару.
3. **Криптографічний реєстр SLSA:** Усі згенеровані моделями скрипти верифікуються за SHA256 хешами перед виконанням.

## Повідомлення про вразливості
Якщо ви виявили вразливість безпеки, будь ласка, надішліть приватне повідомлення автору ([@sshill](https://github.com/sshill)) або створіть конфіденційний Security Advisory на GitHub.

---

<a name="english"></a>
# 🇬🇧 English Version

## Supported Versions
Security patches and updates are provided for the active release line:

| Version | Support Status |
| :---: | :---: |
| v0.9.x (v0.9.5) | 🟢 Active Support |
| < v0.9.0 | 🔴 Deprecated |

## Framework Security Tenets
1. **Credential Isolation:** API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) are stored in `~/.env` with `600` file permissions and strictly excluded from Git.
2. **Local-First Processing:** Code diagnostics, AST checks, and indexing remain strictly offline on the developer's workstation.
3. **SLSA Provenance Attestation:** All AI-synthesized scripts are cryptographically registered via SHA256 hashes prior to execution.

## Reporting Vulnerabilities
If you discover a security vulnerability, please contact the maintainer ([@sshill](https://github.com/sshill)) privately or submit a confidential Security Advisory via GitHub.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_migration_content.py — Deterministic Migration Content & Bridge Validator (Kernel v0.9.12)

Inspects migration artifacts, bridge prompts, and skill files to ensure they do NOT contain:
1. Anti-regulation circumvention, evasion, or gate-bypass instructions.
2. Directives to use forbidden inline code execution (python -c, bash -c, eval, here-docs, | sh).
3. Directives to write state or flags to /tmp or perform shell redirection into protected dirs.
4. Outdated v0.9.4–v0.9.11 rules or deprecated CLI parameters (--register).
5. Unanchored blind query directives ('найди щось', 'пошукай когось').

Enforces strict Fail-Closed security, line-scoped evaluation, and pre-match negation checking.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True

MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2 MB limit to prevent ReDoS

# Negation prefixes that indicate legitimate descriptions of prohibitions:
# Must strictly precede the pattern within ~45 chars on the SAME line.
NEGATION_PREFIX_PATTERN = re.compile(
    r'(?:заборон\w*|категорично\s+заборон\w*|не\s+(?:використовувати|викликати|створювати|кодити)|'
    r'forbidden|prohibit\w*|never\s+use|disallow\w*|ліквідован\w*|безвинятков\w*|запобіган\w*|'
    r'захист\s+від|блокує|блокувати|відхил\w*|неприпустим\w*)[^\n]{0,45}$',
    re.IGNORECASE
)

# Outdated version claims: specifically v0.9.4 through v0.9.11 as the active target version
OUTDATED_ACTIVE_VERSION_PATTERN = re.compile(
    r'(?:актуальний\s+Регламент|Версія\s+Регламенту:?|Hybrid\s+IDE\s+Policy)\s*[`"\'*]*(?:v?0\.9\.(?:[4-9]|10|11))\b',
    re.IGNORECASE
)

# Deprecated CLI arguments (e.g. phase4_provenance.py --register)
DEPRECATED_CLI_PATTERN = re.compile(
    r'(?:phase4_provenance\.py|diagnostic_runner\.py)[^\n]{0,30}--register\b',
    re.IGNORECASE
)

# Step budget gaming (v0.9.4 obsolete formula used to manipulate limits)
OUTDATED_BUDGET_FORMULA_PATTERN = re.compile(
    r'A_max\s*=\s*max\s*\(\s*25\s*,',
    re.IGNORECASE
)

# Blind unanchored directives as instructions
BLIND_UNANCHORED_DIRECTIVE_PATTERN = re.compile(
    r'\b(?:знайди|найди|пошукай)\s+(?:щось|когось|якогось\s+персонажа)\b',
    re.IGNORECASE
)

# Directives to bypass or disable hooks / gates
HOOK_BYPASS_DIRECTIVE_PATTERN = re.compile(
    r'\b(?:bypass|skip|disable|ignore)\b[^\n]{0,35}\b(?:hook|pre_tool_hook|post_tool_hook|hard\s+gate|gate|check|passport)\b|'
    r'\b(?:обійти|відключити|пропустити|ігнорувати)\b[^\n]{0,35}\b(?:хук\w*|пре_тул\w*|пост_тул\w*|залізний\s+гейт\w*|шлюз\w*|перевірк\w*|провененс\w*|паспорт\w*)\b',
    re.IGNORECASE
)

# Shell inline-eval execution directives
SHELL_INLINE_EVAL_PATTERN = re.compile(
    r'\bpython[0-9.]*\s+-c\s+[\'"]|\bbash\s+-c\s+[\'"]|\b(?:eval|exec)\s*\([^\n]+\)|<<\s*EOF\b|\|\s*(?:sh|bash)\b',
    re.IGNORECASE
)

# Generic state in /tmp directives
TMP_STATE_DIRECTIVE_PATTERN = re.compile(
    r'(?:>\s*|>>\s*|tee\s+(?:-a\s+)?)/tmp/|'
    r'/tmp/(?:[a-zA-Z0-9_\-]*_executed\.flag|antigravity_[a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

# Shell redirection into protected state directories (checked inside code fence / shell contexts)
SHELL_PROTECTED_REDIRECT_PATTERN = re.compile(
    r'(?:>\s*|>>\s*|tee\s+(?:-a\s+)?)(?:[^\s\'"]*/)?(?:\.system_generated/|provenance_ledger|core/)',
    re.IGNORECASE
)


def normalize_content(raw_text: str) -> str:
    """Normalize text using NFKC and strip invisible/formatting characters (category Cf)."""
    normalized = unicodedata.normalize("NFKC", raw_text)
    # Filter out zero-width joiners, soft hyphens, and other format-control characters
    cleaned_chars = [c for c in normalized if unicodedata.category(c) != "Cf"]
    return "".join(cleaned_chars)


def is_negated_line(line_prefix: str) -> bool:
    """Check if the text preceding the pattern on the same line contains a valid negation predicate."""
    return bool(NEGATION_PREFIX_PATTERN.search(line_prefix))


def validate_migration_text(text: str, source_label: str = "inline") -> tuple[bool, list[str]]:
    """
    Pure deterministic validation of migration content.
    Returns (is_valid: bool, violations: list[str]).
    Enforces Fail-Closed behavior: errors or empty input return False.
    """
    if not text or not text.strip():
        return False, [f"[{source_label}] Empty content: Fail-Closed validation triggered."]

    if len(text.encode("utf-8")) > MAX_CONTENT_BYTES:
        return False, [f"[{source_label}] Content exceeds {MAX_CONTENT_BYTES} bytes limit (ReDoS protection)."]

    cleaned = normalize_content(text)
    lines = cleaned.splitlines()
    violations = []

    in_code_fence = False
    fence_lang = ""

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # Track markdown code fences
        if line.startswith("```"):
            if not in_code_fence:
                in_code_fence = True
                fence_lang = line.lstrip("`").strip().lower()
            else:
                in_code_fence = False
                fence_lang = ""
            continue

        # 1. Check Hook Bypass Directives
        m_hook = HOOK_BYPASS_DIRECTIVE_PATTERN.search(raw_line)
        if m_hook:
            prefix = raw_line[:m_hook.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Direct hook/gate bypass instruction: '{m_hook.group(0)}'")

        # 2. Check Shell Inline-Eval Directives
        m_eval = SHELL_INLINE_EVAL_PATTERN.search(raw_line)
        if m_eval:
            prefix = raw_line[:m_eval.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Forbidden inline-eval directive: '{m_eval.group(0)}'")

        # 3. Check /tmp State / Flag Manipulation
        m_tmp = TMP_STATE_DIRECTIVE_PATTERN.search(raw_line)
        if m_tmp:
            prefix = raw_line[:m_tmp.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Forbidden /tmp state or flag manipulation: '{m_tmp.group(0)}'")

        # 4. Check Shell Redirection into Protected State (Only inside shell code fences or shell lines)
        is_shell_context = in_code_fence and fence_lang in ("bash", "sh", "zsh", "shell", "console", "")
        if is_shell_context or any(raw_line.strip().startswith(cmd) for cmd in ("python3", "bash", "sh", "tee", "cat")):
            m_red = SHELL_PROTECTED_REDIRECT_PATTERN.search(raw_line)
            if m_red:
                prefix = raw_line[:m_red.start()]
                if not is_negated_line(prefix):
                    violations.append(f"Line {line_idx}: Shell redirection into protected state: '{m_red.group(0)}'")

        # 5. Check Outdated Active Version Claims (v0.9.4–v0.9.9 claimed as active kernel)
        m_ver = OUTDATED_ACTIVE_VERSION_PATTERN.search(raw_line)
        if m_ver:
            prefix = raw_line[:m_ver.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Outdated active regulation version declaration: '{m_ver.group(0)}'")

        # 6. Check Deprecated CLI Calls (--register)
        m_cli = DEPRECATED_CLI_PATTERN.search(raw_line)
        if m_cli:
            prefix = raw_line[:m_cli.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Deprecated CLI parameter usage: '{m_cli.group(0)}'")

        # 7. Check Outdated Step Budget Formula (v0.9.4)
        m_bg = OUTDATED_BUDGET_FORMULA_PATTERN.search(raw_line)
        if m_bg:
            prefix = raw_line[:m_bg.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Obsolete v0.9.4 step budget formula: '{m_bg.group(0)}'")

        # 8. Check Blind Unanchored Directives ('найди щось')
        m_blind = BLIND_UNANCHORED_DIRECTIVE_PATTERN.search(raw_line)
        if m_blind:
            prefix = raw_line[:m_blind.start()]
            if not is_negated_line(prefix):
                violations.append(f"Line {line_idx}: Blind unanchored search directive: '{m_blind.group(0)}'")

    if violations:
        return False, violations
    return True, []


def validate_migration_file(file_path: str) -> tuple[bool, list[str]]:
    """Validate content of a file on disk (fail-closed on IO/decode errors)."""
    real_path = os.path.realpath(os.path.expanduser(file_path))
    if not os.path.isfile(real_path):
        return False, [f"File not found: {real_path}"]

    try:
        with open(real_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, [f"Error reading file {real_path}: {e}"]

    return validate_migration_text(content, source_label=os.path.basename(real_path))


def generate_canonical_bridge_prompt(workspace_dir: str = None, conv_id: str = None) -> tuple[bool, str]:
    """
    Generates a canonical Kernel v0.9.12 Bridge Prompt and verifies it through the validator.
    Returns (success: bool, prompt_or_error: str).
    Fail-Closed: on any validation failure, returns (False, error) and prints nothing to stdout.
    """
    ws = os.path.realpath(workspace_dir or os.getcwd())
    domain_name = os.path.basename(ws)
    cid = conv_id or os.environ.get("ANTIGRAVITY_CONVERSATION_ID", "<Conversation ID>")

    # Discover git branch and commit safely
    git_branch = "main"
    git_commit = "HEAD"
    try:
        res_b = subprocess.run(["git", "-C", ws, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        if res_b.returncode == 0:
            git_branch = res_b.stdout.strip()
        res_c = subprocess.run(["git", "-C", ws, "log", "-n", "1", "--oneline"], capture_output=True, text=True, timeout=5)
        if res_c.returncode == 0:
            git_commit = res_c.stdout.strip()
    except Exception:
        pass

    walkthrough_cand = os.path.join(ws, "walkthrough.md")
    if not os.path.isfile(walkthrough_cand):
        walkthrough_cand = os.path.expanduser("~/.gemini/antigravity/brain/walkthrough.md")

    prompt = f"""# 🌉 Регламентний старт: 4-Tier аудит ШІ-матриці та інтеграція AGENTS.md (v0.9.12)

## 1. Метадані стану та середовища
- **Версія Регламенту:** `v0.9.12` (Trusted Enclave Architecture, Multi-Tier AI Gateway, 2D-Telemetry, Phase 5.2 Git State Seal Gate)
- **Домен:** `{domain_name}` (`{ws}`)
- **Parent Conversation ID:** `{cid}`
- **Active Git Branch:** `{git_branch}` (коміт `{git_commit}`)
- **Чинне Конституційне ядро:** `~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md`
- **Доменний оверлей проєкту:** `{ws}/AGENTS.md` (всі файли `GEMINI.md` утилізовано)
- **Попередній Walkthrough:** [`walkthrough.md`](file://{walkthrough_cand})

---

## 2. Імперативний стартовий протокол (Strict Step-by-Step Gate)

### 🛑 Крок 1: Phase 1 Status Banner та 2D-телеметрія контексту
Виконати динамічний вимір метрик (`core/enclave/enclave_daemon.py --telemetry` або `core/inspect/phase1_inspect.py --telemetry`) та вивести обов'язковий статус:
`🎯 [DOMAIN: {domain_name} | HOST: Linux/Debian]`
`<Індикатор 🟢/🟡/🔴> [CONTEXT: <S> кроків (~<tok>k tok) | SANDBOX: Host-First BypassSandbox | BATCH ACCESS: Authorized]`
*(Обов'язково вивести віджет `[CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]` у чат!)*

### 🛑 Крок 2: Бойова перевірка ШІ-матриці через Довірений Анклав
Виконати єдиною пакетною командою (`BypassSandbox: true`):
`python3 core/enclave/enclave_daemon.py --battle-test`
*(Перевіряє Tier 1 Ollama 1.5b, Tier 2 Groq 120b, Tier 4 Claude Sonnet 3.5 та Tier 4.5 Copilot CLI probe)*

### 🛑 Крок 3: Лог інтеграції плагіна та доменного оверлею
Сформувати та вивести структурований звіт:
```text
======================================================================
📦 [PLUGIN & OVERLAY INTEGRATION LOG]
======================================================================
[Step 1: Global Plugin Discovery]
  - Шлях плагіна:   ~/.gemini/config/plugins/hybrid-ide/
  - Маніфест:       plugin.json (v1.0.0, Kernel v0.9.12)
  - Хуки безпеки:   hooks.json (PreToolUse OS Gates v0.9.12, PostToolUse Breaker, Stop)
  - Статус хуків:   🟢 Активно (єдиний глобальний обробник)

[Step 2: Constitutional Kernel Audit]
  - Файл ядра:      rules/AGENTS.md (Kernel v0.9.12)
  - OS Hard Gates:  Zero Inline-Eval, Shell State Isolation, Cryptographic Hash Passports, In-Memory Simulation
  - Дисципліна:     5 обов'язкових фаз, Anchored Grounding Gate, Anti-Echo Protocol

[Step 3: Domain Overlay Resolution & Core Policies]
  - Файл оверлею:   {ws}/AGENTS.md
  - 5 фаз Анклаву:  1.Діагностика (телеметрія) -> 2.План -> 2.5.Pre-Approval (Claude Sonnet / Attest) -> 3.Схвалення (+/++) -> 4.1.Context Assembly -> 4.2.Pre-Check (Sonnet) -> 4.3.Синтез Анклавом (FrugalGPT Ollama 1.5b/3b/7b, Groq 120B overflow, Anti-Echo, HMAC Schema 1.2) -> 4.4.AST & Compile Gate -> 4.5.Pre-Release Arbiter (Copilot CLI -> Failover на Claude Sonnet) -> 5.Верифікація (40 unit + 10 auditor + 37/37)
  - Двогейтовий суверенітет: '+' для локальних змін/коміту; '++' для релізу/пушу
  - Zero-SHA:       Антігравіті суворо заборонено самостійно обчислювати хеші чи випускати паспорти

[Step 3.1: Tool Catalog & Satellite Interfaces]
  - Головні інструменти Анклаву (core/enclave/enclave_daemon.py):
    * POST /apply (--target, --task | --direct-code) — атомарний синтез/патч
    * POST /query (--query) — суверенний мульти-Tier ШІ-шлюз (FrugalGPT & Failover)
    * GET /battle-test (--battle-test) — бойовий 4-Tier тест
    * GET /telemetry (--telemetry) — 2D-телеметрія сесії та RAM
    * GET /help (--help-tools) — схема та параметри контрактів
    * GET /verify-chain (--verify-chain) — верифікація ланцюга паспортів
    * POST /attest (--attest-arbiter) — атестаційний гейт Antigravity Pool
  - Супутні та зовнішні інтерфейси:
    * LinkedIn Developer API: OAuth 2.0 у ~/.env (LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI)
    * Email & SMTP нотифікації: системні сповіщення та релізи
    * Контрактний довідник: core/enclave/ENCLAVE_INTERFACE.md (читання через view_file)
    * Верифікатор: core/verify/phase5_verify.py (40 unit + 37/37 перевірок)

[Step 3.2: Anchored Instrumental Requests Protocol]
  - Обов'язкова звірка з ENCLAVE_INTERFACE.md або --help-tools перед запитом
  - Тільки параметризовані виклики (target_path, task_prompt, direct_code, patch_target, start_line, end_line, mode, tier)

[Step 4: Decoupling & Binding Verdict]
  - Статус GEMINI:  🚫 Декупловано з підпроєктів (файли GEMINI.md вичищено)
  - Вердикт:        ✅ Ядро та доменний оверлей успішно зв'язано в активний контекст
======================================================================
```

### 🛑 Крок 4: Стан Git та перехід до Фази 1
Перевірити `git status -sb` та `git log -n 3 --oneline`. Зчитати попередній `walkthrough.md` та перейти до виконання завдань за 5-фазним регламентом.

> [!CAUTION]
> Доки Кроки 1–3 не виконано на 100% (PASS) з публікацією віджетів інференсу для всіх провайдерів, агенту категорично заборонено змінювати бойовий код!
"""

    ok, violations = validate_migration_text(prompt, source_label="generated_canonical_bridge")
    if not ok:
        return False, f"Validation of generated bridge prompt failed: {', '.join(violations)}"
    return True, prompt


def audit_skills(repo_root: str = None) -> tuple[bool, dict]:
    """Audit all repository and global skills for compliance."""
    root = Path(repo_root or os.getcwd())
    results = {}
    all_clean = True

    skill_files = []
    # Repo skills
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for s in skills_dir.glob("**/SKILL.md"):
            skill_files.append(s)

    # Global skills
    global_skills_dir = Path.home() / ".gemini" / "config" / "skills"
    if global_skills_dir.is_dir():
        for s in global_skills_dir.glob("**/SKILL.md"):
            if s not in skill_files:
                skill_files.append(s)

    for sf in skill_files:
        ok, violations = validate_migration_file(str(sf))
        results[str(sf)] = {"valid": ok, "violations": violations}
        if not ok:
            all_clean = False

    return all_clean, results


def main():
    parser = argparse.ArgumentParser(description="Deterministic Migration Content Validator (Kernel v0.9.12)")
    parser.add_argument("--file", type=str, help="Path to file to validate against anti-regulation directives")
    parser.add_argument("--audit-skills", action="store_true", help="Audit all skills in repo and global configuration")
    parser.add_argument("--generate-bridge", action="store_true", help="Generate and validate canonical Bridge Prompt (fail-closed)")
    parser.add_argument("--workspace", type=str, default=None, help="Workspace directory for bridge generation")

    args = parser.parse_args()

    if args.generate_bridge:
        ok, prompt_or_err = generate_canonical_bridge_prompt(args.workspace)
        if not ok:
            print(f"❌ FAIL-CLOSED: {prompt_or_err}", file=sys.stderr)
            sys.exit(1)
        print(prompt_or_err)
        sys.exit(0)

    if args.audit_skills:
        print("🔍 Початок аудиту навичок на наявність інструкцій протидії регламенту...")
        all_clean, results = audit_skills()
        for path, res in results.items():
            if res["valid"]:
                print(f"  🟢 PASS: {path}")
            else:
                print(f"  🔴 FAIL: {path}")
                for v in res["violations"]:
                    print(f"     ⚠️ {v}")
        if not all_clean:
            print("\n❌ Виявлено порушення у навичках!", file=sys.stderr)
            sys.exit(1)
        print("\n✅ Усі навички успішно пройшли валідацію протидії регламенту!")
        sys.exit(0)

    if args.file:
        ok, violations = validate_migration_file(args.file)
        if ok:
            print(f"🟢 PASS: '{args.file}' не містить інструкцій протидії регламенту.")
            sys.exit(0)
        else:
            print(f"🔴 FAIL: '{args.file}' містить заборонені інструкції або застарілий контент:", file=sys.stderr)
            for v in violations:
                print(f"  ⚠️ {v}", file=sys.stderr)
            sys.exit(1)

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()

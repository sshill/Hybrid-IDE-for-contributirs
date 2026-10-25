#!/usr/bin/env python3
import sys
import os
import json
import time

# Prevent creation of .pyc files
sys.dont_write_bytecode = True

def _write_file(path, content=""):
    """Write content to a file, ensuring the directory exists."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to write file '{path}': {e}")

def _sanitize_conv_id(conv_id: str) -> str:
    """Sanitize conversation ID to prevent path traversal."""
    if not conv_id:
        return "default_conversation"
    clean = os.path.basename(str(conv_id).strip("/\\"))
    if not clean or clean in (".", ".."):
        return "default_conversation"
    clean = "".join(c for c in clean if c.isalnum() or c in ("-", "_", "."))
    return clean or "default_conversation"

def _resolve_brain_state_dir(artifact_dir, conversation_id):
    """
    Resolve the brain state directory (.system_generated) with strict path traversal checks.
    """
    brain_root = os.path.realpath(os.path.expanduser("~/.gemini/antigravity/brain"))
    if artifact_dir:
        real_art = os.path.realpath(artifact_dir)
        if real_art == brain_root or real_art.startswith(brain_root + os.sep):
            return os.path.join(real_art, ".system_generated")
    clean_id = _sanitize_conv_id(conversation_id)
    return os.path.join(brain_root, clean_id, ".system_generated")

def _create_telemetry_flags(brain_state_dir):
    """Create telemetry flag files in the brain state directory (.system_generated/flags) and /tmp."""
    telemetry_path = os.path.join(brain_state_dir, "telemetry.flag")
    flags_dir = os.path.join(brain_state_dir, "flags")
    flags_json = os.path.join(flags_dir, "telemetry.json")
    tmp_path = "/tmp/antigravity_telemetry_inspected.flag"
    payload = json.dumps({"timestamp": time.time(), "status": "auto_initialized"})
    _write_file(telemetry_path, payload)
    _write_file(flags_json, payload)
    _write_file(tmp_path, payload)

def _detect_registered_workspaces():
    """Знаходить локальні Git-репозиторії у ~/Documents з обмеженням часу та виключенням симлінків."""
    repos = []
    docs_dir = os.path.expanduser("~/Documents")
    if os.path.isdir(docs_dir):
        try:
            for item in sorted(os.listdir(docs_dir)):
                candidate = os.path.join(docs_dir, item)
                if os.path.isdir(candidate) and not os.path.islink(candidate):
                    if os.path.isdir(os.path.join(candidate, ".git")):
                        repos.append(candidate)
        except Exception:
            pass
    return repos

def _resolve_repo_root(path):
    """Визначає корінь репозиторію для шляху (підтримує робочі підкаталоги)."""
    if not path or not os.path.exists(path):
        return None
    curr = os.path.abspath(path)
    home = os.path.expanduser("~")
    while curr and curr != home and curr != os.path.dirname(curr):
        if os.path.isdir(os.path.join(curr, ".git")):
            return curr
        curr = os.path.dirname(curr)
    return None

def _build_injection(workspace_paths=None):
    """Створює адаптивне повідомлення авто-старту відповідно до воркспейсу."""
    home = os.path.expanduser("~")
    clean_wps = [os.path.abspath(p) for p in (workspace_paths or []) if p and os.path.exists(p)]

    # Визначаємо, чи сесія ненав'язана (порожня або вказує на $HOME)
    is_unattached = not clean_wps or all(p == home for p in clean_wps)

    repo_root = None
    if not is_unattached:
        for wp in clean_wps:
            root = _resolve_repo_root(wp)
            if root:
                repo_root = root
                break

    overlay_info = "AGENTS.md"
    warning_banner = ""

    if is_unattached:
        known_repos = _detect_registered_workspaces()
        repos_list = "\n".join(f"  • {r}" for r in known_repos) if known_repos else "  • ~/Documents/<project>"
        warning_banner = (
            "⚠️ [УВАГА: Сесія відкрита без прив'язки до репозиторію (Cwd: ~)]:\n"
            "Поточний робочий каталог є домашньою директорією користувача і НЕ є репозиторієм Git.\n"
            "Для уникнення помилок 'fatal: not a git repository' у Фазі 1 (Діагностика):\n"
            "• Вказуйте параметр Cwd або використовуйте 'git -C <шлях>' до цільового проєкту:\n"
            f"{repos_list}\n"
            "• Не використовуйте ls/find (заблоковані OS Hard Gate), читайте стан через git.\n\n"
        )
    elif repo_root:
        overlay_file = os.path.join(repo_root, "AGENTS.md")
        if os.path.isfile(overlay_file):
            overlay_info = f"{repo_root}/AGENTS.md (активний доменний оверлей)"
        else:
            overlay_info = f"{repo_root} (оверлей AGENTS.md відсутній, діє лише Конституційне ядро)"

    guidance = (
        f"{warning_banner}"
        "⚡ [HYBRID-IDE KERNEL v0.9.9 AUTO-START]:\n"
        "Сесію ініціалізовано. Регламент діє автоматично:\n"
        "• Конституційне ядро: ~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md\n"
        f"• Проєктний оверлей: {overlay_info}\n"
        "• Фаза 1: Діагностика (лише читання; заборонено ls/find/grep, використовувати git та індекси)\n"
        "• Фаза 2: Репорт та implementation_plan.md\n"
        "• Фаза 2.5: Pre-Approval Gate — аудит плану через Tier 4 Claude Sonnet (--sonnet-audit)\n"
        "• Фаза 3: Схвалення користувача (+, +!, ++)\n"
        "• Фаза 4.1: Pre-Execution Context Assembly (Оркестратор Antigravity, view_file, zero-shell)\n"
        "• Фаза 4.2: Pre-Check Audit Gate через Claude Sonnet (--sonnet-precheck)\n"
        "• Фаза 4.3: Синтез коду моделями ШІ (Ollama / Groq) з реєстрацією у SLSA Provenance Ledger\n"
        "• Фаза 4.4: Детерміністичний синтаксичний та компіляційний гейт (AST, py_compile, Caprica Wine 10)\n"
        "• Фаза 4.5: Повний E2E аудит через GitHub Copilot CLI (--copilot-audit)\n"
        "• Фаза 5.1: Dual-Audit Report (Claude Sonnet + Copilot CLI) та phase5_verify.py (37/37)\n"
        "Глобальні канонічні інструменти ядра (працюють з будь-якого каталогу):\n"
        "  - python3 ~/.gemini/config/plugins/hybrid-ide/bin/diagnostic_runner.py (ШІ-інференс Tier 1/2/4/4.5)\n"
        "  - python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase1_inspect.py (--telemetry, 2D контекст)\n"
        "  - python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase4_provenance.py (--register, --verify, SLSA)\n"
        "  - python3 ~/.gemini/config/plugins/hybrid-ide/bin/phase5_verify.py (верифікація 37/37)\n"
        "У репозиторії Hybrid-IDE інструменти також доступні локально в core/."
    )
    return {
        "injectSteps": [
            {
                "ephemeralMessage": guidance
            }
        ]
    }

def main():
    try:
        raw_input = sys.stdin.read()
        try:
            payload = json.loads(raw_input) if raw_input.strip() else {}
        except json.JSONDecodeError:
            payload = {}

        if not isinstance(payload, dict):
            payload = {}

        try:
            invocation_num = int(payload.get("invocationNum", 1))
        except (TypeError, ValueError):
            invocation_num = 1

        conversation_id = str(payload.get("conversationId") or "default_conversation")
        artifact_dir = payload.get("artifactDirectoryPath")
        workspace_paths = payload.get("workspacePaths", [])

        brain_state_dir = _resolve_brain_state_dir(artifact_dir, conversation_id)
        os.makedirs(brain_state_dir, exist_ok=True)

        telemetry_flag_path = os.path.join(brain_state_dir, "telemetry.flag")
        if invocation_num == 1 or not os.path.exists(telemetry_flag_path):
            _create_telemetry_flags(brain_state_dir)

        if invocation_num == 1:
            output = _build_injection(workspace_paths)
        else:
            output = {}

        json.dump(output, sys.stdout, ensure_ascii=False)
        sys.stdout.flush()
    except Exception as exc:
        # Fail-open: write warning to stderr, output empty dict, exit 0 to prevent chat disruption
        try:
            sys.stderr.write("Warning in pre_invocation_hook (fail-open): {}\n".format(str(exc)))
            json.dump({}, sys.stdout)
            sys.stdout.flush()
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()

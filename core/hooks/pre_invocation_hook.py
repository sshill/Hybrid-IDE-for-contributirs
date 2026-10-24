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
    """Create telemetry flag files in the brain state directory and /tmp."""
    telemetry_path = os.path.join(brain_state_dir, "telemetry.flag")
    tmp_path = "/tmp/antigravity_telemetry_inspected.flag"
    _write_file(telemetry_path, json.dumps({"timestamp": time.time(), "status": "auto_initialized"}))
    _write_file(tmp_path, json.dumps({"timestamp": time.time(), "status": "auto_initialized"}))

def _build_injection():
    """Construct the injection payload for the first invocation."""
    guidance = (
        "⚡ [HYBRID-IDE KERNEL v0.9.9 AUTO-START]:\n"
        "Сесію ініціалізовано для воркспейсу. Регламент діє автоматично:\n"
        "• Конституційне ядро: ~/.gemini/config/plugins/hybrid-ide/rules/AGENTS.md\n"
        "• Проєктний оверлей: AGENTS.md (Hybrid IDE Core & Contributor Overlay v0.9.9)\n"
        "• Фаза 1: Діагностика (лише читання; заборонено ls/find/grep, використовувати git та індекси)\n"
        "• Фаза 2: Репорт та implementation_plan.md\n"
        "• Фаза 2.5: Pre-Approval Gate — аудит плану через Tier 4 Claude Sonnet (--sonnet-audit)\n"
        "• Фаза 3: Схвалення користувача (+, +!, ++)\n"
        "• Фаза 4.1: Збірка контексту та Pre-Check через Claude Sonnet (--sonnet-precheck)\n"
        "• Фаза 4.3: Синтез коду моделями ШІ (Ollama / Groq) з реєстрацією у SLSA Provenance Ledger\n"
        "• Фаза 4.5: Повний E2E аудит через GitHub Copilot CLI (--copilot-audit)\n"
        "• Фаза 5.1: Dual-Audit Report (Claude Sonnet + Copilot CLI) та phase5_verify.py (37/37)\n"
        "Інструменти ядра доступні за шляхами:\n"
        "  - core/engine/diagnostic_runner.py (ШІ-інференс Tier 1/2/4/4.5, --check-agents)\n"
        "  - core/inspect/phase1_inspect.py (--telemetry, 2D контекст)\n"
        "  - core/provenance/phase4_provenance.py (--register, --verify, SLSA леджер)\n"
        "  - core/verify/phase5_verify.py (верифікація 37/37)\n"
        "Глобальні копії інструментів: ~/.gemini/config/plugins/hybrid-ide/bin/ та .agents/scripts/."
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
        # workspacePaths is read but not used in current logic
        # workspace_paths = payload.get("workspacePaths", [])

        brain_state_dir = _resolve_brain_state_dir(artifact_dir, conversation_id)
        os.makedirs(brain_state_dir, exist_ok=True)

        telemetry_flag_path = os.path.join(brain_state_dir, "telemetry.flag")
        if invocation_num == 1 or not os.path.exists(telemetry_flag_path):
            _create_telemetry_flags(brain_state_dir)

        if invocation_num == 1:
            output = _build_injection()
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

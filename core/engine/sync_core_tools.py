#!/usr/bin/env python3
"""
Скрипт синхронізації утиліт, хуків та навичок ядра Hybrid-IDE (Kernel v0.9.12).
Синхронізує бінарні модулі з core/ до глобального плагіна (~/.gemini/config/plugins/hybrid-ide/bin)
та локальних хабів (.agents/scripts, Antigravity_Mgr/tools),
а також системні навички до ~/.gemini/config/skills/ з автоматичним бекапом.
"""
import argparse
import hashlib
import os
import shutil
import stat
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CORE_FILES = [
    # Core Engine & Enclave
    REPO_ROOT / "core" / "enclave" / "enclave_daemon.py",
    REPO_ROOT / "core" / "engine" / "diagnostic_runner.py",
    REPO_ROOT / "core" / "engine" / "validate_migration_content.py",
    REPO_ROOT / "core" / "inspect" / "phase1_inspect.py",
    REPO_ROOT / "core" / "provenance" / "phase4_provenance.py",
    REPO_ROOT / "core" / "router" / "phase2_router.py",
    REPO_ROOT / "core" / "verify" / "phase5_verify.py",
    REPO_ROOT / "core" / "verify" / "chat_context_auditor.py",
    REPO_ROOT / "core" / "verify" / "verify_remote_ci.py",
    REPO_ROOT / "core" / "verify" / "validate_general_policy.py",
    # Core Lifecycle Hooks
    REPO_ROOT / "core" / "hooks" / "pre_invocation_hook.py",
    REPO_ROOT / "core" / "hooks" / "pre_invocation_hook.sh",
    REPO_ROOT / "core" / "hooks" / "pre_tool_hook.py",
    REPO_ROOT / "core" / "hooks" / "pre_tool_hook.sh",
    REPO_ROOT / "core" / "hooks" / "post_tool_hook.py",
    REPO_ROOT / "core" / "hooks" / "post_tool_hook.sh",
    REPO_ROOT / "core" / "hooks" / "stop_hook.sh",
]

TARGET_DIRS = [
    Path.home() / ".gemini" / "config" / "plugins" / "hybrid-ide" / "bin",
    Path.home() / "Documents" / ".agents" / "scripts",
    Path.home() / "Documents" / "Antigravity_Mgr" / "tools",
]

WHITELISTED_SKILLS = ["bridge", "reglament", "principal", "supervisor", "audit"]

SKILL_TARGET_DIRS = [
    Path.home() / ".gemini" / "config" / "skills",
    Path.home() / ".gemini" / "config" / "plugins" / "hybrid-ide" / "skills",
]


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sync(dry_run: bool = False):
    print(f"🔄 Початок синхронізації інструментів ядра Hybrid-IDE Kernel v0.9.12{' (DRY-RUN)' if dry_run else ''}...")
    synced_count = 0

    # 1. Синхронізація Core Files у bin-каталоги
    for target_dir in TARGET_DIRS:
        if not target_dir.parent.exists() and "plugins" not in str(target_dir):
            continue
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📂 Цільова директорія інструментів: {target_dir}")

        for src in CORE_FILES:
            if not src.exists():
                print(f"  ⚠️ Пропущено (не знайдено): {src.name}")
                continue
            dst = target_dir / src.name
            if dst.exists() and file_sha256(src) == file_sha256(dst):
                print(f"  ⏩ Без змін (хеш ідентичний): {src.name}")
                continue

            if not dry_run:
                shutil.copy2(src, dst)
                current_perms = os.stat(dst).st_mode
                os.chmod(dst, current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"  ✅ Синхронізовано: {src.name}")
            synced_count += 1

    # 2. Синхронізація навичок (skills) з резервним копіюванням
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    for s_target_dir in SKILL_TARGET_DIRS:
        if not s_target_dir.parent.exists() and "plugins" not in str(s_target_dir):
            continue
        print(f"\n🧩 Цільова директорія навичок: {s_target_dir}")

        for skill_name in WHITELISTED_SKILLS:
            src_skill = REPO_ROOT / "skills" / skill_name / "SKILL.md"
            if not src_skill.exists():
                continue
            dst_skill_dir = s_target_dir / skill_name
            dst_skill = dst_skill_dir / "SKILL.md"

            if dst_skill.exists() and file_sha256(src_skill) == file_sha256(dst_skill):
                print(f"  ⏩ Без змін (хеш ідентичний): {skill_name}/SKILL.md")
                continue

            if not dry_run:
                # Безпечний бекап перед перезаписом
                if dst_skill.exists():
                    bak_dir = Path.home() / ".gemini" / "config" / f"skills.bak-{timestamp}" / skill_name
                    bak_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst_skill, bak_dir / "SKILL.md")

                dst_skill_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_skill, dst_skill)
            print(f"  ✅ Синхронізовано навичку: {skill_name}/SKILL.md")
            synced_count += 1

    print(f"\n🎉 Синхронізацію успішно завершено! Оновлено {synced_count} об'єктів.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Core tools and skills synchronizer (Kernel v0.9.12)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sync without modifying disk")
    args = parser.parse_args()
    return sync(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

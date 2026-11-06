#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.dont_write_bytecode = True

"""
Фаза 4: Сесійний реєстр провененсу та Anti-Shadow Execution Gate.
Шлях: core/provenance/phase4_provenance.py
Стандарт: SLSA / in-toto Cryptographic Attestation (Zero-Dep stdlib).
Гарантує, що жоден виконуваний скрипт не підкинуто в обхід моделей ШІ.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import time
import uuid

SCHEMA_VERSION = "1.2"
V0_9_11_CUTOVER_TIMESTAMP = 1793050000.0

GENERATIVE_MODELS_ALLOWLIST = {
    "qwen2.5-coder:1.5b": 1,
    "qwen2.5-coder:3b": 1,
    "qwen2.5-coder:7b": 1,
    "openai/gpt-oss-120b": 2,
    "gpt-oss-120b": 2,
    "claude-3-5-sonnet-20241022": 4,
    "claude-3.5-sonnet": 4,
    "copilot-cli": 4.5,
}

RESERVED_TTL_SECONDS = 120.0

def resolve_persistent_ledger_path() -> str:
    if "HYBRID_IDE_LEDGER" in os.environ:
        return os.environ["HYBRID_IDE_LEDGER"]
    plugin_ledger = os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/.provenance_ledger.json")
    agents_ledger = os.path.expanduser("~/Documents/.agents/.provenance_ledger.json")
    if os.path.exists(os.path.dirname(agents_ledger)):
        return agents_ledger
    return plugin_ledger

PERSISTENT_LEDGER_PATH = resolve_persistent_ledger_path()

def resolve_brain_state_dir() -> str:
    """Визначає персистентний Brain-First каталог стану сесії."""
    if "HYBRID_IDE_BRAIN_DIR" in os.environ and os.path.isdir(os.environ["HYBRID_IDE_BRAIN_DIR"]):
        sg = os.path.join(os.environ["HYBRID_IDE_BRAIN_DIR"], ".system_generated")
        os.makedirs(sg, exist_ok=True)
        return sg
    brain_root = os.path.expanduser("~/.gemini/antigravity/brain")
    if os.path.exists(brain_root):
        try:
            cands = [os.path.join(brain_root, d) for d in os.listdir(brain_root) if os.path.isdir(os.path.join(brain_root, d))]
            if cands:
                cands.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                sg = os.path.join(cands[0], ".system_generated")
                os.makedirs(sg, exist_ok=True)
                return sg
        except Exception:
            pass
    return None

def resolve_brain_ledger_path() -> str:
    """Визначає персистентний Brain-First шлях леджера провененсу."""
    sg = resolve_brain_state_dir()
    if sg:
        return os.path.join(sg, "provenance_ledger.json")
    return None

def resolve_brain_flags_dir() -> str:
    """Визначає персистентний Brain-First каталог прапорців сесії."""
    sg = resolve_brain_state_dir()
    if sg:
        fd = os.path.join(sg, "flags")
        os.makedirs(fd, exist_ok=True)
        return fd
    return None

def get_file_sha256(path: str) -> str:
    """Обчислення SHA256 хешу файлу."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_content_sha256(content: str) -> str:
    """Обчислення SHA256 хешу текстового рядка."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def simulate_replacement(
    content_bytes: bytes,
    target_bytes: bytes,
    replacement_bytes: bytes,
    start_line: int = None,
    end_line: int = None,
    allow_multiple: bool = False
) -> tuple[bool, bytes, str]:
    """
    Єдина детерміністична байтова симуляція інструмента replace_file_content.
    Повертає (success: bool, simulated_bytes: bytes, error_message: str).
    """
    if not target_bytes:
        return False, b"", "TargetContent cannot be empty"

    if start_line is not None and end_line is not None:
        lines = content_bytes.splitlines(keepends=True)
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            return False, b"", f"Invalid line range [{start_line}, {end_line}] for file with {len(lines)} lines"

        slice_bytes = b"".join(lines[start_line - 1:end_line])
        if target_bytes not in slice_bytes:
            return False, b"", "TargetContent not found in specified line range"

        count = slice_bytes.count(target_bytes)
        if not allow_multiple and count != 1:
            return False, b"", f"TargetContent occurs {count} times in line range (expected 1)"

        new_slice = slice_bytes.replace(target_bytes, replacement_bytes, -1 if allow_multiple else 1)
        res = b"".join(lines[:start_line - 1]) + new_slice + b"".join(lines[end_line:])
        return True, res, "OK"
    else:
        if target_bytes not in content_bytes:
            return False, b"", "TargetContent not found in file content"

        count = content_bytes.count(target_bytes)
        if not allow_multiple and count != 1:
            return False, b"", f"TargetContent occurs {count} times in file (expected 1)"

        res = content_bytes.replace(target_bytes, replacement_bytes, -1 if allow_multiple else 1)
        return True, res, "OK"

def _get_master_secret_path() -> str:
    if "HYBRID_IDE_MASTER_SECRET" in os.environ:
        return os.environ["HYBRID_IDE_MASTER_SECRET"]
    return os.path.expanduser("~/.gemini/antigravity/.core_master_hmac.secret")

def _get_or_create_master_hmac_secret() -> bytes:
    """
    Отримання або ініціалізація майстер-ключа HMAC.
    Зберігається у ~/.gemini/antigravity/.core_master_hmac.secret з правами 0600.
    Захист від race condition через O_CREAT | O_EXCL та перевірка прав батьківського каталогу.
    """
    secret_path = _get_master_secret_path()
    parent_dir = os.path.dirname(secret_path)

    if os.path.exists(parent_dir):
        try:
            st = os.stat(parent_dir)
            if st.st_mode & 0o022:
                try:
                    os.chmod(parent_dir, 0o700)
                    st = os.stat(parent_dir)
                except OSError:
                    pass
            if (st.st_mode & 0o002) and hasattr(os, "getuid") and st.st_uid != os.getuid():
                raise PermissionError(
                    f"Parent directory {parent_dir} is world-writable by other users (mode {oct(st.st_mode)}, UID {st.st_uid}). "
                    "Refusing to load/store master secret."
                )
        except OSError as e:
            raise PermissionError(f"Failed to stat secret parent dir {parent_dir}: {e}")
    else:
        os.makedirs(parent_dir, mode=0o700, exist_ok=True)

    if os.path.isfile(secret_path):
        st = os.stat(secret_path)
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            raise PermissionError(f"Secret file {secret_path} is owned by UID {st.st_uid}, expected {os.getuid()}. Refusing to load.")
        if (st.st_mode & 0o077) != 0:
            try:
                os.chmod(secret_path, 0o600)
            except OSError:
                raise PermissionError(f"Secret file {secret_path} has insecure permissions {oct(st.st_mode)} and cannot be chmodded to 0600.")
        with open(secret_path, "rb") as f:
            secret = f.read().strip()
            if not secret:
                raise ValueError(f"Secret file {secret_path} is empty.")
            return secret
    else:
        new_secret = os.urandom(32).hex().encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(secret_path, flags, 0o600)
            with open(fd, "wb") as f:
                f.write(new_secret)
                f.flush()
                os.fsync(f.fileno())
            return new_secret
        except FileExistsError:
            with open(secret_path, "rb") as f:
                return f.read().strip()

def derive_session_key(session_id: str) -> bytes:
    """Деривація сесійного ключа з майстер-ключа: HMAC(MasterKey, session_id)."""
    clean_sess = str(session_id or "").strip()
    if not clean_sess:
        raise ValueError("Invalid session_id: cannot derive session key for empty or missing session_id")
    master_key = _get_or_create_master_hmac_secret()
    return hmac.new(master_key, clean_sess.encode("utf-8"), hashlib.sha256).digest()

def compute_passport_hmac(passport: dict) -> str:
    """
    Розрахунок криптографічного HMAC-SHA256 підпису паспорта за канонічним JSON (Schema 1.2).
    Покриває всі критичні поля: schema_version, passport_id, session_id, file_path,
    baseline_sha256, target_sha256, model, tier, status, created_at_us, reserved_at_us,
    reserved_by_tool, applied_at_us, metrics.
    """
    session_id = str(passport.get("session_id") or "").strip()
    session_key = derive_session_key(session_id)

    created_at = passport.get("created_at") or 0.0
    reserved_at = passport.get("reserved_at") or 0.0
    applied_at = passport.get("applied_at") or 0.0

    canonical_payload = json.dumps({
        "schema_version": SCHEMA_VERSION,
        "passport_id": passport.get("passport_id", ""),
        "session_id": session_id,
        "file_path": passport.get("file_path", ""),
        "baseline_sha256": passport.get("baseline_sha256") or "",
        "target_sha256": passport.get("target_sha256", ""),
        "model": passport.get("model", ""),
        "tier": passport.get("tier", 1),
        "status": passport.get("status", "MINTED"),
        "created_at_us": int(round(created_at * 1_000_000)),
        "reserved_at_us": int(round(reserved_at * 1_000_000)) if reserved_at else 0,
        "reserved_by_tool": passport.get("reserved_by_tool") or "",
        "applied_at_us": int(round(applied_at * 1_000_000)) if applied_at else 0,
        "metrics": passport.get("metrics") or {}
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    return hmac.new(session_key, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest()

def verify_passport_hmac(passport: dict) -> tuple[bool, str]:
    """
    Перевірка HMAC-підпису паспорта (Schema 1.2).
    Fail-closed: якщо паспорт у секції passports не має підпису або підпис не збігається,
    він безумовно відхиляється.
    """
    sig = passport.get("signature")
    session_id = str(passport.get("session_id") or "").strip()

    if not session_id:
        return False, "COUNTERFEIT_PASSPORT: Missing or empty session_id"

    try:
        master_key = _get_or_create_master_hmac_secret()
        has_local_master = True
    except PermissionError as e:
        return False, f"SECURITY_ERROR: {e}"
    except Exception:
        has_local_master = False

    if not sig:
        return False, "COUNTERFEIT_PASSPORT: Missing HMAC signature on passport"

    if not has_local_master:
        return False, "CANNOT_VERIFY: Master key missing in local environment"

    expected_sig = compute_passport_hmac(passport)
    if hmac.compare_digest(sig, expected_sig):
        return True, "HMAC_VERIFIED"
    else:
        return False, "SIGNATURE_MISMATCH: Passport tamper-evidence triggered"

def get_canonical_lock_path() -> str:
    """Визначає єдиний канонічний шлях блокування реєстру провененсу."""
    if "HYBRID_IDE_LEDGER" in os.environ:
        return os.environ["HYBRID_IDE_LEDGER"] + ".lock"
    brain_state = resolve_brain_state_dir()
    if brain_state:
        return os.path.join(brain_state, ".provenance_ledger.lock")
    return os.path.expanduser("~/.gemini/antigravity/.provenance_ledger.lock")

def _load_ledger_unlocked() -> dict:
    """Внутрішнє завантаження реєстру (без взяття власного блокування)."""
    ledger = {"schema_version": SCHEMA_VERSION, "passports": {}, "legacy_files": {}}
    loaded_any = False

    targets = []
    if "HYBRID_IDE_LEDGER" in os.environ:
        targets.append(os.environ["HYBRID_IDE_LEDGER"])
    else:
        brain_ledger = resolve_brain_ledger_path()
        if brain_ledger:
            targets.append(brain_ledger)
        persistent_path = resolve_persistent_ledger_path()
        if persistent_path not in targets:
            targets.append(persistent_path)

    for path in targets:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "passports" in data or "legacy_files" in data:
                            ledger.update(data)
                        else:
                            ledger["legacy_files"].update(data)
                        loaded_any = True
                        break
            except json.JSONDecodeError as e:
                corrupt_backup = f"{path}.corrupt.{int(time.time())}"
                try:
                    shutil.copy2(path, corrupt_backup)
                except Exception:
                    pass
                raise ValueError(
                    f"Corrupt ledger JSON at {path} ({e}). "
                    f"Backed up to {corrupt_backup}. Aborting to prevent state loss."
                )
            except Exception as e:
                raise e

    return ledger

def _save_ledger_unlocked(ledger: dict):
    """Внутрішнє атомарне збереження реєстру (без взяття власного блокування)."""
    if "HYBRID_IDE_LEDGER" in os.environ:
        targets = [os.environ["HYBRID_IDE_LEDGER"]]
    else:
        targets = []
        brain_ledger = resolve_brain_ledger_path()
        if brain_ledger:
            targets.append(brain_ledger)
        persistent_path = resolve_persistent_ledger_path()
        if persistent_path not in targets:
            targets.append(persistent_path)

    for path in targets:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = path + f".tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"⚠️ Попередження: не вдалося зберегти реєстр у {path}: {e}", file=sys.stderr)

@contextmanager
def locked_ledger():
    """
    Канонічний атомарний контекстний менеджер для циклу read-modify-write.
    Захоплює fcntl.flock(LOCK_EX) на весь життєвий цикл операції з леджером.
    """
    lock_path = get_canonical_lock_path()
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            ledger = _load_ledger_unlocked()
            yield ledger
            _save_ledger_unlocked(ledger)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)

def load_ledger() -> dict:
    """Read-only завантаження реєстру з безпечним lock."""
    lock_path = get_canonical_lock_path()
    if os.path.exists(lock_path):
        try:
            with open(lock_path, "w") as lock_f:
                fcntl.flock(lock_f, fcntl.LOCK_SH)
                try:
                    return _load_ledger_unlocked()
                finally:
                    fcntl.flock(lock_f, fcntl.LOCK_UN)
        except Exception:
            pass
    return _load_ledger_unlocked()

def save_ledger(ledger: dict):
    """Синхронне збереження реєстру під ексклюзивним lock."""
    lock_path = get_canonical_lock_path()
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            _save_ledger_unlocked(ledger)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)

def mint_passport(
    session_id: str,
    file_path: str,
    baseline_sha256: str,
    target_sha256: str,
    model: str,
    tier: int = None,
    metrics: dict = None
) -> str:
    """Випуск активного криптографічного паспорта (MINTED) для передачі коду між фазами."""
    if model not in GENERATIVE_MODELS_ALLOWLIST:
        raise ValueError(
            f"Model '{model}' is not in GENERATIVE_MODELS_ALLOWLIST. "
            f"Only generative models {list(GENERATIVE_MODELS_ALLOWLIST.keys())} can mint passports."
        )

    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        raise ValueError("Cannot mint passport: session_id is required and cannot be empty.")

    resolved_tier = GENERATIVE_MODELS_ALLOWLIST[model] if tier is None else tier
    real_path = os.path.realpath(os.path.abspath(file_path))
    passport_id = f"pass_{uuid.uuid4().hex[:16]}"

    passport = {
        "passport_id": passport_id,
        "schema_version": SCHEMA_VERSION,
        "session_id": clean_session_id,
        "file_path": real_path,
        "baseline_sha256": baseline_sha256,
        "target_sha256": target_sha256,
        "model": model,
        "tier": resolved_tier,
        "metrics": metrics or {},
        "created_at": time.time(),
        "status": "MINTED",
        "reserved_at": None,
        "reserved_by_tool": None,
        "applied_at": None,
        "signature": None
    }
    passport["signature"] = compute_passport_hmac(passport)

    with locked_ledger() as ledger:
        passports = ledger.setdefault("passports", {})
        passports[passport_id] = passport

    print(f"🎫 [PASSPORT MINTED] ID: {passport_id} for {os.path.basename(real_path)} (target: {target_sha256[:16]}..., model: {model})")
    return passport_id

def reserve_passport(
    session_id: str,
    file_path: str,
    baseline_sha256: str,
    target_sha256: str,
    tool_name: str
) -> tuple[bool, str, str]:
    """Резервування паспорта перед виконанням інструмента (pre_tool_hook)."""
    real_path = os.path.realpath(os.path.abspath(file_path))
    clean_session_id = str(session_id or "").strip()
    if not clean_session_id:
        return False, "", "Cannot reserve passport: session_id is required"

    now = time.time()
    with locked_ledger() as ledger:
        passports = ledger.setdefault("passports", {})

        # Скидання протермінованих RESERVED (TTL 120s) назад у MINTED з перепідписом!
        for p_id, p in passports.items():
            if p.get("status") == "RESERVED":
                res_at = p.get("reserved_at") or 0
                if (now - res_at) > RESERVED_TTL_SECONDS:
                    p["status"] = "MINTED"
                    p["reserved_at"] = None
                    p["reserved_by_tool"] = None
                    p["signature"] = compute_passport_hmac(p)

        # Пошук валідного паспорта
        for p_id, p in passports.items():
            if p.get("file_path") == real_path:
                p_target = p.get("target_sha256")
                p_base = p.get("baseline_sha256")
                status = p.get("status")

                if p_target == target_sha256:
                    if status == "APPLIED":
                        return False, p_id, "Passport already APPLIED (replay prevention)"
                    elif status == "FAILED":
                        return False, p_id, "Passport is FAILED (must re-synthesize code in Phase 4.3)"

                    if baseline_sha256 is not None and p_base is not None and p_base != baseline_sha256:
                        continue

                    if p.get("session_id") != clean_session_id:
                        return False, p_id, f"SESSION_MISMATCH: Passport belongs to session {p.get('session_id')}, requested by {clean_session_id}"

                    if status == "MINTED":
                        ok_sig, sig_msg = verify_passport_hmac(p)
                        if not ok_sig:
                            return False, p_id, f"COUNTERFEIT_PASSPORT: {sig_msg}"

                        p["status"] = "RESERVED"
                        p["reserved_at"] = now
                        p["reserved_by_tool"] = tool_name
                        p["signature"] = compute_passport_hmac(p)
                        return True, p_id, f"Passport {p_id} RESERVED for {tool_name}"

    return False, "", f"No valid MINTED passport found for {os.path.basename(real_path)} with target SHA256 {target_sha256[:16]}..."

def apply_passport(session_id: str, file_path: str) -> tuple[bool, str]:
    """Підтвердження фактичної зміни на диску та фіксація статусу APPLIED (post_tool_hook)."""
    real_path = os.path.realpath(os.path.abspath(file_path))
    if not os.path.isfile(real_path):
        return False, f"Target file does not exist on disk: {real_path}"

    disk_hash = get_file_sha256(real_path)
    clean_session_id = str(session_id or "").strip()

    with locked_ledger() as ledger:
        passports = ledger.setdefault("passports", {})
        target_passport = None
        for p_id, p in passports.items():
            if p.get("file_path") == real_path and p.get("status") == "RESERVED":
                target_passport = p
                break

        if not target_passport:
            return False, f"No RESERVED passport found for {os.path.basename(real_path)}"

        if clean_session_id and target_passport.get("session_id") != clean_session_id:
            return False, f"SESSION_MISMATCH: Passport belongs to session {target_passport.get('session_id')}, apply requested by {clean_session_id}"

        ok_sig, sig_msg = verify_passport_hmac(target_passport)
        if not ok_sig:
            target_passport["status"] = "FAILED"
            target_passport["applied_at"] = time.time()
            target_passport["signature"] = compute_passport_hmac(target_passport)
            return False, f"FORGERY_DETECTED: RESERVED passport signature invalid: {sig_msg}"

        expected_target = target_passport.get("target_sha256")
        if disk_hash == expected_target:
            target_passport["status"] = "APPLIED"
            target_passport["applied_at"] = time.time()
            target_passport["signature"] = compute_passport_hmac(target_passport)
            print(f"✅ [PASSPORT APPLIED] {target_passport.get('passport_id')} for {os.path.basename(real_path)} verified on disk")
            return True, f"OK: disk matches target {disk_hash[:16]}..."
        else:
            target_passport["status"] = "FAILED"
            target_passport["applied_at"] = time.time()
            target_passport["signature"] = compute_passport_hmac(target_passport)
            print(f"🔴 [PASSPORT FAILED] Disk hash {disk_hash[:16]} does not match expected {expected_target[:16]}", file=sys.stderr)
            return False, f"FAILED: disk hash mismatch (disk: {disk_hash[:16]}, expected: {expected_target[:16]})"

def plan_authorizes(file_path: str, repo_path: str = None) -> tuple[bool, str]:
    """
    Єдиний детерміністичний авторизатор Contributor Mode.
    Перевіряє, що approved_plan.sha256 збігається з implementation_plan.md
    та цільовий файл явно перерахований у плані.
    Повністю виключає перевірку назви каталогу (is_contributor_repo).
    """
    brain_state = resolve_brain_state_dir()
    if not brain_state:
        return False, "Brain state directory not found"

    approved_sha_path = os.path.join(brain_state, "approved_plan.sha256")
    plan_path = os.path.join(os.path.dirname(brain_state), "implementation_plan.md")

    if not os.path.isfile(approved_sha_path) or not os.path.isfile(plan_path):
        return False, "Missing approved_plan.sha256 or implementation_plan.md"

    try:
        with open(plan_path, "rb") as pf:
            current_plan_sha = hashlib.sha256(pf.read()).hexdigest()
        with open(approved_sha_path, "r", encoding="utf-8") as af:
            approved_plan_sha = af.read().strip()

        if current_plan_sha != approved_plan_sha:
            return False, f"Plan hash mismatch (current: {current_plan_sha[:8]}, approved: {approved_plan_sha[:8]})"

        cwd = repo_path or os.getcwd()
        abs_target = os.path.realpath(os.path.abspath(file_path))
        try:
            rel_target = os.path.relpath(abs_target, cwd)
        except ValueError:
            rel_target = abs_target

        base_target = os.path.basename(abs_target)

        with open(plan_path, "r", encoding="utf-8") as pf:
            plan_text = pf.read()

        patterns = [
            rf"\[(?:MODIFY|NEW|DELETE)\]\s+.*?(?:`|/){re.escape(base_target)}`?",
            rf"`{re.escape(rel_target)}`",
            rf"`{re.escape(abs_target)}`",
            rf"\(file://[^\)]*{re.escape(base_target)}\)",
            rf"\b{re.escape(rel_target)}\b"
        ]
        for pat in patterns:
            if re.search(pat, plan_text):
                return True, f"File authorized by approved plan ({approved_plan_sha[:8]})"

        return False, f"File {rel_target} not listed in approved implementation_plan.md"
    except Exception as e:
        return False, f"Error validating plan authorization: {e}"

def verify_chain(session_id: str = None, repo_path: str = None) -> tuple[bool, str, list]:
    """Аудит ланцюга паспортів для Фази 4.5 (Copilot CLI) та Фази 5.1 (Commit Gate)."""
    cwd = repo_path or os.getcwd()
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            capture_output=True,
            timeout=15
        )
        if res.returncode != 0:
            return False, f"git status failed: {res.stderr.decode('utf-8', errors='replace')}", []
    except subprocess.TimeoutExpired:
        return False, "git status timed out after 15s (fail-closed)", []
    except Exception as e:
        return False, f"Error running git: {e}", []

    raw = res.stdout
    entries = raw.split(b"\0")
    ledger = load_ledger()
    passports = ledger.get("passports", {})
    verified = []
    unverified = []

    code_exts = (".py", ".sh", ".bash", ".ts", ".js", ".psc", ".pas", ".cpp", ".h", ".go", ".rs")

    idx = 0
    while idx < len(entries):
        entry = entries[idx]
        idx += 1
        if not entry:
            continue
        try:
            status_code = entry[:2].decode("utf-8")
            path_bytes = entry[3:]
        except Exception:
            continue

        if status_code.startswith("R") or status_code.startswith("C"):
            if idx < len(entries):
                new_path_bytes = entries[idx]
                idx += 1
                rel_path = new_path_bytes.decode("utf-8", errors="replace")
            else:
                rel_path = path_bytes.decode("utf-8", errors="replace")
        else:
            rel_path = path_bytes.decode("utf-8", errors="replace")

        abs_p = os.path.realpath(os.path.join(cwd, rel_path))
        if not any(abs_p.endswith(ext) for ext in code_exts):
            continue

        if not os.path.isfile(abs_p):
            continue

        disk_hash = get_file_sha256(abs_p)
        matched = False
        for p_id, p in passports.items():
            if p.get("file_path") == abs_p and p.get("status") == "APPLIED":
                if p.get("target_sha256") == disk_hash:
                    ok_sig, sig_msg = verify_passport_hmac(p)
                    if not ok_sig:
                        print(f"⚠️ [FORGERY REJECTED] Passport {p_id} for {rel_path} has invalid signature: {sig_msg}", file=sys.stderr)
                        continue
                    matched = True
                    verified.append({"path": rel_path, "passport_id": p_id, "model": p.get("model")})
                    break

        if not matched:
            ok_auth, auth_msg = plan_authorizes(abs_p, cwd)
            if ok_auth:
                matched = True
                verified.append({
                    "path": rel_path,
                    "passport_id": "contributor_plan",
                    "model": "contributor-mode (approved_plan)"
                })

        if not matched:
            unverified.append(rel_path)

    if unverified:
        return False, f"Unverified code files without APPLIED passport: {', '.join(unverified)}", unverified
    return True, f"All {len(verified)} modified code files have valid APPLIED passports", verified

def register_provenance(
    script_path: str,
    model: str = "qwen2.5-coder:1.5b",
    sha256_hash: str = None,
    source_prompt: str = None,
    eval_count: int = None,
    prompt_eval_duration_ms: float = None
) -> bool:
    """Реєстрація хешу та метаданих ШІ-синтезу в сесійному та персистентному реєстрі."""
    abs_path = os.path.abspath(script_path)
    if sha256_hash is None:
        if not os.path.isfile(abs_path):
            print(f"❌ Файл для реєстрації не знайдено: {abs_path}", file=sys.stderr)
            return False
        sha256_hash = get_file_sha256(abs_path)

    is_ollama_model = any(k in model.lower() for k in ("qwen", "llama", "coder", "deepseek", "mistral", "gemma", "ollama"))
    if is_ollama_model:
        has_metrics = (eval_count is not None and eval_count > 0 and 
                       prompt_eval_duration_ms is not None and prompt_eval_duration_ms > 0)
        has_valid_flag = False
        flag_p = "/tmp/antigravity_ollama_synthesized.flag"
        if os.path.exists(flag_p):
            try:
                if (time.time() - os.path.getmtime(flag_p)) < 900:
                    with open(flag_p, "r", encoding="utf-8") as f_fl:
                        if abs_path in f_fl.read():
                            has_valid_flag = True
            except Exception:
                pass

        if not (has_metrics or has_valid_flag):
            print(
                f"❌ [HARD REJECT] Фальсифікація провененсу виявлена!\n"
                f"   Спроба зареєструвати файл {os.path.basename(abs_path)} за моделлю '{model}' без реального інференсу.\n"
                f"   Відсутні обов'язкові поля eval_count / prompt_eval_duration_ms або активний сесійний прапорець генерації.\n"
                f"   Код має генеруватися через канонічний раннер: diagnostic_runner.py --synthesize-script",
                file=sys.stderr
            )
            return False

    entry = {
        "sha256": sha256_hash,
        "model": model,
        "registered_at": time.time(),
        "path": abs_path
    }
    if source_prompt is not None:
        entry["source_prompt"] = source_prompt
    if eval_count is not None:
        entry["eval_count"] = eval_count
    if prompt_eval_duration_ms is not None:
        entry["prompt_eval_duration_ms"] = prompt_eval_duration_ms

    try:
        with locked_ledger() as ledger:
            legacy = ledger.setdefault("legacy_files", {})
            legacy[abs_path] = entry

        valid_text = f"PROVENANCE_VALID: {abs_path} at {time.time()} by {model}\n"
        sg = resolve_brain_state_dir()
        if sg:
            try:
                with open(os.path.join(sg, "provenance_valid.flag"), "w", encoding="utf-8") as bf:
                    bf.write(valid_text)
            except Exception:
                pass
        try:
            with open("/tmp/antigravity_provenance_valid.flag", "w", encoding="utf-8") as flag_f:
                flag_f.write(valid_text)
        except Exception:
            pass

        print(f"🔒 [PROVENANCE REGISTERED] Файл {os.path.basename(abs_path)} зареєстровано (SHA256: {sha256_hash[:16]}..., Model: {model})")
        return True
    except Exception as e:
        print(f"❌ Помилка запису в реєстр провененсу: {e}", file=sys.stderr)
        return False

def verify_provenance(script_path: str) -> tuple[bool, str]:
    """Верифікація цілісності та походження скрипта перед виконанням (Schema 1.2 + Legacy)."""
    abs_path = os.path.realpath(os.path.abspath(script_path))
    if not os.path.isfile(abs_path):
        return False, f"Файл не існує: {abs_path}"

    current_hash = get_file_sha256(abs_path)
    ledger = load_ledger()

    # 1. Спершу перевіряємо криптографічні паспорти Schema 1.2
    passports = ledger.get("passports", {})
    for p_id, p in passports.items():
        p_path = os.path.realpath(os.path.abspath(p.get("file_path", "")))
        if p_path == abs_path and p.get("status") == "APPLIED":
            expected_hash = p.get("target_sha256")
            if current_hash != expected_hash:
                return False, f"Порушення цілісності: хеш на диску ({current_hash[:16]}...) не збігається із зареєстрованим у паспорті {p_id} ({str(expected_hash)[:16]}...)"
            ok_sig, sig_msg = verify_passport_hmac(p)
            if not ok_sig:
                return False, f"Підробка паспорта {p_id}: невалідний HMAC підпис ({sig_msg})"
            return True, f"OK (Passport: {p_id}, Model: {p.get('model')}, Tier: {p.get('tier')})"

    # 2. Фолбек на застарілий формат Schema 1.0/1.1 (legacy_files)
    legacy = ledger.get("legacy_files", {})
    record = legacy.get(abs_path)
    if record:
        if current_hash != record.get("sha256"):
            return False, f"Порушення цілісності: хеш на диску ({current_hash[:16]}...) не збігається із зареєстрованим ШІ ({record.get('sha256', '')[:16]}...)"
        return True, f"OK (Legacy Record, Model: {record.get('model')})"

    return False, f"Файл не зареєстровано в сесійному реєстрі ШІ-генерації: {abs_path}"

def verify_content_sha256(sha256_hash: str) -> tuple[bool, str, dict]:
    """Пошук відповідності контенту за SHA256 хешем у сесійному/персистентному реєстрі (Schema 1.2 + Legacy)."""
    if not sha256_hash:
        return False, "Порожній хеш для перевірки.", {}

    ledger = load_ledger()

    # 1. Перевірка паспортів Schema 1.2
    passports = ledger.get("passports", {})
    for p_id, p in passports.items():
        if p.get("target_sha256") == sha256_hash and p.get("status") == "APPLIED":
            return True, f"OK (Passport: {p_id}, Model: {p.get('model')}, Path: {p.get('file_path')})", p

    # 2. Фолбек на legacy_files
    legacy = ledger.get("legacy_files", {})
    for path, entry in legacy.items():
        if entry.get("sha256") == sha256_hash:
            return True, f"OK (Model: {entry.get('model')}, Path: {path})", entry

    return False, f"Хеш {sha256_hash[:16]}... не знайдено в реєстрі провененсу ШІ.", {}

def run_verified_script(script_path: str, script_args: list) -> int:
    """Безпечне виконання скрипта суворо за умови проходження перевірки провененсу."""
    abs_path = os.path.abspath(script_path)
    is_valid, reason = verify_provenance(abs_path)

    if not is_valid:
        print(f"\n🛑 HARD GATE VIOLATION (Anti-Shadow Gate v0.8.2 / v0.9.1):", file=sys.stderr)
        print(f"   {reason}", file=sys.stderr)
        print("   Ручне створення скриптів через write_to_file в обхід моделей ШІ категорично заборонено.", file=sys.stderr)
        print("   Використовуйте канонічний синтез:", file=sys.stderr)
        print(f"   python3 .agents/scripts/diagnostic_runner.py --synthesize-script \"<завдання>\" --out {script_path}\n", file=sys.stderr)
        return 126

    print(f"\n🚀 Запуск валідованого скрипта ({reason}): {os.path.basename(abs_path)}")
    print("=" * 60)
    cmd = [sys.executable, abs_path] + script_args
    start_time = time.time()
    try:
        res = subprocess.run(cmd)
        elapsed = round(time.time() - start_time, 3)
        print(f"\n⏱️ Час виконання: {elapsed} с. Код виходу: {res.returncode}")
        return res.returncode
    except Exception as e:
        print(f"❌ Помилка виконання: {e}", file=sys.stderr)
        return 1

def verify_commit_attribution(commit_msg: str) -> tuple[bool, str]:
    """Перевірка атрибуції ШІ-моделі у повідомленні коміту на основі реєстру провененсу (v0.9.1 / v0.9.7 / v0.9.12)."""
    audit_match = re.search(r"audited:\s*([a-zA-Z0-9_\-.:]+)", commit_msg, re.IGNORECASE)
    if audit_match:
        auditor = audit_match.group(1).strip().lower()
        if "copilot" in auditor:
            copilot_flag = "/tmp/antigravity_copilot_executed.flag"
            if not os.path.exists(copilot_flag):
                return False, f"Фальсифікація аудиту: задекларовано '[audited: {auditor}]', але виконання Copilot CLI не зафіксовано в сесії (відсутній прапорець виконання copilot_executed.flag)."

    match = re.search(r"generated:\s*([a-zA-Z0-9_\-.:]+)", commit_msg, re.IGNORECASE)
    if not match:
        return True, "Атрибуція ШІ відсутня в коміті (ручний або структурний коміт)."

    model_claimed = match.group(1).strip().lower()
    if not model_claimed:
        return False, "Фальсифікація авторства: назва моделі у [generated: ...] порожня."

    ledger = load_ledger()
    legacy = ledger.get("legacy_files", {})
    passports = ledger.get("passports", {})

    if not legacy and not passports:
        return False, f"Реєстр провененсу порожній: генерацію моделлю '{model_claimed}' не підтверджено."

    matched_entries = []
    for p_id, p in passports.items():
        p_model = p.get("model", "").strip().lower()
        if p_model and (model_claimed == p_model or p_model in model_claimed or model_claimed in p_model):
            matched_entries.append(p.get("file_path"))

    for path, entry in legacy.items():
        entry_model = entry.get("model", "").strip().lower()
        if entry_model and (model_claimed == entry_model or entry_model in model_claimed or model_claimed in entry_model):
            matched_entries.append(path)

    if not matched_entries:
        return False, (
            f"Фальсифікація авторства коміту: задекларовано '[generated: {model_claimed}]', "
            f"але в реєстрі провененсу немає жодного файлу, згенерованого цією моделлю."
        )

    return True, f"OK (Знайдено {len(matched_entries)} зареєстрованих файлів для моделі {model_claimed})"

def main():
    parser = argparse.ArgumentParser(description="Phase 4 Provenance Ledger & Anti-Shadow Gate (Policy v0.9.12)")
    parser.add_argument("--verify", type=str, help="Перевірити валідність провененсу файлу")
    parser.add_argument("--verify-hash", type=str, help="Перевірити валідність SHA256 хешу")
    parser.add_argument("--verify-commit", type=str, help="Перевірити валідність атрибуції моделі в повідомленні коміту")
    parser.add_argument("--verify-chain", action="store_true", help="Перевірити ланцюг паспортів для змінених файлів git")
    parser.add_argument("--run", type=str, help="Запустити валідований скрипт")
    parser.add_argument("script_args", nargs="*", help="Аргументи для скрипта")

    args = parser.parse_args()

    if args.verify:
        valid, msg = verify_provenance(args.verify)
        print(f"Верифікація: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.verify_hash:
        valid, msg, entry = verify_content_sha256(args.verify_hash)
        print(f"Верифікація хешу: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.verify_commit:
        valid, msg = verify_commit_attribution(args.verify_commit)
        print(f"Верифікація коміту: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        return 0 if valid else 1
    elif args.verify_chain:
        valid, msg, items = verify_chain()
        print(f"Аудит ланцюга паспортів: {'🟢 PASS' if valid else '🔴 FAIL'} — {msg}")
        for it in items:
            if isinstance(it, dict):
                print(f"  • {it.get('path')} (Passport: {it.get('passport_id')}, Model: {it.get('model')})")
            else:
                print(f"  🔴 {it}")
        return 0 if valid else 1
    elif args.run:
        return run_verified_script(args.run, args.script_args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

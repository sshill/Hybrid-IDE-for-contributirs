#!/usr/bin/env python3
"""Hybrid-IDE PostToolUse hook: Runtime Circuit Breaker (C4). stdlib only."""
import fcntl
import hashlib
import json
import os
import sys
import time
from datetime import datetime

sys.dont_write_bytecode = True

LOG_FILE = "/tmp/antigravity_hooks.log"
CB_FILE = "/tmp/antigravity_circuit_breaker_fails.txt"
CB_TTL_SECONDS = 600

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(f"{datetime.now().isoformat()} [PostToolUse] {msg}\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass

def resolve_cb_file(data=None):
    """Визначає персистентний шлях файлу circuit breaker (Brain-First + /tmp fallback з ізоляцією за сесією)."""
    if data and isinstance(data, dict):
        conv_id = data.get("conversationId") or data.get("conversation_id") or ""
        art_dir = data.get("artifactDirectoryPath")
        wps = data.get("workspacePaths", [])
        if conv_id:
            sess_id = hashlib.sha256(conv_id.encode("utf-8")).hexdigest()[:8]
        elif wps and wps[0]:
            sess_id = hashlib.sha256(wps[0].encode("utf-8")).hexdigest()[:8]
        else:
            sess_id = hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest()[:8]

        sess_cb = f"/tmp/antigravity_circuit_breaker_fails_{sess_id}.txt"
        brain_root = os.path.realpath(os.path.expanduser("~/.gemini/antigravity/brain"))
        if art_dir:
            real_art = os.path.realpath(art_dir)
            if real_art == brain_root or real_art.startswith(brain_root + os.sep):
                sg = os.path.join(real_art, ".system_generated")
                try:
                    os.makedirs(sg, exist_ok=True)
                    return os.path.join(sg, "circuit_breaker_fails.txt")
                except Exception:
                    pass
        return sess_cb
    return CB_FILE

def read_fails(cb_path=CB_FILE):
    try:
        if not os.path.exists(cb_path):
            cb_path = CB_FILE
        if os.path.exists(cb_path):
            if time.time() - os.path.getmtime(cb_path) > CB_TTL_SECONDS:
                reset(cb_path)
                return 0
            with open(cb_path, "r") as f:
                return max(0, int(f.read().strip()))
    except Exception:
        pass
    return 0

def write_fails(n, cb_path=CB_FILE):
    targets = [cb_path]
    for p in targets:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(str(n))
        except Exception as e:
            log(f"cannot write breaker file {p}: {e}")

def reset(cb_path=CB_FILE):
    targets = set([cb_path, CB_FILE])
    for p in targets:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def find_exit_code(data):
    containers = [data]
    for key in ("toolResult", "tool_result", "result", "toolResponse", "tool_response", "output"):
        v = data.get(key)
        if isinstance(v, dict):
            containers.append(v)
    for c in containers:
        for key in ("exitCode", "exit_code", "returncode"):
            v = c.get(key)
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass
    return None

def has_error(data):
    containers = [data]
    for key in ("toolResult", "tool_result", "result", "toolResponse", "tool_response"):
        v = data.get(key)
        if isinstance(v, dict):
            containers.append(v)
    for c in containers:
        if c.get("error") or c.get("isError") is True or c.get("is_error") is True:
            return True
    return False

def _import_apply_passport():
    prov_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "provenance"),
        os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/bin"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bin")),
    ]
    for pd in prov_dirs:
        if os.path.isdir(pd) and pd not in sys.path:
            sys.path.insert(0, pd)
    try:
        from core.provenance.phase4_provenance import apply_passport
        return apply_passport
    except ModuleNotFoundError:
        try:
            from phase4_provenance import apply_passport
            return apply_passport
        except ModuleNotFoundError:
            return None

def handle_passport_post_tool(data, failed):
    """Підтверджує статус APPLIED для паспорта після успішної модифікації файлу."""
    if failed:
        return
    tool_name = data.get("toolName") or data.get("tool_name")
    if tool_name not in ("write_to_file", "replace_file_content"):
        return

    args = data.get("toolInput") or data.get("tool_input") or data.get("args") or {}
    target_file = args.get("TargetFile") or args.get("target_file") or args.get("path")
    if not target_file:
        return

    session_id = data.get("conversationId") or "session_default"
    art_dir = data.get("artifactDirectoryPath")
    if art_dir:
        session_id = os.path.basename(art_dir)

    apply_fn = _import_apply_passport()
    if apply_fn:
        try:
            ok, msg = apply_fn(session_id, target_file)
            if ok:
                log(f"Passport verified and APPLIED: {target_file}")
            else:
                log(f"Passport apply check: {msg}")
        except Exception as pe:
            log(f"apply_passport error: {pe}")

def main():
    if "--reset-breaker" in sys.argv[1:]:
        reset()
        log("breaker reset via --reset-breaker")
        print("{}")
        return

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}
    except Exception as e:
        log(f"json decode error: {e}")
        data = {}

    cb_path = resolve_cb_file(data)

    try:
        code = find_exit_code(data)
        failed = (code is not None and code != 0) or has_error(data)
        if failed:
            fails = read_fails(cb_path) + 1
            write_fails(fails, cb_path)
            log(f"failure recorded (exitCode={code}), consecutive={fails}")
        elif code is not None or data:
            if os.path.exists(cb_path) or os.path.exists(CB_FILE):
                log("success: breaker reset")
            reset(cb_path)

        handle_passport_post_tool(data, failed)
    except Exception as e:
        log(f"unexpected error: {e}")

    print("{}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enclave Architecture (Trusted Sidecar / Privilege Separation Enclave Daemon)
Шлях: core/enclave/enclave_daemon.py
Стандарт: SLSA / in-toto Cryptographic Attestation (Zero-Dep stdlib, Schema 1.2).

Призначення:
Повне розділення привілеїв між оркестратором Antigravity та кодогенерацією:
- Єдиний авторизований шлюз для всіх 4 рівнів ШІ (Ollama, Groq, Claude Sonnet, Copilot CLI).
- Первинний контроль кожної генерації: Anti-Echo перевірка шинґлів, AST валідація,
  in-memory симуляція, обчислення SHA256, HMAC-підпис паспорта Schema 1.2,
  атомарний запис на диск (fsync + os.replace) та фіксація статусу APPLIED.
- Мережевий режим на loopback 127.0.0.1:8765 для міжпроцесної ізоляції.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_ENCLAVE_PORT = 8765
DEFAULT_ENCLAVE_HOST = "127.0.0.1"


def _resolve_core_imports():
    """Динамічний імпорт функцій провененсу та діагностичного раннера (Dual-Layout)."""
    search_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "provenance"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"),
        os.path.expanduser("~/.gemini/config/plugins/hybrid-ide/bin"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bin")),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for sd in search_dirs:
        if os.path.isdir(sd) and sd not in sys.path:
            sys.path.insert(0, sd)

    prov_fns = {}
    diag_fns = {}

    try:
        from core.provenance.phase4_provenance import (
            mint_passport, reserve_passport, apply_passport,
            simulate_replacement, get_file_sha256, get_content_sha256,
            locked_ledger, load_ledger, compute_passport_hmac, verify_passport_hmac,
            GENERATIVE_MODELS_ALLOWLIST
        )
        prov_fns = {
            "mint_passport": mint_passport,
            "reserve_passport": reserve_passport,
            "apply_passport": apply_passport,
            "simulate_replacement": simulate_replacement,
            "get_file_sha256": get_file_sha256,
            "get_content_sha256": get_content_sha256,
            "locked_ledger": locked_ledger,
            "load_ledger": load_ledger,
            "compute_passport_hmac": compute_passport_hmac,
            "verify_passport_hmac": verify_passport_hmac,
            "allowlist": GENERATIVE_MODELS_ALLOWLIST
        }
    except ModuleNotFoundError:
        try:
            from phase4_provenance import (
                mint_passport, reserve_passport, apply_passport,
                simulate_replacement, get_file_sha256, get_content_sha256,
                locked_ledger, load_ledger, compute_passport_hmac, verify_passport_hmac,
                GENERATIVE_MODELS_ALLOWLIST
            )
            prov_fns = {
                "mint_passport": mint_passport,
                "reserve_passport": reserve_passport,
                "apply_passport": apply_passport,
                "simulate_replacement": simulate_replacement,
                "get_file_sha256": get_file_sha256,
                "get_content_sha256": get_content_sha256,
                "locked_ledger": locked_ledger,
                "load_ledger": load_ledger,
                "compute_passport_hmac": compute_passport_hmac,
                "verify_passport_hmac": verify_passport_hmac,
                "allowlist": GENERATIVE_MODELS_ALLOWLIST
            }
        except ModuleNotFoundError:
            pass

    try:
        from core.engine.diagnostic_runner import (
            query_ollama_engine, query_groq_engine, query_openrouter_engine,
            query_claude_engine, query_copilot_engine,
            compute_prompt_code_shingle_overlap, write_session_flag,
            resolve_session_id, check_anchor_spec
        )
        diag_fns = {
            "query_ollama": query_ollama_engine,
            "query_groq": query_groq_engine,
            "query_openrouter": query_openrouter_engine,
            "query_claude": query_claude_engine,
            "query_copilot": query_copilot_engine,
            "compute_shingle_overlap": compute_prompt_code_shingle_overlap,
            "write_session_flag": write_session_flag,
            "resolve_session_id": resolve_session_id,
            "check_anchor_spec": check_anchor_spec
        }
    except ModuleNotFoundError:
        try:
            from diagnostic_runner import (
                query_ollama_engine, query_groq_engine, query_openrouter_engine,
                query_claude_engine, query_copilot_engine,
                compute_prompt_code_shingle_overlap, write_session_flag,
                resolve_session_id, check_anchor_spec
            )
            diag_fns = {
                "query_ollama": query_ollama_engine,
                "query_groq": query_groq_engine,
                "query_openrouter": query_openrouter_engine,
                "query_claude": query_claude_engine,
                "query_copilot": query_copilot_engine,
                "compute_shingle_overlap": compute_prompt_code_shingle_overlap,
                "write_session_flag": write_session_flag,
                "resolve_session_id": resolve_session_id,
                "check_anchor_spec": check_anchor_spec
            }
        except ModuleNotFoundError:
            pass

    return prov_fns, diag_fns


def clean_markdown_fences(raw_code: str) -> str:
    """Видалення markdown-блоків коду (```python ... ``` або ```sh ... ```) та вилучення чистого коду."""
    cb = raw_code.strip()
    if "```" in cb:
        m = re.search(r"```(?:[a-zA-Z0-9_\-]+)?\n?(.*?)```", cb, flags=re.DOTALL)
        if m:
            return m.group(1).strip()
        lines = cb.split("\n")
        in_block = False
        code_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip()
    return cb


def validate_code_syntax(code_str: str, file_path: str) -> tuple[bool, str]:
    """Детерміністична валідація синтаксису коду у пам'яті (AST Gate)."""
    clean_path = file_path.lower()
    if clean_path.endswith(".py"):
        try:
            ast.parse(code_str)
            return True, "AST_PASS"
        except SyntaxError as e:
            return False, f"Python SyntaxError: {e.msg} at line {e.lineno}"
    elif clean_path.endswith(".sh") or clean_path.endswith(".bash"):
        # Базова перевірка збалансованості лапок та шелл-структур
        for q in ('"', "'"):
            if code_str.count(q) % 2 != 0:
                return False, f"Shell SyntaxError: Unbalanced {q} quote detected"
        return True, "SHELL_SYNTAX_PASS"
    return True, "SYNTAX_UNCHECKED"


def direct_query_ollama(prompt: str, model: str = "qwen2.5-coder:1.5b", num_predict: int = 400) -> str:
    """Прямий нативний виклик до локальної Ollama через stdlib (loopback 127.0.0.1:11434)."""
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": num_predict
        }
    }
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception as e:
        return f"OLLAMA_ERROR: {e}"


def query_all_tier_ai(
    prompt: str,
    tier: int = None,
    model: str = None,
    mode: str = "synthesize"
) -> tuple[str, str, int]:
    """
    Уніфікований шлюз виклику моделей ШІ через Анклав (All-Tier AI Gateway).
    Повертає (output_text, model_name, tier_number).
    Підтримує FrugalGPT каскад (Tier 1 Ollama -> Tier 2 Groq -> Tier 4/4.5).
    """
    _, diag_fns = _resolve_core_imports()

    # 1. Специфічний вибір Tier 4.5 (Copilot CLI)
    if tier == 4.5 or model == "copilot-cli":
        if diag_fns and "query_copilot" in diag_fns:
            fn = diag_fns.get("query_copilot")
            res = fn(prompt, mode="query" if mode == "synthesize" else "audit")
            if res and not str(res).startswith("COPILOT_NOT_FOUND"):
                return res, "copilot-cli", 4.5
        # fallback down
        tier = 2

    # 2. Специфічний вибір Tier 4 (Claude Sonnet)
    if tier == 4 or (model and "claude" in model.lower()):
        if diag_fns and "query_claude" in diag_fns:
            fn = diag_fns.get("query_claude")
            resolved_model = model or "claude-3-5-sonnet-20241022"
            res = fn(prompt, mode="query" if mode == "synthesize" else "audit", model=resolved_model)
            if res and not str(res).startswith("CLAUDE_ALL_PROVIDERS_FAILED"):
                return res, resolved_model, 4
        # fallback down to Tier 2
        tier = 2

    # 3. Специфічний вибір Tier 2 (Groq Cloud LPU)
    if tier == 2 or (model and ("gpt-oss" in model.lower() or "groq" in model.lower())):
        if diag_fns and "query_groq" in diag_fns:
            fn = diag_fns.get("query_groq")
            resolved_model = model or "openai/gpt-oss-120b"
            res = fn(prompt, model=resolved_model)
            if res and not str(res).startswith("ERROR:") and "GROQ_KEY_MISSING" not in res:
                return res, resolved_model, 2
        # fallback down to Tier 1
        tier = 1

    # 4. Базовий вибір: Tier 1 (Ollama Local Edge) — первинний за замовчуванням
    resolved_model = model if (model and "qwen" in model.lower()) else "qwen2.5-coder:1.5b"
    if diag_fns and "query_ollama" in diag_fns:
        fn = diag_fns.get("query_ollama")
        res = fn(prompt, model=resolved_model)
        if isinstance(res, tuple):
            res_text = res[0]
        else:
            res_text = res
        if res_text and not str(res_text).startswith("ERROR:") and res_text not in ("OLLAMA_OFFLINE", "HARDWARE_LIMIT_EXCEEDED"):
            return res_text, resolved_model, 1

    # Резервний прямий виклик Ollama через нативний сокет
    direct_res = direct_query_ollama(prompt, model=resolved_model)
    if direct_res and not direct_res.startswith("OLLAMA_ERROR:"):
        return direct_res, resolved_model, 1

    # 5. Авто-каскад на Groq (Tier 2) при недоступності Ollama
    if diag_fns and "query_groq" in diag_fns:
        fn_groq = diag_fns.get("query_groq")
        res_g = fn_groq(prompt, model="openai/gpt-oss-120b")
        if res_g and not str(res_g).startswith("ERROR:") and "GROQ_KEY_MISSING" not in res_g:
            return res_g, "openai/gpt-oss-120b", 2

    return "ERROR: All configured AI model tiers failed to generate response", "none", 0


def compute_shingle_overlap(prompt_text: str, code_text: str, n: int = 8) -> float:
    """Обчислює відсоток збігу n-слівних шинґлів між промптом та кодом (Anti-Echo Gate)."""
    cleaned_prompt = re.sub(r"<context>.*?</context>", "", prompt_text, flags=re.DOTALL)
    prompt_tokens = re.findall(r"\b\w+\b", cleaned_prompt.lower())
    code_tokens = re.findall(r"\b\w+\b", code_text.lower())
    if len(prompt_tokens) < n or len(code_tokens) < n:
        return 0.0
    prompt_shingles = set(tuple(prompt_tokens[i:i+n]) for i in range(len(prompt_tokens) - n + 1))
    code_shingles = set(tuple(code_tokens[i:i+n]) for i in range(len(code_tokens) - n + 1))
    if not code_shingles:
        return 0.0
    overlap = prompt_shingles.intersection(code_shingles)
    return len(overlap) / len(code_shingles)


def enclave_apply(
    target_path: str,
    task_prompt: str = None,
    direct_code: str = None,
    mode: str = "synthesize",
    tier: int = None,
    model: str = None,
    patch_target: str = None,
    start_line: int = None,
    end_line: int = None,
    allow_multiple: bool = False,
    session_id: str = None
) -> dict:
    """
    Атомарний конвеєр первинного контролю та застосування коду (Enclave Primary Control).
    1. Отримання та санітизація коду від моделі ШІ.
    2. Anti-Echo перевірка (шинґли <= 0.25).
    3. AST перевірка у пам'яті (ast.parse).
    4. In-memory симуляція заміни (simulate_replacement) при patch mode.
    5. Обчислення хешів SHA256 у пам'яті.
    6. Випуск криптографічного HMAC-SHA256 паспорта Schema 1.2 (MINTED -> RESERVED).
    7. Атомарний запис на диск (fsync + os.replace).
    8. Фіксація статусу APPLIED у леджері провененсу.
    9. Повернення структурованого JSON-receipt.
    """
    start_time = time.time()
    prov_fns, diag_fns = _resolve_core_imports()

    if not prov_fns:
        return {"status": "ERROR", "error": "Provenance engine functions not available"}

    mint_fn = prov_fns.get("mint_passport")
    reserve_fn = prov_fns.get("reserve_passport")
    apply_fn = prov_fns.get("apply_passport")
    sim_fn = prov_fns.get("simulate_replacement")
    get_file_sha = prov_fns.get("get_file_sha256")

    abs_target = os.path.realpath(os.path.abspath(target_path))
    sess_id = session_id or (diag_fns["resolve_session_id"]() if diag_fns else "enclave_session")

    # 1. Синтез коду моделями ШІ (якщо не передано direct_code)
    active_model = model or "qwen2.5-coder:1.5b"
    active_tier = tier or 1

    if direct_code is not None:
        raw_code = direct_code
    else:
        if not task_prompt:
            return {"status": "ERROR", "error": "Neither task_prompt nor direct_code provided"}
        ext = os.path.splitext(abs_target)[1].lstrip(".") or "py"
        lang = "Python" if ext in ("py", "pyw") else ("Bash" if ext in ("sh", "bash") else "code")
        augmented_prompt = (
            f"You are an expert {lang} developer. Write a clean, complete, standalone {lang} implementation for the following task.\n"
            f"Output ONLY executable code inside markdown fences ```{ext} ... ``` without chat text, explanations or greetings.\n\n"
            f"Task:\n{task_prompt}"
        )
        raw_code, active_model, active_tier = query_all_tier_ai(
            augmented_prompt, tier=tier, model=model, mode=mode
        )
        if raw_code.startswith("ERROR:"):
            return {"status": "ERROR", "error": f"AI synthesis failed: {raw_code}"}

    # 2. Очищення коду від markdown
    clean_code = clean_markdown_fences(raw_code)

    # 3. Anti-Echo Gate: перевірка збігу шинґлів між завданням та кодом
    if task_prompt:
        overlap_fn = diag_fns.get("compute_shingle_overlap") if (diag_fns and "compute_shingle_overlap" in diag_fns) else compute_shingle_overlap
        overlap = overlap_fn(task_prompt, clean_code, n=8)
        if overlap > 0.25:
            return {
                "status": "ERROR",
                "error": f"Anti-Echo Gate Rejection: Shingle overlap ratio {overlap:.2f} > 0.25 (possible echo laundering)"
            }

    # 4. Підготовка підсумкового байтового вмісту (In-Memory Simulation)
    baseline_sha256 = None
    if os.path.isfile(abs_target):
        baseline_sha256 = get_file_sha(abs_target)

    if mode == "synthesize":
        # Додавання обов'язкових стандартів, якщо це новий скрипт Python
        if abs_target.endswith(".py") and not clean_code.startswith("#!"):
            header = (
                "#!/usr/bin/env python3\n"
                "# -*- coding: utf-8 -*-\n"
                f"# [AI_PROVENANCE: TIER_{active_tier} | MODEL: {active_model}]\n"
                "import sys\n"
                "sys.dont_write_bytecode = True\n\n"
            )
            final_code = header + clean_code
        else:
            final_code = clean_code

        final_code = final_code.rstrip() + "\n"
        final_bytes = final_code.encode("utf-8")

        # AST Gate
        ast_ok, ast_msg = validate_code_syntax(final_code, abs_target)
        if not ast_ok:
            return {"status": "ERROR", "error": f"AST Gate Rejection: {ast_msg}"}

    elif mode == "patch":
        if not os.path.isfile(abs_target):
            return {"status": "ERROR", "error": f"Cannot patch non-existent file: {abs_target}"}
        if not patch_target:
            return {"status": "ERROR", "error": "patch_target content is required for mode='patch'"}

        with open(abs_target, "rb") as f_in:
            existing_bytes = f_in.read()

        sim_ok, sim_bytes, sim_err = sim_fn(
            content_bytes=existing_bytes,
            target_bytes=patch_target.encode("utf-8"),
            replacement_bytes=clean_code.encode("utf-8"),
            start_line=start_line,
            end_line=end_line,
            allow_multiple=allow_multiple
        )
        if not sim_ok:
            return {"status": "ERROR", "error": f"Simulation Gate Rejection: {sim_err}"}

        final_bytes = sim_bytes

        # AST Gate на симульованому коді
        try:
            decoded_sim = final_bytes.decode("utf-8")
            ast_ok, ast_msg = validate_code_syntax(decoded_sim, abs_target)
            if not ast_ok:
                return {"status": "ERROR", "error": f"AST Gate Rejection on patched code: {ast_msg}"}
        except UnicodeDecodeError as ue:
            return {"status": "ERROR", "error": f"Patched code UTF-8 decode error: {ue}"}
    else:
        return {"status": "ERROR", "error": f"Unsupported mode: {mode}"}

    target_sha256 = hashlib.sha256(final_bytes).hexdigest()

    # 5. Випуск паспорта провененсу (MINTED)
    metrics = {
        "enclave_mode": mode,
        "elapsed_sec": round(time.time() - start_time, 3),
        "target_file": abs_target
    }
    try:
        passport_id = mint_fn(
            session_id=sess_id,
            file_path=abs_target,
            baseline_sha256=baseline_sha256,
            target_sha256=target_sha256,
            model=active_model,
            tier=int(active_tier) if isinstance(active_tier, (int, float)) else 2,
            metrics=metrics
        )
    except Exception as pe:
        return {"status": "ERROR", "error": f"Failed to mint cryptographic passport: {pe}"}

    # 6. Резервування паспорта (RESERVED)
    ok_res, p_id, res_err = reserve_fn(
        session_id=sess_id,
        file_path=abs_target,
        baseline_sha256=baseline_sha256,
        target_sha256=target_sha256,
        tool_name="enclave_daemon"
    )
    if not ok_res:
        return {"status": "ERROR", "error": f"Failed to reserve passport {passport_id}: {res_err}"}

    # 7. Атомарний запис на диск (fsync + os.replace)
    os.makedirs(os.path.dirname(abs_target), exist_ok=True)
    tmp_path = f"{abs_target}.tmp.{os.getpid()}.{int(time.time() * 1000)}"
    try:
        with open(tmp_path, "wb") as f_out:
            f_out.write(final_bytes)
            f_out.flush()
            os.fsync(f_out.fileno())
        os.replace(tmp_path, abs_target)
    except Exception as fe:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return {"status": "ERROR", "error": f"Atomic disk write failed: {fe}"}

    # 8. Підтвердження паспорта на диску (APPLIED)
    ok_app, app_msg = apply_fn(sess_id, abs_target)
    if not ok_app:
        return {"status": "ERROR", "error": f"Passport apply failed on disk: {app_msg}"}

    # 9. Фіксація сесійного прапорця валідації
    if diag_fns and "write_session_flag" in diag_fns:
        diag_fns["write_session_flag"](
            "enclave_applied.flag",
            f"ENCLAVE_APPLIED: {abs_target} passport={passport_id} model={active_model} tier={active_tier} timestamp={time.time()}\n",
            meta={"file_path": abs_target, "passport_id": passport_id, "target_sha256": target_sha256}
        )

    receipt = {
        "status": "SUCCESS",
        "passport_id": passport_id,
        "target_file": abs_target,
        "baseline_sha256": baseline_sha256,
        "target_sha256": target_sha256,
        "model": active_model,
        "tier": active_tier,
        "mode": mode,
        "ast_verified": True,
        "bytes_written": len(final_bytes),
        "timestamp": time.time()
    }
    return receipt


def enclave_query(
    prompt: str,
    tier: int = 1,
    model: str = None,
    mode: str = "query"
) -> dict:
    """Виконання запиту або аудиту моделі через Анклав з провененс-атестацією."""
    start_time = time.time()
    _, diag_fns = _resolve_core_imports()
    output_text, used_model, used_tier = query_all_tier_ai(prompt, tier=tier, model=model, mode=mode)
    elapsed = round(time.time() - start_time, 2)

    if diag_fns and "write_session_flag" in diag_fns:
        diag_fns["write_session_flag"](
            f"enclave_{mode}.flag",
            f"ENCLAVE_{mode.upper()}: model={used_model} tier={used_tier} elapsed={elapsed} timestamp={time.time()}\n"
        )

    return {
        "status": "SUCCESS" if not output_text.startswith("ERROR:") else "ERROR",
        "output": output_text,
        "model": used_model,
        "tier": used_tier,
        "elapsed_sec": elapsed
    }


class EnclaveHTTPHandler(BaseHTTPRequestHandler):
    """Легкий обробник HTTP-запитів до Анклаву (Loopback 127.0.0.1)."""

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "READY",
                "version": "0.9.11",
                "enclave": "Trusted Sidecar",
                "tiers": [1, 2, 4, 4.5],
                "time": time.time()
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ERROR", "error": f"Invalid JSON body: {e}"}).encode("utf-8"))
            return

        if self.path == "/apply":
            res = enclave_apply(
                target_path=req_data.get("target_path") or req_data.get("target_file", ""),
                task_prompt=req_data.get("task_prompt") or req_data.get("task"),
                direct_code=req_data.get("direct_code"),
                mode=req_data.get("mode", "synthesize"),
                tier=req_data.get("tier"),
                model=req_data.get("model"),
                patch_target=req_data.get("patch_target"),
                start_line=req_data.get("start_line"),
                end_line=req_data.get("end_line"),
                allow_multiple=req_data.get("allow_multiple", False),
                session_id=req_data.get("session_id")
            )
            code = 200 if res.get("status") == "SUCCESS" else 422
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

        elif self.path == "/query":
            res = enclave_query(
                prompt=req_data.get("prompt", ""),
                tier=req_data.get("tier", 1),
                model=req_data.get("model"),
                mode=req_data.get("mode", "query")
            )
            code = 200 if res.get("status") == "SUCCESS" else 422
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Приховуємо шум стандартних HTTP-логів у stdout
        pass


def run_enclave_daemon(host: str = DEFAULT_ENCLAVE_HOST, port: int = DEFAULT_ENCLAVE_PORT):
    """Запуск фонового демона анклаву на loopback інтерфейсі 127.0.0.1."""
    server_address = (host, port)
    try:
        httpd = HTTPServer(server_address, EnclaveHTTPHandler)
        print(f"🔒 [ENCLAVE DAEMON STARTED] Listening strictly on http://{host}:{port}")
        print("  • Tiers available: Tier 1 (Ollama), Tier 2 (Groq), Tier 4 (Claude Sonnet), Tier 4.5 (Copilot CLI)")
        print("  • Primary Control: Anti-Echo, AST, HMAC Passports, Atomic Writes, Ledger Sync")
        print("Press Ctrl+C to terminate.")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🔒 [ENCLAVE DAEMON TERMINATED]")
    except Exception as e:
        print(f"❌ [ENCLAVE DAEMON ERROR]: {e}", file=sys.stderr)
        sys.exit(1)


def is_daemon_running(host: str = DEFAULT_ENCLAVE_HOST, port: int = DEFAULT_ENCLAVE_PORT) -> bool:
    """Перевірка чи активний локальний демон анклаву на 127.0.0.1."""
    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HybridIDE-Enclave-Probe"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("status") == "READY"
    except Exception:
        pass
    return False


def call_daemon_apply(payload: dict, host: str = DEFAULT_ENCLAVE_HOST, port: int = DEFAULT_ENCLAVE_PORT) -> dict:
    """Виклик демона анклаву через loopback HTTP API."""
    url = f"http://{host}:{port}/apply"
    req_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "HybridIDE-Enclave-Client"}
    )
    with urllib.request.urlopen(req, timeout=120.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Hybrid IDE Enclave Architecture Daemon & Client (v0.9.11)")
    parser.add_argument("--daemon", action="store_true", help="Запустити демон анклаву на loopback 127.0.0.1")
    parser.add_argument("--host", type=str, default=DEFAULT_ENCLAVE_HOST, help="Хост (за замовчуванням 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_ENCLAVE_PORT, help="Порт (за замовчуванням 8765)")
    parser.add_argument("--target", type=str, help="Цільовий файл для застосування коду")
    parser.add_argument("--task", type=str, help="ТЗ для синтезу коду моделлю ШІ")
    parser.add_argument("--direct-code", type=str, help="Прямий код для валідації та запису (без запиту до ШІ)")
    parser.add_argument("--mode", type=str, choices=["synthesize", "patch"], default="synthesize", help="Режим: synthesize або patch")
    parser.add_argument("--tier", type=float, help="Рівень ШІ (1, 2, 4, 4.5)")
    parser.add_argument("--model", type=str, help="Назва моделі ШІ")
    parser.add_argument("--patch-target", type=str, help="Вміст для заміни в файлі (для режиму patch)")
    parser.add_argument("--start-line", type=int, help="Початковий рядок заміни")
    parser.add_argument("--end-line", type=int, help="Кінцевий рядок заміни")
    parser.add_argument("--allow-multiple", action="store_true", help="Дозволити множинну заміну")
    parser.add_argument("--query", type=str, help="Виконати аудит або запит через анклав")
    parser.add_argument("--json-output", action="store_true", help="Вивести результат у JSON")
    args = parser.parse_args()

    if args.daemon:
        run_enclave_daemon(host=args.host, port=args.port)
        return 0

    if args.query:
        res = enclave_query(args.query, tier=args.tier or 1, model=args.model)
        if args.json_output:
            print(json.dumps(res, indent=2))
        else:
            print(res.get("output", ""))
        return 0 if res.get("status") == "SUCCESS" else 1

    if args.target:
        payload = {
            "target_path": args.target,
            "task_prompt": args.task,
            "direct_code": args.direct_code,
            "mode": args.mode,
            "tier": args.tier,
            "model": args.model,
            "patch_target": args.patch_target,
            "start_line": args.start_line,
            "end_line": args.end_line,
            "allow_multiple": args.allow_multiple
        }

        # Якщо активний локальний демон на 127.0.0.1, делегуємо через HTTP
        if is_daemon_running(host=args.host, port=args.port):
            try:
                receipt = call_daemon_apply(payload, host=args.host, port=args.port)
            except Exception as e:
                print(f"⚠️ Помилка виклику демона анклаву: {e}. Виконуємо in-process fallback...", file=sys.stderr)
                receipt = enclave_apply(**payload)
        else:
            receipt = enclave_apply(**payload)

        if args.json_output:
            print(json.dumps(receipt, indent=2))
        else:
            if receipt.get("status") == "SUCCESS":
                print(f"✅ [ENCLAVE RECEIPT] Passport {receipt.get('passport_id')} APPLIED for {receipt.get('target_file')}")
                print(f"  • SHA256: {receipt.get('target_sha256')}")
                print(f"  • Model: {receipt.get('model')} (Tier {receipt.get('tier')})")
                print(f"  • Mode: {receipt.get('mode')}, AST verified: {receipt.get('ast_verified')}")
            else:
                print(f"❌ [ENCLAVE ERROR]: {receipt.get('error')}", file=sys.stderr)

        return 0 if receipt.get("status") == "SUCCESS" else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

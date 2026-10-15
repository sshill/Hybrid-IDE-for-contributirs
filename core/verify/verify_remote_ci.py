#!/usr/bin/env python3
"""
core/verify/verify_remote_ci.py
Автономний перевіряльник віддаленого GitHub Actions CI/CD для Фази 5.
Опитує GitHub API, очікує завершення пайплайну для вказаного коміту та
виводить оригінальне повідомлення провайдера (Original Provider Report).
"""

import sys
import os
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Prevent creation of .pyc files
sys.dont_write_bytecode = True

DEFAULT_REPO = "sshill/Hybrid-IDE-for-contributirs"
DEFAULT_WORKFLOW = "policy_ci.yml"

def get_git_commit(repo_dir: str = ".") -> str:
    """Визначення поточного HEAD commit SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return ""

def load_github_token() -> str:
    """Отримання токена GitHub з оточення або ~/.env для збільшення рейт-ліміту."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    env_file = os.path.expanduser("~/.env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_TOKEN=") or line.startswith("GH_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass
    return ""

def fetch_json(url: str, token: str = "") -> dict:
    """Виконання GET-запиту до GitHub API без зовнішніх залежностей."""
    headers = {
        "User-Agent": "Hybrid-IDE-Phase5-Verifier",
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def calculate_duration(start_str: str, end_str: str) -> str:
    """Розрахунок тривалості за ISO 8601 мітками."""
    try:
        # Format: 2026-10-15T05:57:05Z
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(end_str, fmt)
        secs = int((t2 - t1).total_seconds())
        return f"{secs} с"
    except Exception:
        return "н/д"

def print_original_report(run: dict, jobs_data: dict, verbose_json: bool = False):
    """Презентація оригінального повідомлення провайдера з повною деталізацією."""
    run_id = run.get("id")
    run_num = run.get("run_number")
    workflow_name = run.get("name")
    status = run.get("status")
    conclusion = run.get("conclusion")
    html_url = run.get("html_url")
    head_sha = run.get("head_sha")
    branch = run.get("head_branch")
    event = run.get("event")
    actor = run.get("actor", {}).get("login", "unknown")
    start_time = run.get("run_started_at") or run.get("created_at") or ""
    end_time = run.get("updated_at") or ""
    duration = calculate_duration(start_time, end_time)

    commit_info = run.get("head_commit", {})
    commit_msg = commit_info.get("message", "").split("\n")[0] if commit_info else "н/д"

    print("\n" + "=" * 70)
    print("🌐 ОРИГІНАЛЬНЕ ПОВІДОМЛЕННЯ GITHUB ACTIONS: " + str(run.get("path", DEFAULT_WORKFLOW)))
    print("=" * 70)
    print(f"Workflow:      {workflow_name}")
    print(f"Run ID:        {run_id}")
    print(f"Run Number:    #{run_num} (Спроба: {run.get('run_attempt', 1)})")
    print(f"HTML URL:      {html_url}")
    print(f"Commit SHA:    {head_sha}")
    print(f"Commit Msg:    {commit_msg}")
    print(f"Branch / Ref:  {branch}")
    print(f"Trigger Event: {event}")
    print(f"Trigger Actor: {actor}")
    print(f"Run Status:    {status}")
    print(f"Conclusion:    {conclusion}")
    print(f"Started At:    {start_time}")
    print(f"Completed At:  {end_time}")
    print(f"Duration:      {duration}")

    jobs = jobs_data.get("jobs", [])
    if jobs:
        print("\n--- ДЕТАЛІЗАЦІЯ ДЖОБ ТА КРОКІВ (JOBS & STEPS) ---")
        for job in jobs:
            job_name = job.get("name", "job")
            job_status = job.get("status", "unknown")
            job_conclusion = job.get("conclusion", "pending")
            job_icon = "🟢" if job_conclusion == "success" else ("🔴" if job_conclusion == "failure" else "🟡")
            print(f"{job_icon} [Job: {job_name}] Status: {job_status} | Conclusion: {job_conclusion}")
            print(f"   URL: {job.get('html_url')}")

            steps = job.get("steps", [])
            for step in steps:
                s_num = step.get("number")
                s_name = step.get("name")
                s_conc = step.get("conclusion")
                s_icon = "🟢" if s_conc == "success" else ("🔴" if s_conc == "failure" else "⚪")
                s_dur = calculate_duration(step.get("started_at", ""), step.get("completed_at", ""))
                print(f"     {s_icon} [{s_num}] {s_name:<42} [{s_conc}] ({s_dur})")

    print("=" * 70)

    if verbose_json:
        print("\n--- RAW JSON RUN METADATA ---")
        print(json.dumps(run, indent=2, ensure_ascii=False))

def verify_remote_ci(repo: str, workflow: str, target_commit: str, timeout: int = 180, poll_interval: int = 5, verbose_json: bool = False) -> int:
    """
    Основний цикл опитування та валідації хмарного білду.
    Повертає 0 при conclusion == 'success', інакше 1.
    """
    token = load_github_token()
    base_runs_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=10"
    
    print(f"🔍 Запуск верифікатора віддаленого CI...")
    print(f"  Репозиторій: {repo}")
    print(f"  Workflow:    {workflow}")
    print(f"  Commit SHA:  {target_commit}")
    print(f"  Таймаут:     {timeout} с (інтервал: {poll_interval} с)")

    start_time = time.time()
    matched_run = None

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        try:
            data = fetch_json(base_runs_url, token)
            runs = data.get("workflow_runs", [])
            for r in runs:
                r_sha = r.get("head_sha", "")
                if target_commit.lower() in r_sha.lower() or r_sha.lower().startswith(target_commit.lower()):
                    matched_run = r
                    break

            if matched_run:
                status = matched_run.get("status")
                run_num = matched_run.get("run_number")
                if status == "completed":
                    break
                else:
                    print(f"⏳ [{elapsed}с/{timeout}с] Запуск #{run_num} знайдено. Статус: '{status}', очікування завершення...")
            else:
                print(f"⏳ [{elapsed}с/{timeout}с] Очікування появи запуску GitHub Actions для коміту {target_commit[:7]}...")

        except urllib.error.HTTPError as he:
            sys.stderr.write(f"⚠️ Помилка запиту до GitHub API (HTTP {he.code}): {he.reason}\n")
            if he.code == 403:
                sys.stderr.write("  (Можливо вичерпано ліміт запитів GitHub API. Спробуйте вказати GITHUB_TOKEN)\n")
        except Exception as e:
            sys.stderr.write(f"⚠️ Збій з'єднання з GitHub API: {e}\n")

        time.sleep(poll_interval)

    if not matched_run:
        sys.stderr.write(f"\n❌ ТАЙМАУТ: Запуск для коміту {target_commit} не знайдено за {timeout} секунд.\n")
        return 1

    if matched_run.get("status") != "completed":
        # Спробувати зробити фінальне оновлення
        try:
            run_url = matched_run.get("url")
            matched_run = fetch_json(run_url, token)
        except Exception:
            pass

    # Отримання джобів
    jobs_data = {}
    jobs_url = matched_run.get("jobs_url")
    if jobs_url:
        try:
            jobs_data = fetch_json(jobs_url, token)
        except Exception as e:
            sys.stderr.write(f"⚠️ Не вдалося завантажити деталі кроків джоби: {e}\n")

    # Презентація оригінального репорту
    print_original_report(matched_run, jobs_data, verbose_json=verbose_json)

    conclusion = matched_run.get("conclusion")
    if conclusion == "success":
        print("✅ ВЕРДИКТ: Хмарний пайплайн завершено успішно (conclusion: success).")
        return 0
    else:
        print(f"❌ ВЕРДИКТ: Хмарний пайплайн завершився зі статусом '{conclusion}'. Потрібне усунення помилок.")
        return 1

def parse_args():
    parser = argparse.ArgumentParser(description="Автономний перевіряльник віддаленого GitHub Actions CI для Фази 5")
    parser.add_argument("--repo", type=str, default=DEFAULT_REPO, help=f"Репозиторій GitHub (дефолт: {DEFAULT_REPO})")
    parser.add_argument("--workflow", type=str, default=DEFAULT_WORKFLOW, help=f"Файл workflow (дефолт: {DEFAULT_WORKFLOW})")
    parser.add_argument("--commit", type=str, default=None, help="Commit SHA для верифікації (дефолт: HEAD)")
    parser.add_argument("--timeout", type=int, default=180, help="Максимальний час очікування в секундах (дефолт: 180)")
    parser.add_argument("--poll-interval", type=int, default=5, help="Інтервал опитування в секундах (дефолт: 5)")
    parser.add_argument("--json", action="store_true", help="Виводити повний сирий JSON-репорт провайдера")
    return parser.parse_args()

def main():
    args = parse_args()
    commit_sha = args.commit
    if not commit_sha:
        commit_sha = get_git_commit()
    if not commit_sha:
        sys.stderr.write("❌ Не вдалося визначити цільовий Commit SHA.\n")
        sys.exit(1)

    code = verify_remote_ci(
        repo=args.repo,
        workflow=args.workflow,
        target_commit=commit_sha,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        verbose_json=args.json
    )
    sys.exit(code)

if __name__ == "__main__":
    main()

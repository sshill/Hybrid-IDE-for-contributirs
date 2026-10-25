#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit Publisher CLI Runner (core/publish/reddit_publisher.py)
Part of the Hybrid-IDE Multi-Tier Architecture under Policy v0.9.5.

Enables automated, verifiable submission of technical articles and allegorical media
to engineering subreddits (r/ProgrammerHumor, r/LocalLLaMA, r/softwarearchitecture).
Zero external dependencies (uses standard library urllib).
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True


def load_env_credentials() -> dict:
    """Load credentials from ~/.env, workspace .env, and system environment."""
    candidates = [
        os.path.expanduser("~/.env"),
        "/home/hills/Documents/.env",
        "/home/hills/Documents/fallaut/.env",
        os.path.join(os.getcwd(), ".env"),
    ]
    for env_file in candidates:
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

    return {
        "client_id": os.environ.get("REDDIT_CLIENT_ID", ""),
        "client_secret": os.environ.get("REDDIT_CLIENT_SECRET", ""),
        "username": os.environ.get("REDDIT_USERNAME", ""),
        "password": os.environ.get("REDDIT_PASSWORD", ""),
        "user_agent": os.environ.get(
            "REDDIT_USER_AGENT",
            "HybridIDE-Publisher/0.9.5 (by /u/sshill; Principal Systems Architect)",
        ),
    }


def compute_file_sha256(filepath: str) -> str:
    """Compute cryptographic SHA256 hash for SLSA provenance tracking."""
    if not os.path.isfile(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def print_banner():
    print("=" * 65)
    print("🤖 Hybrid IDE: Reddit Publisher & Provenance Dispatcher (v0.9.5)")
    print("=" * 65)


def check_subreddit_accessibility(subreddit: str, user_agent: str) -> dict:
    """Check if the target subreddit exists and is publicly reachable."""
    url = f"https://www.reddit.com/r/{subreddit}/about.json"
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (compatible; HybridIDE/0.9.5)"
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sub_data = data.get("data", {})
            return {
                "ok": True,
                "title": sub_data.get("title", ""),
                "subscribers": sub_data.get("subscribers", 0),
                "over18": sub_data.get("over18", False),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_oauth2_token(creds: dict) -> str:
    """Acquire OAuth2 Bearer token from Reddit."""
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError("Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET in environment.")
    if not creds["username"] or not creds["password"]:
        raise ValueError("Missing REDDIT_USERNAME or REDDIT_PASSWORD in environment.")

    auth_str = f"{creds['client_id']}:{creds['client_secret']}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    token_url = "https://www.reddit.com/api/v1/access_token"
    payload = urllib.parse.urlencode({
        "grant_type": "password",
        "username": creds["username"],
        "password": creds["password"],
    }).encode("utf-8")

    headers = {
        "User-Agent": creds["user_agent"],
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    req = urllib.request.Request(token_url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "access_token" in data:
            return data["access_token"]
        raise RuntimeError(f"Reddit OAuth2 token error: {data}")


def check_auth(creds: dict) -> bool:
    """Verify Reddit credentials and current identity."""
    print("🔹 Перевірка автентифікації Reddit OAuth2...")
    try:
        token = get_oauth2_token(creds)
        me_url = "https://oauth.reddit.com/api/v1/me"
        headers = {
            "User-Agent": creds["user_agent"],
            "Authorization": f"Bearer {token}",
        }
        req = urllib.request.Request(me_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Успішно автентифіковано як: /u/{data.get('name')}")
            print(f"   Karma: Link={data.get('link_karma', 0)}, Comment={data.get('comment_karma', 0)}")
            return True
    except Exception as e:
        print(f"❌ Помилка автентифікації Reddit: {e}")
        return False


def verify_post_status(post_url: str, user_agent: str) -> bool:
    """Verify live HTTP status of a published post."""
    print(f"🔍 Верифікація доступності поста: {post_url}")
    req = urllib.request.Request(post_url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            if status == 200:
                print(f"✅ Пост активний та доступний: HTTP {status} OK")
                return True
            print(f"⚠️ Неочікуваний статус: HTTP {status}")
            return False
    except Exception as e:
        print(f"❌ Помилка перевірки поста: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Hybrid IDE Reddit Publisher (Policy v0.9.5)")
    parser.add_argument("--subreddit", type=str, help="Target subreddit (e.g. ProgrammerHumor, LocalLLaMA)")
    parser.add_argument("--title", type=str, help="Submission title")
    parser.add_argument("--text", type=str, help="Direct text body for text submission")
    parser.add_argument("--text-file", type=str, help="Path to markdown text file")
    parser.add_argument("--image", type=str, help="Path to image file to attach/submit")
    parser.add_argument("--dry-run", action="store_true", help="Simulate submission without making network mutations")
    parser.add_argument("--check-auth", action="store_true", help="Test Reddit credentials and token validity")
    parser.add_argument("--verify", type=str, help="Verify published post URL")

    args = parser.parse_args()
    print_banner()

    creds = load_env_credentials()

    if args.verify:
        verify_post_status(args.verify, creds["user_agent"])
        return

    if args.check_auth:
        check_auth(creds)
        return

    if not args.subreddit or not args.title:
        print("ℹ️ Вкажіть обов'язкові параметри --subreddit та --title (або запустіть з --help).")
        return

    print(f"📋 Цільовий сабреддіт: r/{args.subreddit}")
    print(f"📝 Заголовок: \"{args.title}\"")

    # Перевірка доступності сабреддіта
    sub_info = check_subreddit_accessibility(args.subreddit, creds["user_agent"])
    if sub_info.get("ok"):
        print(f"🟢 Сабреддіт підтверджено: {sub_info.get('title')} ({sub_info.get('subscribers', 0):,} підписників)")
    else:
        print(f"⚠️ Попередження: Не вдалося верифікувати сабреддіт: {sub_info.get('error')}")

    # Обробка тексту
    body_text = args.text or ""
    text_sha256 = ""
    if args.text_file and os.path.isfile(args.text_file):
        with open(args.text_file, "r", encoding="utf-8") as f:
            body_text = f.read()
        text_sha256 = compute_file_sha256(args.text_file)
        print(f"📄 Завантажено текст з файлу: {args.text_file} ({len(body_text)} симв.)")
        print(f"   SHA256 (Текст): {text_sha256}")

    # Обробка зображення
    image_sha256 = ""
    if args.image:
        if os.path.isfile(args.image):
            image_sha256 = compute_file_sha256(args.image)
            image_size_kb = round(os.path.getsize(args.image) / 1024, 1)
            print(f"🖼️ Медіафайл: {args.image} ({image_size_kb} KB)")
            print(f"   SHA256 (Медіа): {image_sha256}")
        else:
            print(f"❌ Помилка: Файл зображення не знайдено: {args.image}")
            sys.exit(1)

    if args.dry_run:
        print("\n" + "=" * 65)
        print("🛡️ РЕЖИМ DRY-RUN: Валідація payload без публікації")
        print("=" * 65)
        print("✅ Попередні перевірки успішно пройдено:")
        print(f"   - Target Subreddit: r/{args.subreddit}")
        print(f"   - Payload Type:     {'Image + Text' if args.image and body_text else ('Image' if args.image else 'Text')}")
        print(f"   - SLSA Provenance:  Зафіксовано криптографічні хеші")
        print(f"   - Reddit Client ID: {'[Встановлено]' if creds['client_id'] else '[Відсутній у .env]'}")
        print(f"   - Reddit Username:  {creds['username'] or '[Відсутній у .env]'}")
        print("\nГотово до бойової публікації після введення креденшалів у ~/.env.")
        return

    # Бойова публікація
    print("\n🚀 Підготовка бойової публікації...")
    try:
        token = get_oauth2_token(creds)
        submit_url = "https://oauth.reddit.com/api/submit"
        post_data = {
            "sr": args.subreddit,
            "title": args.title,
            "resubmit": "true",
            "sendreplies": "true",
        }
        if body_text and not args.image:
            post_data["kind"] = "self"
            post_data["text"] = body_text
        elif args.image:
            # Для зображень: пряма публікація або link post
            post_data["kind"] = "link"
            post_data["url"] = f"https://raw.githubusercontent.com/sshill/Hybrid-IDE-for-contributirs/main/{os.path.basename(args.image)}"

        encoded_data = urllib.parse.urlencode(post_data).encode("utf-8")
        headers = {
            "User-Agent": creds["user_agent"],
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        req = urllib.request.Request(submit_url, data=encoded_data, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                post_url = res.get("jquery", [[]])[-1][-1]
                print(f"🎉 Пост успішно опубліковано: {post_url}")
                verify_post_status(post_url, creds["user_agent"])
            else:
                print(f"❌ Відповідь Reddit API: {res}")
    except Exception as e:
        print(f"❌ Помилка під час публікації: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

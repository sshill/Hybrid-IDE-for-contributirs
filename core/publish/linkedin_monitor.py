#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Post & Comments Monitor (core/publish/linkedin_monitor.py)
Part of the Hybrid-IDE Multi-Tier Architecture under Policy v0.9.5.

Periodically inspects published LinkedIn posts and linked Pulse articles
for reactions, comment updates, and specific technical questions.
Zero external dependencies (uses standard library urllib, json, re, hashlib).
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

DEFAULT_SHORTLINK = "https://lnkd.in/p/dWJ-EyKC"
DEFAULT_CANONICAL_POST = (
    "https://www.linkedin.com/posts/serhii-khylevych-aa152322_"
    "the-yellow-brick-road-to-agi-or-why-engineering-activity-7517172325780422656-OY_k"
)
DEFAULT_PULSE_URL = (
    "https://www.linkedin.com/pulse/"
    "yellow-brick-road-agi-why-engineering-always-chooses-pass-khylevych-o1kpf"
)

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "linkedin_state.json"
)

QUESTION_INDICATORS = [
    r"\?",
    r"\bwhy\b",
    r"\bhow\b",
    r"\bwhat\b",
    r"\bwhen\b",
    r"\bwhere\b",
    r"\bcould\b",
    r"\bwould\b",
    r"\bcan you\b",
    r"\bчому\b",
    r"\bяк\b",
    r"\bщо\b",
    r"\bколи\b",
    r"\bде\b",
    r"\bчи\b",
    r"\bскільки\b",
    r"\bпідкажіть\b",
]


def compute_file_sha256(filepath: str) -> str:
    """Compute cryptographic SHA256 hash for SLSA provenance tracking."""
    if not os.path.isfile(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_previous_state() -> dict:
    """Load previously recorded state from STATE_FILE."""
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_checked_at": 0,
        "reactions_count": 0,
        "comments_count": 0,
        "seen_comment_hashes": [],
        "questions_found": [],
    }


def save_state(state: dict) -> None:
    """Persist updated state to STATE_FILE."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to persist state to {STATE_FILE}: {e}\n")


def fetch_url(url: str, timeout: int = 15) -> tuple[str, str]:
    """Fetch URL with browser user-agent and return (resolved_url, html_content)."""
    # ACCOUNT BAN PROTECTION GATE (Policy v0.9.6):
    # Automated unauthenticated HTML scraping of www.linkedin.com is strictly blocked to protect the user's account from bans.
    allow_scraping = os.getenv("ENABLE_LINKEDIN_LEGACY_SCRAPING", "0") == "1"
    if not allow_scraping and ("linkedin.com" in url or "lnkd.in" in url):
        sys.stderr.write(
            "🛑 [ACCOUNT PROTECTION GATE v0.9.6]: Unauthenticated HTML scraping of LinkedIn is blocked\n"
            "   to prevent bot detection and account suspension. Use official OAuth 2.0 client:\n"
            "   python3 /home/hills/Documents/Antigravity_Mgr/tools/linkedin_oauth_client.py --monitor\n"
        )
        return url, ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,uk;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resolved_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="replace")
            return resolved_url, html
    except Exception as e:
        sys.stderr.write(f"Error fetching {url}: {e}\n")
        return url, ""


def extract_social_metrics(html: str) -> tuple[int, int, list[dict]]:
    """Extract reactions count, comments count, and any visible comments."""
    reactions = 0
    comments_count = 0
    comments = []

    # 1. Reactions
    m_reac = re.search(r'data-num-reactions="(\d+)"', html)
    if m_reac:
        try:
            reactions = int(m_reac.group(1))
        except ValueError:
            pass
    else:
        m_reac_span = re.search(
            r'data-test-id="social-actions__reaction-count"[^>]*>\s*(\d+)', html
        )
        if m_reac_span:
            try:
                reactions = int(m_reac_span.group(1))
            except ValueError:
                pass

    # 2. Comments count
    m_comm = re.search(r'data-num-comments="(\d+)"', html)
    if m_comm:
        try:
            comments_count = int(m_comm.group(1))
        except ValueError:
            pass
    else:
        m_comm_text = re.search(r'(\d+)\s+comments?', html, re.IGNORECASE)
        if m_comm_text:
            try:
                comments_count = int(m_comm_text.group(1))
            except ValueError:
                pass

    # 3. Comment items extraction
    comment_pattern = re.compile(
        r'<div[^>]+class="[^"]*(?:comment__text|comment-item|comments-list__comment-item)[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in comment_pattern.finditer(html):
        raw_text = re.sub(r"<[^>]+>", " ", match.group(1))
        clean_text = " ".join(raw_text.split())
        if clean_text:
            c_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
            is_q = any(
                re.search(pat, clean_text, re.IGNORECASE)
                for pat in QUESTION_INDICATORS
            )
            comments.append({
                "hash": c_hash,
                "text": clean_text,
                "is_question": is_q,
            })

    return reactions, comments_count, comments


def run_monitor_check(target_url: str = DEFAULT_SHORTLINK, verbose: bool = False) -> dict:
    """Execute a single monitoring check cycle."""
    state = load_previous_state()
    prev_reactions = state.get("reactions_count", 0)
    prev_comments = state.get("comments_count", 0)
    seen_hashes = set(state.get("seen_comment_hashes", []))

    # Resolve target URL
    resolved_post_url, post_html = fetch_url(target_url)
    if not post_html and resolved_post_url != DEFAULT_CANONICAL_POST:
        resolved_post_url, post_html = fetch_url(DEFAULT_CANONICAL_POST)

    # Also check linked Pulse article
    _, pulse_html = fetch_url(DEFAULT_PULSE_URL)

    post_reactions, post_comments, post_comment_items = extract_social_metrics(post_html)
    pulse_reactions, pulse_comments, pulse_comment_items = extract_social_metrics(pulse_html)

    total_reactions = max(post_reactions, pulse_reactions)
    total_comments = max(post_comments, pulse_comments)
    all_comments = post_comment_items + pulse_comment_items

    new_comments = []
    new_questions = []

    for c in all_comments:
        c_h = c["hash"]
        if c_h not in seen_hashes:
            seen_hashes.add(c_h)
            new_comments.append(c)
            if c["is_question"]:
                new_questions.append(c)

    # Update state
    now = int(time.time())
    state["last_checked_at"] = now
    state["reactions_count"] = total_reactions
    state["comments_count"] = total_comments
    state["seen_comment_hashes"] = list(seen_hashes)
    if new_questions:
        state.setdefault("questions_found", []).extend(new_questions)

    save_state(state)

    report = {
        "timestamp": now,
        "target_url": target_url,
        "canonical_post_url": resolved_post_url,
        "pulse_url": DEFAULT_PULSE_URL,
        "reactions": {
            "current": total_reactions,
            "previous": prev_reactions,
            "delta": total_reactions - prev_reactions,
        },
        "comments": {
            "current": total_comments,
            "previous": prev_comments,
            "delta": total_comments - prev_comments,
            "new_count": len(new_comments),
            "new_questions_count": len(new_questions),
            "new_questions": new_questions,
        },
        "provenance_sha256": compute_file_sha256(__file__),
    }

    if verbose or not report.get("quiet", False):
        print("=" * 65)
        print("🔍 LinkedIn Post & Article Monitor Check (Policy v0.9.5)")
        print("=" * 65)
        print(f"Target URL:         {target_url}")
        print(f"Canonical Post URL: {resolved_post_url}")
        print(f"Reactions:          {total_reactions} (Δ {report['reactions']['delta']})")
        print(f"Comments:           {total_comments} (Δ {report['comments']['delta']})")
        print(f"New Questions:      {len(new_questions)}")
        if new_questions:
            print("\n⚠️ ATTENTION: Questions detected requiring author response:")
            for q in new_questions:
                print(f"  • {q['text']}")
        print(f"Provenance SHA256:  {report['provenance_sha256']}")
        print("=" * 65)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Post & Article Monitor (Policy v0.9.5)"
    )
    parser.add_argument(
        "--check-once",
        action="store_true",
        help="Run a single inspection check and exit",
    )
    parser.add_argument(
        "--post-url",
        default=DEFAULT_SHORTLINK,
        help="Target LinkedIn post URL or shortlink",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON format only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose diagnostics",
    )
    args = parser.parse_args()

    report = run_monitor_check(target_url=args.post_url, verbose=not args.json)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

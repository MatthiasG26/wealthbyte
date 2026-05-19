#!/usr/bin/env python3
"""
WealthByte Instagram Reel Auto-Poster
Generates and posts personal finance Reels to @getwealthbyte
"""

import anthropic
import requests
import random
import sys
import os
import time
import tempfile
from datetime import datetime, timezone, timedelta
from make_reel import create_reel

INSTAGRAM_USER_ID = os.environ.get("IG_USER_ID", "17841467067743259")
INSTAGRAM_TOKEN = os.environ.get("IG_TOKEN", "")

CONTENT_TYPES = [
    "money_fact",
    "mistake_to_avoid",
    "quick_tip",
    "how_it_works",
    "mindset",
]

HASHTAGS = (
    "#personalfinance #moneytips #financialliteracy #wealthbuilding #savemoney "
    "#moneymanagement #financetips #investingforbeginners #debtfree #financialfreedom "
    "#budgeting #moneymindset #richhabits #buildwealth #financialgoals"
)

# Module-level cleanup hook set by upload_video when GitHub release is used
_gh_cleanup_fn = None


def generate_content(content_type: str) -> str:
    client = anthropic.Anthropic()

    style = (
        "You write scripts for a premium faceless finance Instagram page (@getwealthbyte). "
        "The vibe is: old money, quiet luxury, cinematic, aspirational. NOT sigma memes or fake guru. "
        "HOOK RULES: Short. Mysterious. Creates status curiosity. Under 45 chars. No emojis in hook. "
        "Hook examples: 'Rich people avoid this.' | 'Luxury is usually silent.' | "
        "'Most people stay broke because of this.' | 'The wealthy think differently.' | "
        "'This is how money really works.' | 'The rich don't save. They invest.' | "
        "'Stop trading time for money.' | 'Your salary is keeping you poor.'\n"
        "BODY RULES: 3 lines max. Short punchy sentences. No filler. No cringe. Premium tone.\n"
        "END: One short question that sparks comments. Feels natural, not forced.\n"
        "FORMAT: Only output the lines separated by newlines. No labels, no quotes, no emojis except optionally one on the last line."
    )

    prompts = {
        "money_fact": (
            f"{style}\n\nWrite a script revealing a surprising financial truth most people don't know."
        ),
        "mistake_to_avoid": (
            f"{style}\n\nWrite a script about one money mistake that keeps people broke."
        ),
        "quick_tip": (
            f"{style}\n\nWrite a script sharing one powerful actionable wealth tip."
        ),
        "how_it_works": (
            f"{style}\n\nWrite a script explaining one financial concept (compound interest, index funds, "
            "credit score, assets vs liabilities, Roth IRA, net worth, etc.) in a premium, simple way."
        ),
        "mindset": (
            f"{style}\n\nWrite a script about a mindset difference between the wealthy and everyone else."
        ),
    }

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{prompts[content_type]}\n\n"
                    "Write ONLY the caption lines separated by newlines. No quotes."
                ),
            }
        ],
    )

    caption = message.content[0].text.strip()
    return f"{caption}\n\n{HASHTAGS}"


# ── GitHub Release upload (primary — reliable CDN Instagram can access) ────────

def _gh_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
    if not token:
        raise Exception("No GitHub token (GITHUB_TOKEN / GH_TOKEN) available")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _cleanup_old_releases(repo: str, hdrs: dict):
    """Delete vid-* releases older than 3 hours left over from previous runs."""
    try:
        rels = requests.get(
            f"https://api.github.com/repos/{repo}/releases",
            headers=hdrs, params={"per_page": 30}, timeout=15
        ).json()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
        for rel in rels:
            if not rel.get("tag_name", "").startswith("vid-"):
                continue
            created = datetime.fromisoformat(rel["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                requests.delete(
                    f"https://api.github.com/repos/{repo}/releases/{rel['id']}",
                    headers=hdrs, timeout=15
                )
                requests.delete(
                    f"https://api.github.com/repos/{repo}/git/refs/tags/{rel['tag_name']}",
                    headers=hdrs, timeout=15
                )
    except Exception as e:
        print(f"Release cleanup note: {e}")


def _delete_release(release_id: int, repo: str, hdrs: dict):
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/releases/{release_id}",
            headers=hdrs, timeout=15
        )
        tag = r.json().get("tag_name", "")
        requests.delete(
            f"https://api.github.com/repos/{repo}/releases/{release_id}",
            headers=hdrs, timeout=15
        )
        if tag:
            requests.delete(
                f"https://api.github.com/repos/{repo}/git/refs/tags/{tag}",
                headers=hdrs, timeout=15
            )
        print("Temporary GitHub release deleted.")
    except Exception as e:
        print(f"Release delete note: {e}")


def _upload_to_github_release(video_path: str) -> str:
    global _gh_cleanup_fn
    hdrs = _gh_headers()
    repo = os.environ.get("GITHUB_REPOSITORY", "MatthiasG26/wealthbyte")

    _cleanup_old_releases(repo, hdrs)

    tag = f"vid-{int(time.time())}"
    rel = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=hdrs,
        json={"tag_name": tag, "name": tag, "prerelease": True},
        timeout=30,
    ).json()
    if "id" not in rel:
        raise Exception(f"Release creation failed: {rel}")

    upload_url = rel["upload_url"].split("{")[0]
    with open(video_path, "rb") as f:
        asset = requests.post(
            f"{upload_url}?name=reel.mp4",
            headers={**hdrs, "Content-Type": "video/mp4"},
            data=f,
            timeout=120,
        ).json()

    url = asset.get("browser_download_url", "")
    if not url:
        raise Exception(f"Asset upload failed: {asset}")

    rel_id = rel["id"]
    _gh_cleanup_fn = lambda: _delete_release(rel_id, repo, hdrs)
    return url


# ── Fallback: litterbox (1-hour temp hosting) ──────────────────────────────────

def _upload_to_litterbox(video_path: str) -> str:
    with open(video_path, "rb") as f:
        r = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": f},
            timeout=90,
        )
    url = r.text.strip()
    if url.startswith("https://"):
        return url
    raise Exception(f"Litterbox returned: {r.text[:200]}")


def upload_video(video_path: str) -> str:
    """Upload video to a host Instagram can download from."""
    try:
        url = _upload_to_github_release(video_path)
        print(f"Video uploaded to GitHub CDN: {url}")
        return url
    except Exception as e:
        print(f"GitHub upload failed ({e}), trying litterbox...")

    url = _upload_to_litterbox(video_path)
    print(f"Video uploaded to litterbox: {url}")
    return url


def post_reel_to_instagram(caption: str, video_url: str) -> bool:
    # Step 1: Create reel container
    create_url = f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media"
    create_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": INSTAGRAM_TOKEN,
    }

    response = requests.post(create_url, data=create_payload)
    result = response.json()

    if "id" not in result:
        print(f"ERROR creating reel container: {result}")
        return False

    container_id = result["id"]
    print(f"Reel container created: {container_id}")

    # Step 2: Wait for processing then publish
    for attempt in range(18):  # up to 3 minutes
        time.sleep(10)
        status_url = f"https://graph.instagram.com/v21.0/{container_id}"
        status = requests.get(status_url, params={
            "fields": "status_code,error_message",
            "access_token": INSTAGRAM_TOKEN
        }).json()

        status_code = status.get("status_code", "")
        err_msg = status.get("error_message", "")
        print(f"Status check {attempt+1}: {status_code}" + (f" — {err_msg}" if err_msg else ""))

        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            print(f"Reel processing error: {status}")
            return False

    # Step 3: Publish
    publish_url = f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish"
    pub_response = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": INSTAGRAM_TOKEN,
    })
    pub_result = pub_response.json()

    if "id" not in pub_result:
        print(f"ERROR publishing reel: {pub_result}")
        return False

    print(f"Reel posted! Post ID: {pub_result['id']}")
    return True


def main():
    content_type = sys.argv[1] if len(sys.argv) > 1 else random.choice(CONTENT_TYPES)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} ET] Generating '{content_type}' reel...")

    caption = generate_content(content_type)
    print(f"Caption: {caption[:80]}...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name

    create_reel(caption, video_path)
    print(f"Reel video created: {video_path}")

    video_url = upload_video(video_path)

    success = post_reel_to_instagram(caption, video_url)
    os.unlink(video_path)

    # Clean up the temporary GitHub release now that Instagram is done with the URL
    if _gh_cleanup_fn:
        _gh_cleanup_fn()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
WealthByte Instagram Reel Auto-Poster
Generates and posts personal finance Reels to @getwealthbyte
"""

import requests
import random
import re
import sys
import os
import time
import tempfile
from datetime import datetime, timezone, timedelta
from make_reel import create_reel
from quotes import QUOTES

QUOTE_INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quote_index.txt")

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


def _read_quote_index() -> int:
    try:
        with open(QUOTE_INDEX_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_quote_index(idx: int):
    with open(QUOTE_INDEX_FILE, "w") as f:
        f.write(f"{idx}\n")


def get_next_quote() -> dict:
    """Pick the next quote in order, increment counter, return the quote dict."""
    idx = _read_quote_index()
    quote = QUOTES[idx % len(QUOTES)]
    _write_quote_index(idx + 1)
    print(f"Using quote {(idx % len(QUOTES)) + 1}/{len(QUOTES)} (run #{idx + 1})")
    return quote


def split_into_clips(text: str) -> list[str]:
    """Split a quote into ~5-10 short clips by sentence, then by comma if a sentence is long."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    clips = []
    for s in sentences:
        s_clean = s.rstrip(".!?")
        words = s_clean.split()
        if len(words) <= 7:
            clips.append(s_clean)
        else:
            # Split by comma for longer sentences
            parts = [p.strip() for p in s_clean.split(",") if p.strip()]
            if len(parts) > 1:
                clips.extend(parts)
            else:
                # No comma — split roughly in half
                mid = len(words) // 2
                clips.append(" ".join(words[:mid]))
                clips.append(" ".join(words[mid:]))
    return clips


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


def upload_to_youtube(video_path: str, title: str, description: str) -> bool:
    """Upload video as a YouTube Short using OAuth refresh token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("YouTube libraries not installed, skipping YouTube upload")
        return False

    client_id     = os.environ.get("YT_CLIENT_ID", "")
    client_secret = os.environ.get("YT_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        print("YouTube credentials not set, skipping YouTube upload")
        return False

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        creds.refresh(Request())
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": ["wealth", "money", "finance", "personalfinance",
                         "financialtips", "investing", "richhabits", "shorts"],
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4",
                                chunksize=-1, resumable=True)
        req = youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )
        response = req.execute()
        yt_id = response.get("id", "unknown")
        print(f"YouTube Short posted! https://youtube.com/shorts/{yt_id}")
        return True
    except Exception as e:
        print(f"YouTube upload error: {e}")
        return False


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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} ET] Building reel from quote list...")

    quote = get_next_quote()
    captions = split_into_clips(quote["text"])
    print(f"Captions ({len(captions)}): {captions}")

    ig_caption = f"{quote['text']}\n\n{quote['description']}\n\n{HASHTAGS}"
    print(f"IG caption: {ig_caption[:80]}...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name

    create_reel(captions, video_path)
    print(f"Reel video created: {video_path}")

    # YouTube — upload directly from file (no CDN needed)
    yt_title = captions[0] if captions else "Wealth tip"
    upload_to_youtube(video_path, yt_title, ig_caption)

    # Instagram — needs a public CDN URL
    video_url = upload_video(video_path)
    ig_success = post_reel_to_instagram(ig_caption, video_url)

    os.unlink(video_path)

    # Clean up the temporary GitHub release now that Instagram is done with the URL
    if _gh_cleanup_fn:
        _gh_cleanup_fn()

    if not ig_success:
        sys.exit(1)


if __name__ == "__main__":
    main()

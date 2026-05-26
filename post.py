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


def generate_captions(content_type: str) -> list[str]:
    """Generate 9-10 clip captions that together deliver one sharp wealth tip like a cinematic edit."""
    client = anthropic.Anthropic()

    topic_hints = {
        "money_fact": "a financial truth most people were never taught — something that feels like insider knowledge",
        "mistake_to_avoid": "one money habit that silently keeps people broke — something that makes the viewer feel called out",
        "quick_tip": "one counterintuitive wealth move — contradicts what most people believe",
        "how_it_works": "how one money concept works (compound interest, assets vs liabilities, index funds, net worth) — makes the viewer feel they just got an unlock",
        "mindset": "one quiet difference in how wealthy people think — old money mentality, not hustle culture",
    }

    prompt = f"""You create clip-by-clip caption sequences for a luxury wealth Instagram Reel (@getwealthbyte).
Vibe: old money, cinematic, genuinely wise. Like a mentor who made it speaking plainly.

Topic: {topic_hints.get(content_type, 'luxury wealth mindset')}

Write exactly 10 short captions that together deliver one real, actionable wealth insight.
Think of it as a quote broken across 10 clips — each line reveals the next part of the idea.

Structure:
1. Hook (clip 1): bold truth that stops a scroll. 4-7 words. Something most people have never heard phrased this way.
2. Build (clips 2-7): each line expands the idea with a specific, real, useful fact or insight. 2-5 words each. No filler.
3. Close (clips 8-10): land the lesson. Make the viewer walk away knowing something they can actually use.

Rules:
- Every line must be genuinely useful — not just aesthetic. Teach something real.
- Short lines only: 2-7 words max per clip
- Specific over vague: "Index funds beat 92% of managers." not "Invest wisely."
- No emoji. No hashtags. Statements only. No filler words.
- Vocabulary: clear and direct. Smart but accessible. Not corporate, not cringe.
- Do NOT use: "grind", "hustle", "boss", "sigma", "bro", "mindset", "journey"

EXAMPLE OUTPUT (topic: compound interest):
Most people misunderstand compound interest.
It's not about returns.
It's about time.
$300 a month at 22.
Becomes $1 million at 65.
Same money, started at 32.
Becomes $500,000.
Ten years costs you half.
Start before you're ready.
Time is the only edge.

OUTPUT FORMAT: One caption per line. No numbers. No quotes. No labels. Nothing else."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}],
    )

    lines = [l.strip() for l in message.content[0].text.strip().split("\n") if l.strip()]
    lines = lines[:12]
    while len(lines) < 8:
        lines.append("Build in silence.")
    print(f"Captions ({len(lines)}): {lines}")
    return lines


def generate_content(content_type: str) -> str:
    client = anthropic.Anthropic()

    style = """You write scripts for a premium faceless finance Instagram page (@getwealthbyte).
Vibe: old money, quiet luxury, cinematic. NOT sigma memes, fake guru, or grindset content.

THE HOOK IS EVERYTHING. It must:
- Stop someone mid-scroll in under 1 second
- Say something TRUE that people have never heard phrased this way
- Create a pattern interrupt — contradict a common belief or say the uncomfortable truth
- Be under 42 characters. No emoji. No question mark. Statement only.
- Make the viewer feel slightly called out OR suddenly curious

BEST PERFORMING HOOK FORMULAS:
• Uncomfortable truth: "Your job is designed to keep you dependent."
• Contradiction: "Saving money is making you poorer."
• Status flip: "The wealthy never talk about money."
• Simple fact that hits hard: "Time, not money, is the real currency."
• Reframe: "A Rolex isn't a flex. It's a lesson."
• Unexpected insider truth: "Banks profit when you don't invest."
• Identity challenge: "You're not broke. You're uninformed."
• Counterintuitive: "The less you show, the richer you look."
• Pattern interrupt: "Rich people hate cash."
• Quiet luxury truth: "Noise is cheap. Silence is expensive."

BODY (lines 2–4): Expand the hook with 3 SHORT punchy sentences.
Each line = one clear idea. No filler. No corporate speak. Premium, direct, true.

LAST LINE: A short question that makes people stop and comment. Genuine, not forced.

FORMAT: Output only the lines separated by newlines. No labels. No quotes. No intro text."""

    prompts = {
        "money_fact": (
            f"{style}\n\nWrite a script that reveals a financial truth most people were never taught. "
            "Something that feels like insider knowledge. The hook should feel like a secret."
        ),
        "mistake_to_avoid": (
            f"{style}\n\nWrite a script about one money behavior that silently keeps people broke. "
            "The hook should make someone feel slightly called out."
        ),
        "quick_tip": (
            f"{style}\n\nWrite a script with one wealth move that sounds counterintuitive but works. "
            "The hook should contradict conventional advice."
        ),
        "how_it_works": (
            f"{style}\n\nWrite a script that explains one concept — compound interest, assets vs liabilities, "
            "index funds, net worth, credit, Roth IRA — in a way that makes the viewer feel like "
            "they just learned something the wealthy already know. Hook should feel like an unlock."
        ),
        "mindset": (
            f"{style}\n\nWrite a script about one quiet difference in how wealthy people think vs everyone else. "
            "Not hustle culture. Old money mentality. The hook should be a truth that stings slightly."
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
    content_type = sys.argv[1] if len(sys.argv) > 1 else random.choice(CONTENT_TYPES)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} ET] Generating '{content_type}' reel...")

    captions = generate_captions(content_type)
    ig_caption = generate_content(content_type)
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

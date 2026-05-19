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
import tempfile
from datetime import datetime
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


def generate_content(content_type: str) -> str:
    client = anthropic.Anthropic()

    prompts = {
        "money_fact": (
            "Write a surprising personal finance fact for a short video.\n"
            "Line 1 (hook, under 60 chars): Start with '💡 Did you know?'\n"
            "Lines 2-4: Explain the fact simply, 1 sentence each.\n"
            "Last line: End with an engaging question."
        ),
        "mistake_to_avoid": (
            "Write about one money mistake people in their 20s-30s make.\n"
            "Line 1 (hook, under 60 chars): Start with '🚨 Stop doing this:'\n"
            "Lines 2-4: Explain the mistake and what to do instead.\n"
            "Last line: End with an engaging question."
        ),
        "quick_tip": (
            "Give one actionable money tip someone can use today.\n"
            "Line 1 (hook, under 60 chars): Start with '💰 Money tip:'\n"
            "Lines 2-4: Explain why it works and how to do it.\n"
            "Last line: End with an engaging question."
        ),
        "how_it_works": (
            "Explain one financial concept simply (compound interest, index funds, "
            "credit score, Roth IRA, emergency fund, etc.)\n"
            "Line 1 (hook, under 60 chars): Start with '📊 How [concept] works:'\n"
            "Lines 2-4: Explain in plain language.\n"
            "Last line: End with an engaging question."
        ),
        "mindset": (
            "Share a money mindset shift that separates wealthy from broke people.\n"
            "Line 1 (hook, under 60 chars): Start with '🧠 Wealthy people think differently:'\n"
            "Lines 2-4: Explain the mindset shift.\n"
            "Last line: End with an engaging question."
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


def upload_video(video_path: str) -> str:
    """Upload video to catbox.moe for free public hosting."""
    with open(video_path, "rb") as f:
        response = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f},
            timeout=60
        )
    url = response.text.strip()
    if url.startswith("https://"):
        return url
    raise Exception(f"Upload failed: {response.text}")


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
    import time
    for attempt in range(12):
        time.sleep(10)
        status_url = f"https://graph.instagram.com/v21.0/{container_id}"
        status = requests.get(status_url, params={
            "fields": "status_code",
            "access_token": INSTAGRAM_TOKEN
        }).json()

        status_code = status.get("status_code", "")
        print(f"Status check {attempt+1}: {status_code}")

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
    print(f"Video uploaded: {video_url}")

    success = post_reel_to_instagram(caption, video_url)
    os.unlink(video_path)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

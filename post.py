#!/usr/bin/env python3
"""
WealthByte Instagram Auto-Poster
Generates and posts personal finance content to @getwealthbyte
"""

import anthropic
import requests
import random
import sys
import os
from datetime import datetime

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

def generate_content(content_type: str) -> dict:
    client = anthropic.Anthropic()

    prompts = {
        "money_fact": (
            "Write a surprising, little-known personal finance fact that would shock most "
            "millennials or Gen Z. Format: Start with '💡 Did you know?' then 2-3 sentences. "
            "End with a practical takeaway. Keep it under 200 characters for the caption hook."
        ),
        "mistake_to_avoid": (
            "Write about one common money mistake people in their 20s-30s make that costs them "
            "thousands. Format: Start with '🚨 Stop doing this:' then explain the mistake and "
            "what to do instead. Under 220 characters for hook."
        ),
        "quick_tip": (
            "Give one actionable money tip someone can implement today to save or grow their wealth. "
            "Format: Start with '💰 Money tip:' then the tip. Under 200 characters for hook."
        ),
        "how_it_works": (
            "Explain one financial concept (compound interest, index funds, credit score, "
            "emergency fund, Roth IRA, etc.) in the simplest way possible for someone with "
            "zero finance knowledge. Format: Start with '📊 How [concept] works:' then explain "
            "in 3 bullet points."
        ),
        "mindset": (
            "Share a powerful money mindset shift that separates broke people from wealthy people. "
            "Format: Start with '🧠 Wealthy people think differently:' then the mindset shift. "
            "Under 220 characters for hook."
        ),
    }

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{prompts[content_type]}\n\n"
                    "Write ONLY the caption text. No quotes around it. "
                    "Make it punchy and shareable. End with a question to boost engagement."
                ),
            }
        ],
    )

    caption = message.content[0].text.strip()
    full_caption = f"{caption}\n\n{HASHTAGS}"

    return {"type": content_type, "caption": full_caption}


def get_image_url(content_type: str) -> str:
    # Finance-themed images from Pexels (Instagram-compatible public URLs)
    images = {
        "money_fact": "https://images.pexels.com/photos/4386431/pexels-photo-4386431.jpeg",
        "mistake_to_avoid": "https://images.pexels.com/photos/6801648/pexels-photo-6801648.jpeg",
        "quick_tip": "https://images.pexels.com/photos/4386373/pexels-photo-4386373.jpeg",
        "how_it_works": "https://images.pexels.com/photos/6802042/pexels-photo-6802042.jpeg",
        "mindset": "https://images.pexels.com/photos/6802049/pexels-photo-6802049.jpeg",
    }
    return images.get(content_type, images["quick_tip"])


def post_to_instagram(caption: str, image_url: str) -> bool:
    # Step 1: Create media container
    create_url = f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media"
    create_payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_TOKEN,
    }

    response = requests.post(create_url, data=create_payload)
    result = response.json()

    if "id" not in result:
        print(f"ERROR creating container: {result}")
        return False

    container_id = result["id"]
    print(f"Container created: {container_id}")

    # Step 2: Publish the container
    publish_url = f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": INSTAGRAM_TOKEN,
    }

    pub_response = requests.post(publish_url, data=publish_payload)
    pub_result = pub_response.json()

    if "id" not in pub_result:
        print(f"ERROR publishing: {pub_result}")
        return False

    print(f"Posted successfully! Post ID: {pub_result['id']}")
    return True


def main():
    content_type = sys.argv[1] if len(sys.argv) > 1 else random.choice(CONTENT_TYPES)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} ET] Generating '{content_type}' post...")

    content = generate_content(content_type)
    image_url = get_image_url(content_type)

    print(f"Caption preview: {content['caption'][:100]}...")
    success = post_to_instagram(content["caption"], image_url)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

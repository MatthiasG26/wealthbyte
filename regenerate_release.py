#!/usr/bin/env python3
"""
Regenerate the GitHub Release video for a given quote number using the
CURRENT code (latest pacing / caption splitter). Does NOT touch Instagram.

Usage:  python regenerate_release.py 19          # regenerate one
        python regenerate_release.py 19 25       # regenerate a range, inclusive
"""

import os, sys, tempfile, time, re, requests
from quotes import QUOTES
from post import (
    split_into_clips, HASHTAGS, _gh_headers,
    save_video_for_manual_youtube,
)
from make_reel import create_reel


def find_existing_release_by_quote_num(quote_num: int, repo: str, hdrs: dict):
    """Find a release whose tag starts with yt-NNN-... and return (id, tag) or (None, None)."""
    prefix = f"yt-{quote_num:03d}-"
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/releases",
            headers=hdrs, params={"per_page": 100, "page": page}, timeout=20,
        )
        items = r.json()
        if not isinstance(items, list) or not items:
            return None, None
        for rel in items:
            tag = rel.get("tag_name", "")
            if tag.startswith(prefix):
                return rel["id"], tag
        page += 1
        if page > 5:
            return None, None


def delete_release(release_id: int, tag: str, repo: str, hdrs: dict):
    requests.delete(
        f"https://api.github.com/repos/{repo}/releases/{release_id}",
        headers=hdrs, timeout=20,
    )
    if tag:
        requests.delete(
            f"https://api.github.com/repos/{repo}/git/refs/tags/{tag}",
            headers=hdrs, timeout=20,
        )


def regenerate(quote_num: int):
    if quote_num < 1 or quote_num > len(QUOTES):
        print(f"Skip {quote_num}: out of range (1..{len(QUOTES)})")
        return False

    quote = QUOTES[quote_num - 1]
    captions = split_into_clips(quote["text"])
    print(f"\n=== Regenerating #{quote_num:03d} ({len(captions)} clips) ===")
    for i, c in enumerate(captions):
        print(f"  {i+1:2d}. {c}")

    ig_caption = f"{quote['text']}\n\n{quote['description']}\n\n{HASHTAGS}"

    # Delete any existing release for this quote number
    repo = os.environ.get("GITHUB_REPOSITORY", "MatthiasG26/wealthbyte")
    hdrs = _gh_headers()
    rel_id, tag = find_existing_release_by_quote_num(quote_num, repo, hdrs)
    if rel_id:
        print(f"  Removing old release {tag}...")
        delete_release(rel_id, tag, repo, hdrs)
        time.sleep(1)

    # Build fresh video using CURRENT code
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name
    create_reel(captions, video_path)

    hook = captions[0] if captions else "Wealth tip"
    yt_title = f"{hook} #shorts"[:100]
    save_video_for_manual_youtube(video_path, quote_num, hook, ig_caption, yt_title)

    try:
        os.unlink(video_path)
    except Exception:
        pass
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_release.py <start> [end]")
        sys.exit(1)
    start = int(sys.argv[1])
    end = int(sys.argv[2]) if len(sys.argv) > 2 else start
    for n in range(start, end + 1):
        try:
            regenerate(n)
        except Exception as e:
            print(f"ERROR on #{n}: {e}")
            continue
    print("\nDone.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
WealthByte Long-Form Poster
Generates a long-form luxury wealth video (Brian voiceover + cinematic b-roll)
and uploads it to YouTube as a regular video (not a Short).
"""

import os, sys, tempfile, requests, time
from datetime import datetime
from make_longform import create_longform

HASHTAGS_LONGFORM = (
    "#wealth #personalfinance #money #investing #financialfreedom "
    "#oldmoney #luxury #financialliteracy #passiveincome #wealthbuilding"
)


def upload_longform_to_youtube(video_path: str, title: str, description: str) -> bool:
    """Upload as a regular (long-form) YouTube video using the existing OAuth refresh token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("YouTube libraries not installed")
        return False

    client_id     = os.environ.get("YT_CLIENT_ID", "")
    client_secret = os.environ.get("YT_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]):
        print("YouTube credentials not set, cannot upload")
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
                "tags": ["wealth", "money", "personal finance", "investing",
                         "financial freedom", "old money", "luxury",
                         "financial literacy", "wealth building"],
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4",
                                chunksize=8 * 1024 * 1024, resumable=True)
        req = youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )

        # Resumable upload loop with progress logging
        response = None
        while response is None:
            status, response = req.next_chunk()
            if status:
                print(f"  Upload {int(status.progress() * 100)}%")
        yt_id = response.get("id", "unknown")
        print(f"Long-form posted! https://youtube.com/watch?v={yt_id}")
        return True
    except Exception as e:
        print(f"YouTube upload error: {e}")
        return False


# Backup: save to a GitHub Release in case the YT upload fails for some reason
def _save_to_release(video_path: str, title: str, description: str) -> str | None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "MatthiasG26/wealthbyte")
    if not token:
        return None
    hdrs = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    tag = f"lf-{int(time.time())}"
    rel = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=hdrs,
        json={"tag_name": tag, "name": f"LONGFORM — {title}", "body": description},
        timeout=30,
    ).json()
    if "id" not in rel:
        return None
    upload_url = rel["upload_url"].split("{")[0]
    with open(video_path, "rb") as f:
        asset = requests.post(
            f"{upload_url}?name=longform.mp4",
            headers={**hdrs, "Content-Type": "video/mp4"},
            data=f, timeout=600,
        ).json()
    return asset.get("browser_download_url")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} ET] Generating long-form video...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        output_path = tmp.name

    result = create_longform(topic_hint=None, output_path=output_path)

    description = (
        f"{result['description']}\n\n"
        f"---\n\n"
        f"WealthByte — quiet luxury, real wealth.\n"
        f"Follow @getwealthbyte for daily insights.\n\n"
        f"{HASHTAGS_LONGFORM}"
    )

    success = upload_longform_to_youtube(output_path, result["title"], description)

    if not success:
        print("YT upload failed — archiving to GitHub Release as fallback")
        url = _save_to_release(output_path, result["title"], description)
        if url:
            print(f"Fallback download: {url}")

    try:
        os.unlink(output_path)
    except Exception:
        pass

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

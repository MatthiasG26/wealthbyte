#!/usr/bin/env python3
"""
WealthByte Reel Generator v3
Luxury background video + word-by-word text overlay + elegant music
"""

import os, random, tempfile, requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, VideoClip, ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip

WIDTH, HEIGHT = 1080, 1920
FPS = 30
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")

LUXURY_QUERIES = [
    "luxury lifestyle cinematic",
    "luxury car driving",
    "private jet interior",
    "penthouse city view night",
    "luxury yacht sailing ocean",
    "champagne pour slow motion",
    "sports car driving cinematic",
    "rooftop luxury city",
    "Lamborghini driving",
    "Monaco luxury cars",
    "Dubai skyline aerial",
    "luxury villa infinity pool",
    "luxury hotel lobby",
    "luxury watch closeup",
    "private pool villa sunset",
    "luxury fashion cinematic",
    "supercar aerial drone",
    "luxury resort aerial",
    "billionaire mansion aerial",
    "cinematic aerial city night",
]

MUSIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.mp3")


def get_font(size: int):
    paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def download_luxury_video() -> str:
    """Fetch a random luxury portrait video from Pexels."""
    query = random.choice(LUXURY_QUERIES)
    url = "https://api.pexels.com/videos/search"
    params = {"query": query, "per_page": 15, "orientation": "portrait"}
    headers = {"Authorization": PEXELS_KEY}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    data = resp.json()
    videos = data.get("videos", [])

    # Pick a random video that has a portrait HD file
    random.shuffle(videos)
    for v in videos:
        for f in v.get("video_files", []):
            w, h = f.get("width", 0), f.get("height", 0)
            if h > w and f.get("quality") in ("hd", "sd") and h >= 720:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                video_data = requests.get(f["link"], timeout=60).content
                tmp.write(video_data)
                tmp.close()
                print(f"Background: '{query}' — {v['id']}")
                return tmp.name

    raise Exception(f"No portrait video found for query: {query}")


def make_overlay_frame(bg_frame: np.ndarray, words: list, revealed: int,
                        font_size: int = 88, subtitle: str = "") -> np.ndarray:
    """Composite text overlay onto a background frame."""
    img = Image.fromarray(bg_frame).resize((WIDTH, HEIGHT))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Dark gradient overlay so text pops
    for i in range(HEIGHT):
        alpha = int(160 + 60 * (abs(i - HEIGHT // 2) / (HEIGHT // 2)))
        draw.line([(0, i), (WIDTH, i)], fill=(0, 0, 0, min(alpha, 210)))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw2 = ImageDraw.Draw(img)

    font = get_font(font_size)
    small = get_font(46)
    tiny = get_font(38)

    # Handle top left
    draw2.text((60, 80), "@getwealthbyte", font=tiny, fill=(255, 200, 0))

    # Group words into lines of ~4
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4:
            lines.append(cur); cur = []
    if cur:
        lines.append(cur)

    line_h = font_size + 30
    total_h = len(lines) * line_h
    y0 = (HEIGHT - total_h) // 2 - 60
    word_idx = 0

    for li, line_words in enumerate(lines):
        line_str = " ".join(line_words)
        bbox = draw2.textbbox((0, 0), line_str, font=font)
        line_w = bbox[2] - bbox[0]
        x = (WIDTH - line_w) // 2
        y = y0 + li * line_h
        cursor_x = x

        for word in line_words:
            w_bbox = draw2.textbbox((0, 0), word + " ", font=font)
            w_w = w_bbox[2] - w_bbox[0]

            if word_idx < revealed:
                color = (255, 255, 255)
            elif word_idx == revealed:
                color = (255, 200, 0)  # gold highlight on current word
            else:
                color = (130, 130, 130)

            # Shadow for readability
            draw2.text((cursor_x + 3, y + 3), word, font=font, fill=(0, 0, 0, 180))
            draw2.text((cursor_x, y), word, font=font, fill=color)
            cursor_x += w_w
            word_idx += 1

    # Subtitle
    if subtitle:
        bbox = draw2.textbbox((0, 0), subtitle, font=small)
        sw = bbox[2] - bbox[0]
        draw2.text(((WIDTH - sw) // 2, HEIGHT - 240), subtitle, font=small, fill=(255, 200, 0))

    # Bottom CTA
    cta = "Follow @getwealthbyte · Daily money tips"
    bbox = draw2.textbbox((0, 0), cta, font=tiny)
    cw = bbox[2] - bbox[0]
    draw2.text(((WIDTH - cw) // 2, HEIGHT - 160), cta, font=tiny, fill=(200, 200, 200))

    return np.array(img)


def create_reel(caption_text: str, output_path: str = "/tmp/reel.mp4") -> str:
    lines = [l.strip() for l in caption_text.split("\n")
             if l.strip() and not l.startswith("#")]
    hook = lines[0] if lines else "💰 Money tip"
    body_lines = [l for l in lines[1:5] if l]

    # Download luxury background
    bg_path = download_luxury_video()
    bg_clip = VideoFileClip(bg_path)

    # Make bg loop if shorter than needed
    secs_per_word = 0.27
    all_words = hook.split() + [w for l in body_lines for w in l.split()] + ["Follow", "for", "daily", "money", "tips"]
    total_duration = max(15, len(all_words) * secs_per_word + 5)

    if bg_clip.duration < total_duration:
        loops = int(total_duration / bg_clip.duration) + 1
        from moviepy import concatenate_videoclips as cv
        bg_clip = cv([bg_clip] * loops)
    bg_clip = bg_clip.subclipped(0, total_duration).resized((WIDTH, HEIGHT))

    clips = []
    current_t = [0.0]

    def make_segment(words, duration, subtitle="", font_size=88):
        n = len(words)
        def frame_fn(t):
            revealed = min(n, int(t / secs_per_word))
            bg_t = min(current_t[0] + t, bg_clip.duration - 0.1)
            bg_frame = bg_clip.get_frame(bg_t)
            return make_overlay_frame(bg_frame, words, revealed, font_size, subtitle)
        clip = VideoClip(frame_fn, duration=duration)
        current_t[0] += duration
        return clip

    # Hook
    hook_words = hook.split()
    clips.append(make_segment(hook_words,
                               max(2.5, len(hook_words) * secs_per_word + 0.8),
                               font_size=92))

    # Body
    for line in body_lines:
        bwords = line.split()
        if bwords:
            clips.append(make_segment(bwords,
                                       max(2.0, len(bwords) * secs_per_word + 0.6),
                                       font_size=80))

    # CTA
    cta_words = ["Follow", "for", "daily", "money", "tips", "that", "actually", "work."]
    clips.append(make_segment(cta_words, 2.5,
                               subtitle="🔔 Turn on notifications", font_size=84))

    video = concatenate_videoclips(clips, method="compose")

    # Add music
    if os.path.exists(MUSIC_PATH):
        try:
            audio = AudioFileClip(MUSIC_PATH)
            from moviepy import concatenate_audioclips
            if audio.duration < video.duration:
                loops = int(video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops)
            audio = audio.subclipped(0, video.duration).with_volume_scaled(0.75)
            video = video.with_audio(audio)
        except Exception as e:
            print(f"Audio note: {e}")

    video.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "main",
                       "-level", "4.0", "-movflags", "+faststart",
                       "-b:v", "4000k", "-b:a", "128k"],
        logger=None
    )
    os.unlink(bg_path)
    return output_path


if __name__ == "__main__":
    test = (
        "💰 Money tip: Delete shopping apps from your phone today.\n"
        "Out of sight means out of mind — and out of your bank account.\n"
        "Impulse purchases drop 30% when apps aren't one tap away.\n"
        "Have you deleted any apps to save money?"
    )
    out = create_reel(test)
    print(f"Reel saved: {out}")

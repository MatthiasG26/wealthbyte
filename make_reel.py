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
    # Supercars — generic terms Pexels actually has
    "supercar driving",
    "sports car driving",
    "exotic car",
    "luxury car interior",
    "supercar exhaust",
    "sports car close up",
    "luxury car detail",
    "supercar wheel",
    "red sports car",
    "black luxury car",
    # Watches
    "luxury watch closeup",
    "luxury watch wrist",
    "watch detail luxury",
    "expensive watch",
    # Lifestyle
    "private jet interior",
    "champagne pouring",
    "luxury yacht deck",
    "penthouse view",
    "luxury hotel suite",
    "luxury shopping",
    "rooftop pool luxury",
    "tailored suit",
    "cigar luxury",
    "luxury lifestyle",
]

MUSIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.mp3")

MUSIC_URLS = [
    # Chill house / smooth electronic (Kevin MacLeod, royalty free)
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Electro%20Cabello.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Cool%20Vibes.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Groove%20Grove.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Bass%20Vibes.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Backed%20Vibes%20Clean.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Smooth%20Lovin.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Chill%20Wave.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Deuces.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Dreamer.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Easy%20Lemon.mp3",
]


def ensure_music() -> str | None:
    """Download a fresh random track every run — no caching so music varies every post."""
    for url in random.sample(MUSIC_URLS, len(MUSIC_URLS)):
        try:
            print(f"Downloading music: {url.split('/')[-1]}")
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 100_000:
                with open(MUSIC_PATH, "wb") as f:
                    f.write(r.content)
                print(f"Music downloaded: {len(r.content)//1024}KB")
                return MUSIC_PATH
        except Exception as e:
            print(f"Music URL failed ({url.split('/')[-1]}): {e}")
    print("WARNING: all music downloads failed — reel will be silent")
    return None


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


def _fetch_one_video(query: str, used_ids: set) -> str | None:
    """Download one HD video from Pexels — any orientation, we'll crop landscape to portrait."""
    headers = {"Authorization": PEXELS_KEY}
    # Search without orientation filter so we get landscape car/watch content too
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "per_page": 20},
        headers=headers, timeout=15,
    )
    videos = resp.json().get("videos", [])
    random.shuffle(videos)
    for v in videos:
        if v["id"] in used_ids:
            continue
        # Prefer HD, pick the best file available
        best = None
        for f in v.get("video_files", []):
            w, h = f.get("width", 0), f.get("height", 0)
            q = f.get("quality", "")
            if q in ("hd", "sd") and max(w, h) >= 720:
                if best is None or max(w, h) > max(best.get("width", 0), best.get("height", 0)):
                    best = f
        if best:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(requests.get(best["link"], timeout=60).content)
            tmp.close()
            used_ids.add(v["id"])
            w, h = best.get("width", 0), best.get("height", 0)
            orientation = "portrait" if h > w else "landscape"
            print(f"Clip ({orientation}): '{query}' — {v['id']} ({w}x{h})")
            return tmp.name
    return None


def download_luxury_clips(needed_secs: float) -> list[str]:
    """Download multiple unique luxury clips until we have enough duration — no looping."""
    paths, used_ids = [], set()
    queries = random.sample(LUXURY_QUERIES, len(LUXURY_QUERIES))
    total = 0.0
    for query in queries:
        if total >= needed_secs:
            break
        path = _fetch_one_video(query, used_ids)
        if path:
            dur = VideoFileClip(path).duration
            paths.append(path)
            total += dur
            print(f"  → {dur:.1f}s collected ({total:.1f}/{needed_secs:.1f}s)")
    if not paths:
        raise Exception("No portrait videos found from Pexels")
    return paths


def make_overlay_frame(bg_frame: np.ndarray, words: list, revealed: int,
                        font_size: int = 88, subtitle: str = "") -> np.ndarray:
    """Composite text overlay onto a background frame."""
    img = Image.fromarray(bg_frame).resize((WIDTH, HEIGHT))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Light overlay — let the bright luxury visuals show through
    for i in range(HEIGHT):
        t = abs(i - HEIGHT // 2) / (HEIGHT // 2)
        alpha = int(90 + 60 * t)
        draw.line([(0, i), (WIDTH, i)], fill=(0, 0, 0, min(alpha, 140)))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw2 = ImageDraw.Draw(img)

    font = get_font(font_size)
    small = get_font(46)
    tiny = get_font(38)

    # Subtle watermark top left
    draw2.text((60, 80), "@getwealthbyte", font=tiny, fill=(200, 200, 200))

    # Group words into lines of ~3 — minimal, clean, readable
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3:
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

    # Bottom — minimal elegant CTA
    cta = "Follow for daily wealth insights"
    bbox = draw2.textbbox((0, 0), cta, font=tiny)
    cw = bbox[2] - bbox[0]
    draw2.text(((WIDTH - cw) // 2, HEIGHT - 160), cta, font=tiny, fill=(180, 180, 180))

    return np.array(img)


def create_reel(caption_text: str, output_path: str = "/tmp/reel.mp4") -> str:
    lines = [l.strip() for l in caption_text.split("\n")
             if l.strip() and not l.startswith("#")]
    hook = lines[0] if lines else "💰 Money tip"
    body_lines = [l for l in lines[1:5] if l]

    secs_per_word = 0.13
    all_words = hook.split() + [w for l in body_lines for w in l.split()] + ["Follow", "for", "more."]
    total_duration = max(15, len(all_words) * secs_per_word + 5)

    # Download multiple unique luxury clips — no looping the same footage
    from moviepy import concatenate_videoclips as cv
    bg_paths = download_luxury_clips(total_duration)
    def to_portrait(path):
        clip = VideoFileClip(path)
        if clip.w > clip.h:
            # Landscape — center-crop to 9:16 so subject stays centered
            target_w = int(clip.h * 9 / 16)
            x1 = (clip.w - target_w) // 2
            clip = clip.cropped(x1=x1, x2=x1 + target_w)
        return clip.resized((WIDTH, HEIGHT))

    raw_clips = [to_portrait(p) for p in bg_paths]
    bg_clip = cv(raw_clips, method="chain") if len(raw_clips) > 1 else raw_clips[0]
    bg_clip = bg_clip.subclipped(0, min(bg_clip.duration, total_duration + 2))

    clips = []
    current_t = [0.0]

    def make_segment(words, duration, subtitle="", font_size=88, instant=False):
        n = len(words)
        def frame_fn(t):
            if instant:
                # Show all words immediately — used for hook so it hits in frame 1
                revealed = n
            else:
                revealed = min(n, int(t / secs_per_word))
            bg_t = min(current_t[0] + t, bg_clip.duration - 0.1)
            bg_frame = bg_clip.get_frame(bg_t)
            return make_overlay_frame(bg_frame, words, revealed, font_size, subtitle)
        clip = VideoClip(frame_fn, duration=duration)
        current_t[0] += duration
        return clip

    # Hook — full text visible instantly so the first frame grabs attention
    hook_words = hook.split()
    clips.append(make_segment(hook_words,
                               max(2.5, len(hook_words) * secs_per_word + 1.2),
                               font_size=74, instant=True))

    # Body
    for line in body_lines:
        bwords = line.split()
        if bwords:
            clips.append(make_segment(bwords,
                                       max(2.0, len(bwords) * secs_per_word + 0.6),
                                       font_size=64))

    # CTA
    cta_words = ["Follow", "@getwealthbyte", "for", "more."]
    clips.append(make_segment(cta_words, 2.0,
                               subtitle="Turn on notifications", font_size=64))

    video = concatenate_videoclips(clips, method="compose")

    # Add music
    music_file = ensure_music()
    if music_file:
        try:
            from moviepy import concatenate_audioclips
            audio = AudioFileClip(music_file)
            if audio.duration < video.duration:
                loops = int(video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops)
            audio = audio.subclipped(0, video.duration).with_volume_scaled(1.8)
            video = video.with_audio(audio)
            print(f"Audio added, duration {video.duration:.1f}s")
        except Exception as e:
            print(f"Audio error: {e}")

    video.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "main",
                       "-level", "4.0", "-movflags", "+faststart",
                       "-b:v", "4000k", "-b:a", "128k"],
        logger=None
    )
    for p in bg_paths:
        try:
            os.unlink(p)
        except Exception:
            pass
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

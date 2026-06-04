#!/usr/bin/env python3
"""
WealthByte Reel Generator v4
Fast luxury montage: 8-12 clips × 0.7-1.5s, short captions, chill house music
"""

import os, random, tempfile, requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, VideoClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips

WIDTH, HEIGHT = 1080, 1920
FPS = 30
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")

LUXURY_QUERIES = [
    # Supercars
    "supercar driving",
    "sports car driving",
    "exotic car",
    "luxury car interior",
    "supercar exhaust",
    "sports car close up",
    "supercar wheel",
    "red sports car",
    "black luxury car",
    # Scenic drives
    "sports car coastal road",
    "car mountain road sunset",
    "supercar scenic drive",
    "convertible sunset drive",
    "car cliff road",
    # Watches
    "luxury watch closeup",
    "luxury watch wrist",
    "rolex watch",
    "watch detail",
    "expensive watch",
    # Lifestyle
    "champagne pouring",
    "private jet interior",
    "luxury yacht deck",
    "penthouse view",
    "luxury hotel suite",
    "rooftop pool luxury",
    "luxury lifestyle",
    "cigar luxury",
]

MUSIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.mp3")

MUSIC_URLS = [
    # Luxury piano instrumental — all confirmed live
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gymnopedie%20No%201.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gymnopedie%20No%202.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gymnopedie%20No%203.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Healing.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sad%20Trio.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Other%20Side%20of%20the%20Door.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Oppressive%20Gloom.mp3",
    "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Heartbreaking.mp3",
]


def ensure_music() -> str | None:
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
        "/home/runner/.fonts/Montserrat-Bold.ttf",              # CI download
        "/usr/local/share/fonts/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",                  # macOS
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fetch_one_video(query: str, used_ids: set) -> str | None:
    headers = {"Authorization": PEXELS_KEY}
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
            print(f"Clip: '{query}' — {v['id']} ({w}x{h})")
            return tmp.name
    return None


def to_portrait(path: str) -> VideoFileClip:
    clip = VideoFileClip(path)
    if clip.w > clip.h:
        target_w = int(clip.h * 9 / 16)
        x1 = (clip.w - target_w) // 2
        clip = clip.cropped(x1=x1, x2=x1 + target_w)
    return clip.resized((WIDTH, HEIGHT))


def _warm_grade(img: Image.Image) -> Image.Image:
    """Subtle warm cinematic color grade — slightly richer darks, warm shadows."""
    arr = np.array(img, dtype=np.float32)
    # Lift shadows slightly, push warm tone
    arr[..., 0] = np.clip(arr[..., 0] * 1.06 + 8, 0, 255)   # red up
    arr[..., 1] = np.clip(arr[..., 1] * 1.01 + 2, 0, 255)   # green slight
    arr[..., 2] = np.clip(arr[..., 2] * 0.92, 0, 255)        # blue down
    return Image.fromarray(arr.astype(np.uint8))


def make_caption_frame(bg_frame: np.ndarray, caption: str, is_hook: bool = False) -> np.ndarray:
    img = Image.fromarray(bg_frame).resize((WIDTH, HEIGHT))
    img = _warm_grade(img)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Vignette — dark edges, lighter center
    for i in range(HEIGHT):
        t = abs(i / HEIGHT - 0.5) * 2  # 0 at center, 1 at edges
        alpha = int(30 + 140 * (t ** 1.6))
        draw.line([(0, i), (WIDTH, i)], fill=(0, 0, 0, min(alpha, 180)))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw2 = ImageDraw.Draw(img)

    # Watermark — top left, subtle
    tiny = get_font(34)
    draw2.text((52, 72), "@getwealthbyte", font=tiny, fill=(210, 210, 210))

    # Font size: adaptive to caption length so longer text still fits cleanly
    word_count = len(caption.split())
    if word_count <= 4:
        font_size = 96 if is_hook else 76
    elif word_count <= 7:
        font_size = 82 if is_hook else 64
    elif word_count <= 11:
        font_size = 68 if is_hook else 54
    else:
        font_size = 58 if is_hook else 46
    font = get_font(font_size)

    # Word wrap
    words = caption.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        test = " ".join(cur)
        bbox = draw2.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > WIDTH - 100:
            if len(cur) > 1:
                lines.append(" ".join(cur[:-1]))
                cur = [w]
            else:
                lines.append(test)
                cur = []
    if cur:
        lines.append(" ".join(cur))

    line_h = font_size + 18
    total_h = len(lines) * line_h
    y0 = (HEIGHT - total_h) // 2 - 20

    for i, line in enumerate(lines):
        bbox = draw2.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (WIDTH - lw) // 2
        y = y0 + i * line_h

        # Multi-layer shadow for depth
        for sx, sy, salpha in [(5, 5, 200), (3, 3, 140), (1, 1, 80)]:
            draw2.text((x + sx, y + sy), line, font=font, fill=(0, 0, 0, salpha))

        # White text
        draw2.text((x, y), line, font=font, fill=(255, 255, 255))

    # Gold accent line under text
    line_y = y0 + total_h + 18
    accent_w = 120
    draw2.rectangle(
        [(WIDTH // 2 - accent_w // 2, line_y), (WIDTH // 2 + accent_w // 2, line_y + 3)],
        fill=(212, 175, 55)
    )

    # Bottom CTA — only on non-hook clips to avoid clutter on the opener
    if not is_hook:
        cta_font = get_font(36)
        cta = "Follow for daily wealth insights"
        bbox = draw2.textbbox((0, 0), cta, font=cta_font)
        cw = bbox[2] - bbox[0]
        draw2.text(((WIDTH - cw) // 2, HEIGHT - 120), cta, font=cta_font, fill=(170, 170, 170))

    return np.array(img)


def create_reel(captions: list[str], output_path: str = "/tmp/reel.mp4") -> str:
    n_clips = len(captions)
    used_ids: set = set()
    queries = random.sample(LUXURY_QUERIES, min(len(LUXURY_QUERIES), n_clips * 2))

    # Download one clip per caption
    bg_paths = []
    q_idx = 0
    for i in range(n_clips):
        path = None
        while path is None and q_idx < len(queries):
            path = _fetch_one_video(queries[q_idx], used_ids)
            q_idx += 1
        if path:
            bg_paths.append(path)
        else:
            print(f"WARNING: could not get clip {i+1}, reusing last")
            if bg_paths:
                bg_paths.append(bg_paths[-1])

    if not bg_paths:
        raise Exception("No luxury clips downloaded from Pexels")

    # Pad to n_clips if short
    while len(bg_paths) < n_clips:
        bg_paths.append(random.choice(bg_paths))

    clips = []
    for i, (path, caption) in enumerate(zip(bg_paths, captions)):
        is_hook = i == 0
        # Tight pacing for retention: ~0.32s per word + 0.55s baseline.
        # Short snappy lines fly by, hook gets a little extra to land the statement.
        word_count = max(1, len(caption.split()))
        base = max(1.3, word_count * 0.32 + 0.55)
        if is_hook:
            base += 0.7
        clip_dur = round(random.uniform(base - 0.1, base + 0.2), 2)
        raw = to_portrait(path)

        # Start from a random point in the clip
        max_start = max(0, raw.duration - clip_dur - 0.1)
        start = random.uniform(0, max_start) if max_start > 0 else 0
        segment = raw.subclipped(start, start + clip_dur)

        # Capture locals for closure
        seg_ref = segment
        cap_ref = caption
        hook_ref = is_hook

        def make_frame(t, _seg=seg_ref, _cap=cap_ref, _hook=hook_ref):
            bg_t = min(t, _seg.duration - 1/FPS)
            bg_frame = _seg.get_frame(bg_t)
            return make_caption_frame(bg_frame, _cap, is_hook=_hook)

        vc = VideoClip(make_frame, duration=clip_dur)
        clips.append(vc)
        print(f"Segment {i+1}/{n_clips} {'[HOOK]' if is_hook else ''}: '{caption}' ({clip_dur:.2f}s)")

    video = concatenate_videoclips(clips, method="chain")

    # Music
    music_file = ensure_music()
    if music_file:
        try:
            audio = AudioFileClip(music_file)
            if audio.duration < video.duration:
                loops = int(video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops)
            audio = audio.subclipped(0, video.duration).with_volume_scaled(1.6)
            video = video.with_audio(audio)
            print(f"Audio added, total duration: {video.duration:.1f}s")
        except Exception as e:
            print(f"Audio error: {e}")

    video.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "main",
                       "-level", "4.0", "-movflags", "+faststart",
                       "-b:v", "4000k", "-b:a", "128k"],
        logger=None
    )

    unique_paths = list(set(bg_paths))
    for p in unique_paths:
        try:
            os.unlink(p)
        except Exception:
            pass

    return output_path


if __name__ == "__main__":
    test_captions = [
        "Wealth is silent.",
        "Rich people buy assets.",
        "Your job has a ceiling.",
        "Invest before you spend.",
        "Time compounds too.",
        "Debt kills freedom.",
        "Own, don't rent.",
        "Think in decades.",
        "The wealthy stay quiet.",
        "Build while they sleep.",
    ]
    out = create_reel(test_captions)
    print(f"Reel saved: {out}")

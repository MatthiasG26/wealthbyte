#!/usr/bin/env python3
"""
WealthByte Reel Generator v2
Word-by-word kinetic text reveal, 9:16 vertical, black bg, gold accents
Lo-fi/motivational background music
"""

import os
import math
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, VideoClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip

WIDTH, HEIGHT = 1080, 1920
FPS = 30
BG_COLOR = (5, 5, 5)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (255, 200, 0)
DIM_COLOR = (100, 100, 100)

MUSIC_PATH = os.path.join(os.path.dirname(__file__), "music.mp3")


def get_font(size: int):
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_word_reveal_frame(words: list, revealed: int, font_size: int = 90,
                            subtitle: str = "", show_handle: bool = True) -> np.ndarray:
    """Render frame with words revealed up to `revealed` index."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = get_font(font_size)
    small = get_font(44)
    tiny = get_font(36)

    # Handle / watermark top left
    if show_handle:
        draw.text((60, 72), "@getwealthbyte", font=tiny, fill=ACCENT_COLOR)

    # Wrap words into lines of ~4 words
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= 4:
            lines.append(current)
            current = []
    if current:
        lines.append(current)

    # Calculate total text block height
    line_h = font_size + 28
    total_h = len(lines) * line_h
    y_start = (HEIGHT - total_h) // 2 - 60

    word_idx = 0
    for line_words in lines:
        # Calculate line width
        line_str = " ".join(line_words)
        bbox = draw.textbbox((0, 0), line_str, font=font)
        line_w = bbox[2] - bbox[0]
        x = (WIDTH - line_w) // 2
        y = y_start + lines.index(line_words) * line_h

        # Draw each word in line
        cursor_x = x
        for word in line_words:
            w_bbox = draw.textbbox((0, 0), word + " ", font=font)
            w_width = w_bbox[2] - w_bbox[0]

            if word_idx < revealed:
                color = TEXT_COLOR
            elif word_idx == revealed:
                color = ACCENT_COLOR  # current word highlights gold
            else:
                color = DIM_COLOR

            draw.text((cursor_x, y), word, font=font, fill=color)
            cursor_x += w_width
            word_idx += 1

    # Subtitle
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=small)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) // 2, HEIGHT - 240), subtitle, font=small, fill=ACCENT_COLOR)

    # CTA at bottom
    cta = "Follow @getwealthbyte for daily money tips"
    bbox = draw.textbbox((0, 0), cta, font=tiny)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT - 160), cta, font=tiny, fill=(140, 140, 140))

    return np.array(img)


def make_stat_frame(stat_text: str, sub: str = "") -> np.ndarray:
    """Full-screen bold single stat."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    big_font = get_font(120)
    small_font = get_font(52)
    tiny = get_font(36)

    draw.text((60, 72), "@getwealthbyte", font=tiny, fill=ACCENT_COLOR)

    lines = textwrap.wrap(stat_text, width=14)
    total_h = len(lines) * 150
    y = (HEIGHT - total_h) // 2 - 80
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=big_font)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) // 2, y), line, font=big_font, fill=ACCENT_COLOR)
        y += 150

    if sub:
        bbox = draw.textbbox((0, 0), sub, font=small_font)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) // 2, HEIGHT - 280), sub, font=small_font, fill=TEXT_COLOR)

    cta = "Follow @getwealthbyte for daily money tips"
    bbox = draw.textbbox((0, 0), cta, font=tiny)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT - 160), cta, font=tiny, fill=(140, 140, 140))

    return np.array(img)


def create_reel(caption_text: str, output_path: str = "/tmp/reel.mp4") -> str:
    lines = [l.strip() for l in caption_text.split("\n") if l.strip() and not l.startswith("#")]

    hook = lines[0] if lines else "💰 Money tip"
    body_lines = lines[1:5] if len(lines) > 1 else []

    clips = []
    secs_per_word = 0.28  # word reveal speed

    # --- Hook slide: word-by-word reveal ---
    hook_words = hook.split()
    n_hook = len(hook_words)
    hook_duration = max(2.5, n_hook * secs_per_word + 0.8)

    def hook_frame(t):
        revealed = min(n_hook, int(t / secs_per_word))
        return make_word_reveal_frame(hook_words, revealed, font_size=96, subtitle="")

    hook_clip = VideoClip(lambda t: hook_frame(t), duration=hook_duration)
    clips.append(hook_clip)

    # --- Body slides ---
    for body_line in body_lines:
        body_words = body_line.split()
        if not body_words:
            continue
        n = len(body_words)
        duration = max(2.0, n * secs_per_word + 0.6)

        frame_fn = (lambda words, count: lambda t: make_word_reveal_frame(
            words, min(count, int(t / secs_per_word)), font_size=80
        ))(body_words, n)

        clip = VideoClip(frame_fn, duration=duration)
        clips.append(clip)

    # --- CTA slide ---
    cta_words = ["Follow", "for", "daily", "money", "tips", "that", "actually", "work."]
    cta_duration = 2.5
    cta_frame = make_word_reveal_frame(cta_words, len(cta_words), font_size=86,
                                        subtitle="🔔 Turn on notifications")
    clips.append(ImageClip(cta_frame, duration=cta_duration))

    # Concatenate
    video = concatenate_videoclips(clips, method="compose")

    # Add music if available
    if os.path.exists(MUSIC_PATH):
        try:
            audio = AudioFileClip(MUSIC_PATH)
            # Loop audio to match video length, trim to video duration, lower volume
            total = video.duration
            if audio.duration < total:
                import math
                loops = math.ceil(total / audio.duration)
                from moviepy import concatenate_audioclips
                audio = concatenate_audioclips([audio] * loops)
            audio = audio.subclipped(0, total).with_effects(
                [__import__('moviepy.audio.fx', fromlist=['MultiplyVolume']).MultiplyVolume(0.18)]
            )
            video = video.with_audio(audio)
        except Exception as e:
            print(f"Audio skipped: {e}")

    video.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None)
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

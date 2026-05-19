#!/usr/bin/env python3
"""
WealthByte Reel Generator
Creates kinetic text Reels for @getwealthbyte
9:16 vertical format, black background, white animated text
"""

import textwrap
import os
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip

WIDTH, HEIGHT = 1080, 1920
FPS = 30
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (255, 215, 0)  # gold


def wrap_text(text: str, max_chars: int = 28) -> list[str]:
    return textwrap.wrap(text, width=max_chars)


def make_frame(lines: list[str], subtitle: str, progress: float, font_size: int = 72) -> np.ndarray:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        small_font = ImageFont.truetype(font_path, 42) if font_path else font
        accent_font = ImageFont.truetype(font_path, 36) if font_path else font
    except Exception:
        font = ImageFont.load_default()
        small_font = font
        accent_font = font

    # Draw watermark
    draw.text((54, 80), "@getwealthbyte", font=accent_font, fill=ACCENT_COLOR)

    # Draw main text lines centered
    total_height = len(lines) * (font_size + 20)
    y_start = (HEIGHT - total_height) // 2 - 80

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        y = y_start + i * (font_size + 20)

        # Fade in effect per line
        line_progress = max(0, min(1, progress * len(lines) - i))
        alpha = int(255 * line_progress)
        color = (alpha, alpha, alpha)
        draw.text((x, y), line, font=font, fill=color)

    # Draw subtitle
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=small_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, HEIGHT - 220), subtitle, font=small_font, fill=ACCENT_COLOR)

    # Bottom CTA
    cta = "Follow for daily money tips"
    bbox = draw.textbbox((0, 0), cta, font=accent_font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT - 140), cta, font=accent_font, fill=(180, 180, 180))

    return np.array(img)


def create_reel(caption_text: str, output_path: str = "/tmp/reel.mp4") -> str:
    # Split caption into hook + body
    lines_raw = caption_text.split("\n")[0]  # first line = hook
    hook_lines = wrap_text(lines_raw, max_chars=22)

    # Build slides
    clips = []

    # Slide 1: Hook (3 seconds)
    def hook_frame(t):
        progress = min(1.0, t / 1.5)
        return make_frame(hook_lines, "💰 WealthByte", progress, font_size=80)

    hook_clip = ImageClip(hook_frame(2.9), duration=3.5)
    clips.append(hook_clip)

    # Slide 2-N: Body content lines
    body_lines = caption_text.split("\n")
    body_text = " ".join(body_lines[1:]).strip()
    body_text = body_text.replace("#", "").strip()

    # Split body into chunks of ~3 lines each
    all_words = body_text.split()
    chunk_size = 15
    chunks = [all_words[i:i+chunk_size] for i in range(0, min(len(all_words), 45), chunk_size)]

    for chunk in chunks:
        chunk_text = " ".join(chunk)
        chunk_lines = wrap_text(chunk_text, max_chars=26)
        frame = make_frame(chunk_lines, "", 1.0, font_size=64)
        clip = ImageClip(frame, duration=2.5)
        clips.append(clip)

    # Slide: CTA
    cta_lines = ["Follow for", "daily money tips", "that actually work."]
    frame = make_frame(cta_lines, "🔔 Turn on notifications", 1.0, font_size=72)
    cta_clip = ImageClip(frame, duration=2.5)
    clips.append(cta_clip)

    # Concatenate all clips
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(output_path, fps=FPS, codec="libx264", audio=False, logger=None)

    return output_path


if __name__ == "__main__":
    test_caption = (
        "💰 Money tip: Set up a $5/day automatic transfer to savings RIGHT NOW.\n"
        "That's $1,825 by next year — without thinking about it.\n"
        "Small consistent actions beat big one-time efforts every time.\n"
        "Are you automating your savings yet?"
    )
    out = create_reel(test_caption)
    print(f"Reel saved to {out}")

#!/usr/bin/env python3
"""
WealthByte Long-Form YouTube Video Generator
8-10 minute faceless wealth content:
  Claude script  →  Brian (ElevenLabs) voiceover  →  Pexels b-roll montage
"""

import os, sys, json, random, tempfile, requests, re
import anthropic
from moviepy import (
    VideoFileClip, concatenate_videoclips, AudioFileClip,
    CompositeAudioClip, concatenate_audioclips,
)

from make_reel import ensure_music

WIDTH, HEIGHT = 1920, 1080  # 16:9 for YouTube long-form
FPS = 30
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
BRIAN_VOICE_ID = "nPczCjzI2devNBz1zQrb"

LUXURY_QUERIES_LONGFORM = [
    # Wealth aesthetic
    "luxury watch closeup", "rolex watch", "expensive watch", "watch detail",
    "luxury car interior", "supercar driving", "sports car coastal road",
    "luxury yacht deck", "private jet interior", "champagne pouring",
    "penthouse view", "luxury hotel suite", "rooftop pool luxury",
    "cigar luxury", "whiskey glass", "luxury dinner",
    # Business / wealth working
    "businessman walking city", "stock market chart", "trading screens",
    "city skyline night", "wall street", "office skyscraper",
    "money counting", "gold bars", "bank vault",
    # Lifestyle
    "exotic vacation", "private beach", "mansion exterior",
    "luxury bedroom", "marble interior",
    # Time / cinematic
    "sunset cityscape", "timelapse city", "fireplace closeup",
    "books library", "vintage car",
]


# ────────────────────────────────────────────────────────────────────────
# Script generation (Claude)
# ────────────────────────────────────────────────────────────────────────

TOPIC_POOL = [
    "Why most people will never get rich (and what the wealthy do differently)",
    "How the wealthy actually use debt (it's not what you think)",
    "The quiet habits of old money families",
    "Why compound interest is the most powerful force in finance",
    "How to think like a millionaire (even if you're broke)",
    "Why high income doesn't equal wealth",
    "The truth about luxury (what really matters)",
    "How successful people manage their time",
    "Why most lottery winners go broke within five years",
    "The mindset that separates the rich from the poor",
    "How the wealthy raise their kids differently",
    "What the rich do every morning that you don't",
    "Why your job will never make you rich",
    "The hidden cost of looking rich",
    "How to build wealth on an average salary",
]


def generate_script(topic_hint: str | None = None) -> dict:
    """Generate a ~1,500-word long-form script with title, description, b-roll queries."""
    client = anthropic.Anthropic()
    topic = topic_hint or random.choice(TOPIC_POOL)

    prompt = f"""You are writing a long-form YouTube script for a luxury wealth channel called WealthByte.
Vibe: cinematic, old money, quiet luxury. Documentary narrated by a calm, wise mentor (think Brian — deep, classy, resonant).

TOPIC: {topic}

Write the FULL spoken script. Target ~1,500 words (will run 9-10 minutes with voiceover at natural pace).

STRUCTURE:
1. HOOK (first ~40 words, ~15 seconds): bold opening that stops the scroll. Pattern interrupt, uncomfortable truth, or counterintuitive fact. No "Hey what's up guys."
2. PROMISE (~80 words, next 30s): tell the viewer what they'll learn and why it actually matters to their life.
3. BODY (6-8 sections, ~150-200 words each): each section reveals a specific principle, framework, or truth. Use real examples, specific numbers, named concepts. Each section should land one idea cleanly.
4. CONCLUSION (~120 words): tie it together with a final insight. Soft, classy CTA — "If this resonates, subscribe." NOT "SMASH THAT LIKE BUTTON."

STYLE RULES:
- Write for the EAR, not the eye. Short sentences. Natural pauses. Read it out loud in your head.
- Authoritative but humble. Like a mentor who has lived it.
- Specific over vague: "Index funds beat 92% of active managers over 20 years" — not "Smart investing wins."
- No corporate speak. No "in conclusion." No hype words.
- AVOID THESE WORDS: hustle, grind, sigma, boss, journey, blueprint, level up, game changer
- No stage directions like [PAUSE] or [MUSIC]. Just the words to be spoken.
- Open with the hook directly. Do NOT introduce yourself or the channel at the start.

OUTPUT — return ONLY valid JSON, no markdown, no commentary, exactly this format:
{{
  "title": "Compelling YouTube title under 70 chars, no clickbait, no all-caps",
  "description": "2-3 sentence description for the YouTube description box",
  "script": "the full ~1500-word narration as one string",
  "search_queries": ["8-12 Pexels b-roll queries that visually match the script's vibe", "e.g. 'luxury watch closeup'", "'penthouse city view'"]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    print(f"Title: {data['title']}")
    print(f"Script length: {len(data['script'].split())} words, {len(data['script'])} chars")
    return data


# ────────────────────────────────────────────────────────────────────────
# Voiceover (ElevenLabs — Brian)
# ────────────────────────────────────────────────────────────────────────

def generate_voiceover(script_text: str, output_path: str) -> float:
    if not ELEVENLABS_KEY:
        raise Exception("ELEVENLABS_API_KEY not set")

    print(f"Generating Brian voiceover ({len(script_text)} chars)...")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{BRIAN_VOICE_ID}",
        headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
        json={
            "text": script_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.75,
                "style": 0.2,
                "use_speaker_boost": True,
            },
        },
        timeout=600,
    )
    if r.status_code != 200:
        raise Exception(f"ElevenLabs error {r.status_code}: {r.text[:400]}")

    with open(output_path, "wb") as f:
        f.write(r.content)

    audio = AudioFileClip(output_path)
    duration = audio.duration
    audio.close()
    print(f"Voiceover: {duration:.1f}s ({len(r.content)//1024}KB)")
    return duration


# ────────────────────────────────────────────────────────────────────────
# B-roll (Pexels)
# ────────────────────────────────────────────────────────────────────────

def _fetch_broll_clip(query: str, used_ids: set) -> tuple[str, float] | None:
    if not PEXELS_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            headers={"Authorization": PEXELS_KEY}, timeout=15,
        )
        videos = resp.json().get("videos", [])
    except Exception as e:
        print(f"  Pexels search failed for '{query}': {e}")
        return None

    random.shuffle(videos)
    for v in videos:
        if v["id"] in used_ids:
            continue
        best = None
        for f in v.get("video_files", []):
            w, h = f.get("width", 0), f.get("height", 0)
            if w >= 1280 and h >= 720 and w >= h:
                if best is None or w > best.get("width", 0):
                    best = f
        if not best:
            continue
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(requests.get(best["link"], timeout=90).content)
            tmp.close()
            vc = VideoFileClip(tmp.name)
            d = vc.duration
            vc.close()
            used_ids.add(v["id"])
            print(f"  B-roll: '{query}' — {v['id']} ({best['width']}x{best['height']}, {d:.1f}s)")
            return tmp.name, d
        except Exception:
            continue
    return None


def gather_broll(queries: list[str], total_duration_needed: float) -> list[tuple[str, float]]:
    used_ids: set = set()
    clips: list[tuple[str, float]] = []
    all_queries = list(dict.fromkeys(list(queries) + LUXURY_QUERIES_LONGFORM))
    random.shuffle(all_queries)

    total = 0.0
    q_idx = 0
    safety = 0
    while total < total_duration_needed and safety < len(all_queries) * 4:
        q = all_queries[q_idx % len(all_queries)]
        q_idx += 1
        safety += 1
        result = _fetch_broll_clip(q, used_ids)
        if result:
            clips.append(result)
            total += result[1]
    return clips


# ────────────────────────────────────────────────────────────────────────
# Video assembly
# ────────────────────────────────────────────────────────────────────────

def to_landscape(path: str) -> VideoFileClip:
    clip = VideoFileClip(path)
    target_ratio = WIDTH / HEIGHT
    cur_ratio = clip.w / clip.h
    if cur_ratio > target_ratio + 0.01:
        target_w = int(clip.h * target_ratio)
        x1 = (clip.w - target_w) // 2
        clip = clip.cropped(x1=x1, x2=x1 + target_w)
    elif cur_ratio < target_ratio - 0.01:
        target_h = int(clip.w / target_ratio)
        y1 = (clip.h - target_h) // 2
        clip = clip.cropped(y1=y1, y2=y1 + target_h)
    return clip.resized((WIDTH, HEIGHT))


def build_video(audio_path: str, broll: list[tuple[str, float]], output_path: str):
    print("Building video segments...")
    voiceover = AudioFileClip(audio_path)
    total_duration = voiceover.duration

    # Layered ambient music underneath voice
    music_file = ensure_music()
    if music_file:
        try:
            music = AudioFileClip(music_file)
            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)
            music = music.subclipped(0, total_duration).with_volume_scaled(0.12)
            final_audio = CompositeAudioClip([voiceover.with_volume_scaled(1.0), music])
        except Exception as e:
            print(f"Music layer failed: {e}")
            final_audio = voiceover
    else:
        final_audio = voiceover

    # Cut b-roll into 6-12s segments until we cover the audio
    segments = []
    accumulated = 0.0
    clip_idx = 0
    while accumulated < total_duration and clip_idx < len(broll) * 6:
        path, dur = broll[clip_idx % len(broll)]
        seg_len = random.uniform(6.5, 11.5)
        seg_len = min(seg_len, max(2.0, dur - 0.4))
        seg_len = min(seg_len, total_duration - accumulated)
        if seg_len < 1.5:
            break
        try:
            raw = to_landscape(path)
            max_start = max(0, raw.duration - seg_len - 0.1)
            start = random.uniform(0, max_start) if max_start > 0 else 0
            seg = raw.subclipped(start, start + seg_len).without_audio()
            segments.append(seg)
            accumulated += seg_len
        except Exception as e:
            print(f"  Segment skip: {e}")
        clip_idx += 1

    if not segments:
        raise Exception("No usable b-roll segments built")

    print(f"Concatenating {len(segments)} segments ({accumulated:.0f}s of {total_duration:.0f}s)...")
    video = concatenate_videoclips(segments, method="chain")
    video = video.subclipped(0, min(video.duration, total_duration)).with_audio(final_audio)

    print(f"Rendering to {output_path}...")
    video.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-profile:v", "main",
                       "-level", "4.0", "-movflags", "+faststart",
                       "-b:v", "6000k", "-b:a", "192k"],
        logger=None, threads=2,
    )

    for path, _ in broll:
        try:
            os.unlink(path)
        except Exception:
            pass


def create_longform(topic_hint: str | None = None, output_path: str = "/tmp/longform.mp4") -> dict:
    print("=" * 60)
    print("WealthByte Long-Form Generator")
    print("=" * 60)

    data = generate_script(topic_hint)

    voice_path = "/tmp/voiceover.mp3"
    audio_duration = generate_voiceover(data["script"], voice_path)

    print(f"Fetching b-roll for {audio_duration:.0f}s of audio...")
    broll = gather_broll(data["search_queries"], audio_duration * 1.15)
    if not broll:
        raise Exception("No b-roll clips downloaded from Pexels")
    print(f"Got {len(broll)} clips, total {sum(d for _, d in broll):.0f}s")

    build_video(voice_path, broll, output_path)

    try:
        os.unlink(voice_path)
    except Exception:
        pass

    data["output_path"] = output_path
    data["duration"] = audio_duration
    return data


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    result = create_longform(topic)
    print(f"\nDone: {result['output_path']}")
    print(f"Title: {result['title']}")

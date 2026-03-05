#!/usr/bin/env python3

import os
import json
import shutil
import subprocess
import argparse
import random
from pathlib import Path
from PIL import Image

FPS = 25

# ======================
# UTILS
# ======================

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_total_duration(timeline):
    return max(segment["end"] for segment in timeline)


def time_to_frame(t):
    return int(t * FPS)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


# ======================
# IMAGE LOADERS
# ======================

def load_mouth_image(viseme, mouths_dir):
    path = os.path.join(mouths_dir, f"{viseme}.png")
    if not os.path.exists(path):
        raise ValueError(f"Viseme image not found: {path}")
    return Image.open(path).convert("RGBA")


def load_eye_image(state, eyes_dir):
    path = os.path.join(eyes_dir, f"{state}.png")
    if not os.path.exists(path):
        raise ValueError(f"Eye image not found: {path}")
    return Image.open(path).convert("RGBA")


# ======================
# EYE TIMELINE GENERATOR
# ======================

def generate_eye_timeline(duration, eyes_config):

    min_interval = eyes_config.get("min_blink_interval", 3.0)
    max_interval = eyes_config.get("max_blink_interval", 5.5)
    min_duration = eyes_config.get("min_blink_duration", 0.18)
    max_duration = eyes_config.get("max_blink_duration", 0.28)

    timeline = []
    current_time = 0.0

    while current_time < duration:

        interval = random.uniform(min_interval, max_interval)
        blink_duration = random.uniform(min_duration, max_duration)

        blink_start = current_time + interval
        blink_end = blink_start + blink_duration

        if blink_start >= duration:
            timeline.append({
                "start": current_time,
                "end": duration,
                "eye": "OPEN"
            })
            break

        # OPEN phase
        timeline.append({
            "start": current_time,
            "end": blink_start,
            "eye": "OPEN"
        })

        # Blink breakdown
        half_phase = blink_duration * 0.3
        closed_phase = blink_duration * 0.4

        timeline.append({
            "start": blink_start,
            "end": blink_start + half_phase,
            "eye": "HALF-OPEN"
        })

        timeline.append({
            "start": blink_start + half_phase,
            "end": blink_start + half_phase + closed_phase,
            "eye": "CLOSED"
        })

        timeline.append({
            "start": blink_start + half_phase + closed_phase,
            "end": blink_end,
            "eye": "HALF-OPEN"
        })

        current_time = blink_end

    return timeline


# ======================
# MAIN RENDER
# ======================

def render(episode):

    BASE_IMAGE_PATH = f"episodes/images/{episode}.png"
    TIMELINE_PATH = f"episodes/visemes-timeline/{episode}.json"
    POSITION_PATH = f"episodes/positions-mapping/{episode}.json"
    AUDIO_PATH = f"episodes/audios/{episode}.mp3"

    OUTPUT_DIR = "episodes/videos"
    OUTPUT_VIDEO = f"{OUTPUT_DIR}/{episode}.mp4"
    FRAMES_DIR = f"tmp_frames_{episode}"

    print("Loading data...")

    timeline = load_json(TIMELINE_PATH)
    position = load_json(POSITION_PATH)

    base_image = Image.open(BASE_IMAGE_PATH).convert("RGBA")

    total_duration = get_total_duration(timeline)
    total_frames = time_to_frame(total_duration)

    ensure_dir(FRAMES_DIR)
    ensure_dir(OUTPUT_DIR)

    # Emotions
    emotion_1 = position.get("emotion_1", "HAPPY")
    emotion_2 = position.get("emotion_2", emotion_1)
    transition_time = position.get("emotion_transition_time", float("inf"))

    # Generate procedural eye animation
    eyes_config = position.get("eyes", {})
    eye_timeline = generate_eye_timeline(total_duration, eyes_config)

    # Caches
    mouth_cache = {}
    eye_cache = {}

    for frame_number in range(total_frames):

        current_time = frame_number / FPS

        # Emotion selection
        if current_time < transition_time:
            current_emotion = emotion_1
        else:
            current_emotion = emotion_2

        # ======================
        # MOUTH
        # ======================

        mouths_dir = f"characters/lion/mouths/{current_emotion}"

        current_viseme = "CLOSED"
        for segment in timeline:
            if segment["start"] <= current_time < segment["end"]:
                current_viseme = segment["viseme"]
                break

        mouth_cache_key = f"{current_emotion}_{current_viseme}"
        if mouth_cache_key not in mouth_cache:
            mouth_cache[mouth_cache_key] = load_mouth_image(current_viseme, mouths_dir)

        mouth_img = mouth_cache[mouth_cache_key]

        mouth_cfg = position["mouth"]

        mouth_transformed = mouth_img.copy()
        mouth_transformed = mouth_transformed.resize(
            (
                int(mouth_transformed.width * mouth_cfg.get("scale", 1)),
                int(mouth_transformed.height * mouth_cfg.get("scale", 1))
            ),
            Image.LANCZOS
        )
        mouth_transformed = mouth_transformed.rotate(
            mouth_cfg.get("rotation", 0),
            expand=True
        )

        # ======================
        # EYES
        # ======================

        eyes_dir = f"characters/lion/eyes/{current_emotion}"

        current_eye_state = "OPEN"
        for segment in eye_timeline:
            if segment["start"] <= current_time < segment["end"]:
                current_eye_state = segment["eye"]
                break

        eye_cache_key = f"{current_emotion}_{current_eye_state}"
        if eye_cache_key not in eye_cache:
            eye_cache[eye_cache_key] = load_eye_image(current_eye_state, eyes_dir)

        eye_img = eye_cache[eye_cache_key]

        eyes_cfg = position["eyes"]

        eye_transformed = eye_img.copy()
        eye_transformed = eye_transformed.resize(
            (
                int(eye_transformed.width * eyes_cfg.get("scale", 1)),
                int(eye_transformed.height * eyes_cfg.get("scale", 1))
            ),
            Image.LANCZOS
        )
        eye_transformed = eye_transformed.rotate(
            eyes_cfg.get("rotation", 0),
            expand=True
        )

        # ======================
        # COMPOSITING
        # ======================

        frame = base_image.copy()

        # Eyes first
        frame.paste(
            eye_transformed,
            (int(eyes_cfg["x"]), int(eyes_cfg["y"])),
            eye_transformed
        )

        # Mouth after
        frame.paste(
            mouth_transformed,
            (int(mouth_cfg["x"]), int(mouth_cfg["y"])),
            mouth_transformed
        )

        frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_number:05d}.png")
        frame.save(frame_path)

        if frame_number % 50 == 0:
            print(f"Rendered frame {frame_number}/{total_frames}")

    # ======================
    # FFMPEG
    # ======================

    print("Encoding video with ffmpeg...")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(FPS),
        "-i", f"{FRAMES_DIR}/frame_%05d.png",
        "-i", AUDIO_PATH,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        OUTPUT_VIDEO
    ]

    subprocess.run(ffmpeg_cmd, check=True)

    print(f"Video generated: {OUTPUT_VIDEO}")

    print("Cleaning temporary frames...")
    shutil.rmtree(FRAMES_DIR)

    print("Done.")


# ======================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    args = parser.parse_args()

    render(args.episode)

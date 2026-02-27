import os
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from PIL import Image
from PIL import ImageDraw

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


def load_mouth_image(viseme, mouths_dir):
    filename = f"{viseme}.png"
    path = os.path.join(mouths_dir, filename)

    if not os.path.exists(path):
        raise ValueError(f"Viseme image not found: {path}")

    return Image.open(path).convert("RGBA")


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

    print(f"Total duration: {total_duration:.2f}s")
    print(f"Total frames: {total_frames}")

    ensure_dir(FRAMES_DIR)
    ensure_dir(OUTPUT_DIR)

    emotion_1 = position.get("emotion_1", "HAPPY")
    emotion_2 = position.get("emotion_2", emotion_1)
    transition_time = position.get("emotion_transition_time", float("inf"))

    mouth_cache = {}

    for frame_number in range(total_frames):

        current_time = frame_number / FPS

        # Emotion selection
        if current_time < transition_time:
            current_emotion = emotion_1
        else:
            current_emotion = emotion_2

        mouths_dir = f"characters/lion/mouths/{current_emotion}"

        # Find active viseme
        current_viseme = "CLOSED"

        for segment in timeline:
            if segment["start"] <= current_time < segment["end"]:
                current_viseme = segment["viseme"]
                break

        cache_key = f"{current_emotion}_{current_viseme}"

        if cache_key not in mouth_cache:
            mouth_cache[cache_key] = load_mouth_image(current_viseme, mouths_dir)

        mouth_img = mouth_cache[cache_key]

        transformed = mouth_img.copy()

        # Scale
        scale = position.get("scale", 1.0)
        new_size = (
            int(transformed.width * scale),
            int(transformed.height * scale)
        )
        transformed = transformed.resize(new_size, Image.LANCZOS)

        # Rotation
        rotation = position.get("rotation", 0)
        transformed = transformed.rotate(rotation, expand=True)

        # Composite
        frame = base_image.copy()

        x = int(position["x"])
        y = int(position["y"])

        frame.paste(transformed, (x, y), transformed)

        frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_number:05d}.png")
        frame.save(frame_path)

        if frame_number % 50 == 0:
            print(f"Rendered frame {frame_number}/{total_frames}")

    print("Frames generated.")

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

    # ======================
    # CLEANUP
    # ======================

    print("Cleaning temporary frames...")
    shutil.rmtree(FRAMES_DIR)

    print("Done.")


# ======================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    args = parser.parse_args()

    render(args.episode)

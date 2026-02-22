#!/usr/bin/env python3

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List


# --------------------------------------------------
# DATA STRUCTURES
# --------------------------------------------------

@dataclass
class SubtitleBlock:
    start: float
    end: float
    text: str


@dataclass
class VisemeEvent:
    start: float
    end: float
    viseme: str


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

VISEME_RULES = [
    (r"ou", "OU"),
    (r"eau", "O"),
    (r"au", "O"),
    (r"[oô]", "O"),
    (r"(ai|ei|é|è|ê|eu|œ)", "E"),
    (r"[iyîï]", "I"),
    (r"[aàâ]", "A"),
    (r"[mbp]", "M"),
    (r"[fv]", "F"),
]

DEFAULT_VISEME = "NEUTRAL"
MIN_DURATION = 0.05  # sécurité anti micro-visèmes


# --------------------------------------------------
# SRT PARSER
# --------------------------------------------------

def srt_time_to_seconds(time_str: str) -> float:
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.split(",")
    return (
        int(h) * 3600 +
        int(m) * 60 +
        int(s) +
        int(ms) / 1000
    )


def parse_srt(path: str) -> List[SubtitleBlock]:
    content = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())

    subtitles = []

    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 3:
            times = lines[1]
            text = " ".join(lines[2:])

            start_str, end_str = times.split(" --> ")
            start = srt_time_to_seconds(start_str.strip())
            end = srt_time_to_seconds(end_str.strip())

            subtitles.append(SubtitleBlock(start, end, text))

    return subtitles


# --------------------------------------------------
# TEXT → VISEMES
# --------------------------------------------------

def text_to_visemes(text: str) -> List[str]:
    text = text.lower()
    visemes = []
    i = 0

    while i < len(text):
        matched = False

        for pattern, viseme in VISEME_RULES:
            regex = re.compile(pattern)
            match = regex.match(text, i)
            if match:
                visemes.append(viseme)
                i += len(match.group())
                matched = True
                break

        if not matched:
            if text[i].isalpha():
                visemes.append(DEFAULT_VISEME)
            i += 1

    return visemes


# --------------------------------------------------
# TIMELINE GENERATION
# --------------------------------------------------

def generate_timeline(subtitles: List[SubtitleBlock]) -> List[VisemeEvent]:
    timeline = []

    for sub in subtitles:
        visemes = text_to_visemes(sub.text)

        if not visemes:
            continue

        duration = sub.end - sub.start
        time_per_viseme = max(duration / len(visemes), MIN_DURATION)

        current_time = sub.start

        for viseme in visemes:
            start = current_time
            end = min(start + time_per_viseme, sub.end)

            timeline.append(VisemeEvent(start, end, viseme))
            current_time = end

    return merge_consecutive_visemes(timeline)


def merge_consecutive_visemes(events: List[VisemeEvent]) -> List[VisemeEvent]:
    if not events:
        return []

    merged = [events[0]]

    for event in events[1:]:
        last = merged[-1]

        if event.viseme == last.viseme:
            last.end = event.end
        else:
            merged.append(event)

    return merged


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert SRT to viseme timeline JSON")
    parser.add_argument("input_srt", help="Input SRT file")
    parser.add_argument("output_json", help="Output JSON file")

    args = parser.parse_args()

    subtitles = parse_srt(args.input_srt)
    timeline = generate_timeline(subtitles)

    output = [
        {
            "start": round(event.start, 3),
            "end": round(event.end, 3),
            "viseme": event.viseme
        }
        for event in timeline
    ]

    Path(args.output_json).write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Generated {len(output)} viseme events.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

# --------------------------------------------------
# DATA STRUCTURES
# --------------------------------------------------

@dataclass
class VisemeEvent:
    start: float
    end: float
    viseme: str


# --------------------------------------------------
# LOAD VISEME RULES FROM JSON
# --------------------------------------------------

def load_viseme_rules(path: str) -> Tuple[List[Tuple[re.Pattern, str]], str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    compiled_rules = [
        (re.compile(rule["pattern"]), rule["viseme"])
        for rule in data["rules"]
    ]

    default_viseme = data.get("default", "NEUTRAL")

    return compiled_rules, default_viseme


# --------------------------------------------------
# ASS TIME CONVERSION
# --------------------------------------------------

def ass_time_to_seconds(t: str) -> float:
    """
    Convertit un timestamp ASS (h:mm:ss.cc) en secondes
    """
    h, m, s = t.split(":")
    s, cs = s.split(".")
    return (
        int(h) * 3600
        + int(m) * 60
        + int(s)
        + int(cs) / 100
    )


# --------------------------------------------------
# ASS PARSER (karaoke {\k})
# --------------------------------------------------

def parse_ass_karaoke(file_path: str):
    timeline = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    dialogue_lines = [l for l in lines if l.startswith("Dialogue:")]

    for line in dialogue_lines:
        parts = line.split(",", 9)

        start_time = ass_time_to_seconds(parts[1])
        text = parts[9]

        # extrait {\\kXX}texte
        pattern = re.findall(r"{\\k(\d+)}([^{}]+)", text)

        current_time = start_time

        for duration_cs, syllable in pattern:
            duration = int(duration_cs) / 100.0

            timeline.append({
                "start": current_time,
                "end": current_time + duration,
                "text": syllable.strip()
            })

            current_time += duration

    return timeline


# --------------------------------------------------
# TEXT → VISEME
# --------------------------------------------------

def text_to_visemes(text: str, rules, default_viseme: str) -> List[str]:
    """
    Applique les règles regex pour trouver le viseme correspondant.
    Retourne une liste (même si généralement 1 seul viseme).
    """
    text = text.lower()

    matched_visemes = []

    for pattern, viseme in rules:
        if pattern.search(text):
            matched_visemes.append(viseme)

    if not matched_visemes:
        return [default_viseme]

    return matched_visemes


# --------------------------------------------------
# MERGE CONSECUTIVE IDENTICAL VISEMES
# --------------------------------------------------

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
    parser = argparse.ArgumentParser(description="Convert ASS karaoke to viseme timeline JSON")
    parser.add_argument("input_ass", help="Input ASS file")
    parser.add_argument("output_json", help="Output JSON file")
    parser.add_argument("viseme_config", help="Viseme JSON config file")

    args = parser.parse_args()

    rules, default_viseme = load_viseme_rules(args.viseme_config)

    raw_segments = parse_ass_karaoke(args.input_ass)

    timeline = []

    for segment in raw_segments:
        visemes = text_to_visemes(segment["text"], rules, default_viseme)

        # on prend le premier viseme correspondant
        viseme_name = visemes[0] if visemes else default_viseme

        timeline.append(
            VisemeEvent(
                start=segment["start"],
                end=segment["end"],
                viseme=viseme_name
            )
        )

    timeline = merge_consecutive_visemes(timeline)

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

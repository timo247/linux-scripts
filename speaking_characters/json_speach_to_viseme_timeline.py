#!/usr/bin/env python3

import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
import re

# --------------------------------------------------
# CONFIG ANIMATION
# --------------------------------------------------

VISEME_OFFSET = -0.04       # anticipation visuelle
MICRO_PAUSE = 0.03          # fermeture fin de mot
MIN_DURATION = 0.05         # sécurité mot court
SILENCE_THRESHOLD = 0.12    # gap réel = silence bouche fermée
A_BRIDGE_THRESHOLD = 0.18   # distance max entre deux A pour interpolation

# --------------------------------------------------
# DATA STRUCTURE
# --------------------------------------------------

@dataclass
class VisemeEvent:
    start: float
    end: float
    viseme: str

# --------------------------------------------------
# LOAD VISEME RULES
# --------------------------------------------------

def load_viseme_rules(path: str) -> Tuple[List[Tuple[re.Pattern, str]], str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    compiled_rules = [
        (re.compile(rule["pattern"], re.IGNORECASE), rule["viseme"])
        for rule in data["rules"]
    ]
    default_viseme = data.get("default", "CLOSED")
    return compiled_rules, default_viseme

# --------------------------------------------------
# NORMALISATION TEXTE
# --------------------------------------------------

def normalize_word(word: str) -> str:
    word = word.lower()
    word = re.sub(r"[^\wàâäéèêëîïôöùûüÿœ'-]", "", word)
    return word

# --------------------------------------------------
# VISEME PAR MOT
# --------------------------------------------------

def text_to_viseme(text: str, rules, default_viseme: str) -> str:
    text = normalize_word(text)

    # Correction spécifique : "oi" = A en français
    if re.search(r"oi", text):
        return "A"

    for pattern, viseme in rules:
        if pattern.search(text):
            return viseme

    return default_viseme

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
# JSON PARSER
# --------------------------------------------------

def parse_json_segments(file_path: str):
    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    timeline = []

    for segment in data.get("segments", []):
        for word in segment.get("words", []):
            start = float(word["start"])
            end = float(word["end"])
            text = word["word"].strip()

            if end - start < MIN_DURATION:
                continue

            timeline.append({
                "start": start,
                "end": end,
                "text": text
            })

    return timeline

# --------------------------------------------------
# INTERPOLATION A → CONS → A
# --------------------------------------------------

def smooth_a_sequences(events: List[VisemeEvent]) -> List[VisemeEvent]:
    for i in range(1, len(events) - 1):
        prev_e = events[i - 1]
        curr_e = events[i]
        next_e = events[i + 1]

        if (
            prev_e.viseme == "A"
            and next_e.viseme == "A"
            and curr_e.viseme == "CONS"
        ):
            gap = next_e.start - prev_e.end
            if gap < A_BRIDGE_THRESHOLD:
                curr_e.viseme = "A"

    return events

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert JSON speech segments to viseme timeline JSON")
    parser.add_argument("input_json")
    parser.add_argument("output_json")
    parser.add_argument("viseme_config")

    args = parser.parse_args()

    rules, default_viseme = load_viseme_rules(args.viseme_config)
    raw_segments = parse_json_segments(args.input_json)

    timeline: List[VisemeEvent] = []
    previous_end = None

    # --------------------------------------------------
    # Force bouche CLOSED dès 00.000
    # --------------------------------------------------
    if raw_segments:
        first_word_start = max(0.0, raw_segments[0]["start"] + VISEME_OFFSET)

        if first_word_start > 0:
            timeline.append(
                VisemeEvent(
                    0.0,
                    first_word_start,
                    "CLOSED"
                )
            )
            previous_end = first_word_start
        else:
            previous_end = 0.0

    # --------------------------------------------------
    # Génération timeline principale
    # --------------------------------------------------
    for segment in raw_segments:
        base_start = segment["start"]
        base_end = segment["end"]

        start = max(0.0, base_start + VISEME_OFFSET)
        end = base_end

        # Gestion silence réel entre mots
        if previous_end is not None:
            gap = start - previous_end
            if gap > SILENCE_THRESHOLD:
                timeline.append(
                    VisemeEvent(
                        previous_end,
                        start,
                        "CLOSED"
                    )
                )

        viseme = text_to_viseme(segment["text"], rules, default_viseme)

        total_duration = end - start
        if total_duration <= 0:
            continue

        close_duration = min(MICRO_PAUSE, total_duration * 0.4)
        main_end = end - close_duration

        timeline.append(VisemeEvent(start, main_end, viseme))
        timeline.append(VisemeEvent(main_end, end, "CLOSED"))

        previous_end = end

    # --------------------------------------------------
    # Lissage A → CONS → A
    # --------------------------------------------------
    timeline = smooth_a_sequences(timeline)

    # --------------------------------------------------
    # Merge final
    # --------------------------------------------------
    timeline = merge_consecutive_visemes(timeline)

    # --------------------------------------------------
    # Sécurité finale : garantir start = 0.000
    # --------------------------------------------------
    if timeline and timeline[0].start > 0:
        timeline.insert(0, VisemeEvent(0.0, timeline[0].start, "CLOSED"))

    # --------------------------------------------------
    # Export JSON
    # --------------------------------------------------
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

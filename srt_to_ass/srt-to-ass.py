#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pysrt
import sys

def ass_time(srt_time):
    total_ms = srt_time.ordinal
    cs = round(total_ms / 10)

    h  = cs // 360000
    m  = (cs % 360000) // 6000
    s  = (cs % 6000) // 100
    c  = cs % 100

    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def srt_to_ass(srt_path, ass_path):
    subs = pysrt.open(srt_path, encoding='utf-8')

    with open(ass_path, 'w', encoding='utf-8') as out:

        # Header ASS externe
        with open('ass_header.ini', 'r', encoding='utf-8') as H:
            out.write(H.read())

        out.write("\n[Events]\n")
        out.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        for sub in subs:
            start = ass_time(sub.start)
            end   = ass_time(sub.end)

            # Texte
            raw_text = sub.text.replace("\n", " ")
            words = raw_text.split()

            if not words:
                continue

            # durée du sous-titre en ms
            duration_ms = sub.duration.ordinal

            # durée par mot pour effet karaoké
            per_word_k = max(1, duration_ms // len(words) // 10)  # en centièmes (ASS \k)

            # Construction du texte karaoké
            # \kX → surbrillance pendant X centièmes de seconde
            kara_text = ""
            for w in words:
                kara_text += r"{\k" + str(per_word_k) + "}" + w + " "

            kara_text = kara_text.strip()

            out.write(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{kara_text}\n"
            )

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: script.py fichier.srt fichier.ass")
        sys.exit(1)

    episode_srt_path = sys.argv[1]
    episode_ass_path = sys.argv[2]

    srt_to_ass(episode_srt_path, episode_ass_path)
    print(f"✔ Conversion terminée → {episode_ass_path}")


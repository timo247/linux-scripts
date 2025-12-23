import pysrt
import re

episode_path =  '/home/timo/Documents/la-voie-de-la-savane/saison-1/episode-1.srt'
output_path = '/home/timo/Documents/la-voie-de-la-savane/saison-1/episode-1_clean.srt'

subs = pysrt.open(episode_path, encoding='utf-8')
for sub in subs:
    # Capitalise la première lettre
    sub.text = sub.text.strip()
    sub.text = sub.text[0].upper() + sub.text[1:]
    # Normalise les espaces
    sub.text = re.sub(r'\s+', ' ', sub.text)
subs.save(output_path, encoding='utf-8')

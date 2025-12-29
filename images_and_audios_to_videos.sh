#!/bin/bash

images_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/visuels/youtube"
audios_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/audio-episodes"
output_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/videos"

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  echo "Usage: images_and_audios_to_videos.sh FIRST_EPISODE LAST_EPISODE"
  exit 0
fi


first_episode=$1
last_episode=$2

for (( i=$1; i<=$2; i++ ));
do
ffmpeg -loop 1 -i "$images_folder/ep$i.png" -i "$audios_folder/ep-$i.mp3" \
       -c:v libx264 -tune stillimage -pix_fmt yuv420p -shortest \
       -c:a aac -b:a 128k "$output_folder/ep-$i.mp4"
done

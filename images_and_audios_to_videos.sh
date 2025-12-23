#!/bin/bash

images_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/visuels/youtube"
audios_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/audio-episodes"
output_folder="/home/timo/Documents/la-voie-de-la-savane/saison-1/videos"

if [ $1 == "--help" or $1 =="-h" ]; then
  echo "This script will genereate mp4 videos using the images located into the folder $images_folder and the audios located into the folder $audios_folder. It will increment from the first number you pass as argument to the second number ou pass as argument. Usage example: audios_and_images_to_videos.sh 1 10 --> generates 10 videos for episodes 1 to 10"
exit
fi

first_episode=$1
last_episode=$2

for (( i=$1; i<=$2; i++ ));
do
ffmpeg -loop 1 -i "$images_folder/ep$i.png" -i "$audios_folder/ep-$i.mp3" \
       -c:v libx264 -tune stillimage -pix_fmt yuv420p -shortest \
       -c:a aac -b:a 128k "$output_folder/ep-$i.mp4"
done

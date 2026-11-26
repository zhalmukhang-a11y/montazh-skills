#!/usr/bin/env bash
# Скачать бесплатное видео Mixkit в максимальном качестве (4K → 1080 → 720). usage: scripts/mixkit.sh <id> <имя>  → broll/<имя>.mp4
id=$1; n=$2; mkdir -p broll
for r in 2160p 1080p 720p; do
  u=$(curl -sL -A "Mozilla/5.0" "https://mixkit.co/free-stock-video/download/$id/?context=sidebar&type=$r" | grep -oE 'modal-url-value="[^"]+"' | cut -d'"' -f2)
  [ -n "$u" ] && curl -sL -o broll/$n.mp4 "$u" && ffprobe -v error broll/$n.mp4 >/dev/null 2>&1 && break
done
echo "$n: $(ffprobe -v error -show_entries stream=width,height:format=duration -of csv=p=0 broll/$n.mp4 | tr '\n' ' ')"

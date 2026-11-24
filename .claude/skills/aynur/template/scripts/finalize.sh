#!/usr/bin/env bash
# Финальный экспорт под Instagram Reels: титры поверх, звук с музыкой, точная громкость −14 LUFS (два прохода).
# usage: scripts/finalize.sh work/bg.mp4 work/bg_music.mov out/итог.mp4
set -e; BG=$1; AUD=$2; OUT=$3
BG=$BG STYLE=ref_style.html OUT=work/pre.mp4 node render_subs.mjs
J=$(ffmpeg -i "$AUD" -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
g(){ echo "$J" | grep "\"$1\"" | grep -oE '[-0-9.]+' | head -1; }
ffmpeg -v error -y -i work/pre.mp4 -i "$AUD" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" \
  -c:a aac -b:a 320k -ar 48000 -ac 2 -movflags +faststart "$OUT"
ffmpeg -i "$OUT" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:'
ffprobe -v error -show_entries stream=codec_name,profile,width,height,r_frame_rate,bit_rate -of csv=p=0 "$OUT"

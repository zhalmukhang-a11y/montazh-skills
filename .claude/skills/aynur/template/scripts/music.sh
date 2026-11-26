#!/usr/bin/env bash
# Музыка из референса под голос. usage: scripts/music.sh ref/ref.mp4 work/bg.mp4 work/bg_music.mov
# Demucs отделяет музыку от голоса; музыка ставится на ту же разницу с голосом, что в референсе, в конце затухание 1,5 с.
set -e; REF=$1; BG=$2; OUT=$3; PY=.venv/bin/python
mkdir -p ref/sep; ffmpeg -v error -y -i "$REF" -ac 2 -ar 44100 ref/ref44.wav
(cd ref && ../$PY -I -m demucs --two-stems=vocals -n htdemucs -o sep ref44.wav >/dev/null 2>&1)
M=ref/sep/htdemucs/ref44/no_vocals.wav; V=ref/sep/htdemucs/ref44/vocals.wav
lufs(){ ffmpeg -i "$1" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | grep -oE '[-0-9.]+' | head -1; }
LV=$(lufs $V); LM=$(lufs $M); LO=$(lufs "$BG")
GAIN=$(python3 -c "print(round(($LO-($LV-$LM))-($LM),2))"); D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$BG")
echo "референс: голос $LV, музыка $LM; наш голос $LO → музыка ${GAIN} дБ"
ffmpeg -v error -y -i "$BG" -i $M -filter_complex "[1:a]atrim=0:$D,asetpts=PTS-STARTPTS,aresample=48000,volume=${GAIN}dB,afade=t=in:d=0.3,afade=t=out:st=$(python3 -c "print($D-1.5)"):d=1.5[m];[0:a]aresample=48000,aformat=channel_layouts=stereo[v];[v][m]amix=inputs=2:duration=first:normalize=0[a]" -map 0:v -map "[a]" -c:v copy -c:a pcm_s16le "$OUT"

# Звуки: «вжух» на каждую вставку и смену заголовка, тихий «поп» на рукописную строку. Тише голоса эксперта.
# usage: python3 scripts/sfx.py work/bg_v.mov work/bg.mov
import json, subprocess, sys, os
src, out = sys.argv[1], sys.argv[2]
if not os.path.exists('work/whoosh.wav'):
    subprocess.run("ffmpeg -v error -y -f lavfi -i anoisesrc=c=pink:d=0.6:a=0.8 -af bandpass=f=1200:w=900,afade=t=in:d=0.35:curve=exp,afade=t=out:st=0.35:d=0.25,volume=0.6 -ar 48000 -ac 2 work/whoosh.wav", shell=True, check=True)
    subprocess.run("ffmpeg -v error -y -f lavfi -i sine=f=740:d=0.12 -af afade=t=out:d=0.12:curve=exp,volume=0.5 -ar 48000 -ac 2 work/pop.wav", shell=True, check=True)
T = json.load(open('work/titles.json')); I = json.load(open('work/inserts.json')) if os.path.exists('work/inserts.json') else []
ev = [('whoosh', max(0, x['a'] - 0.3)) for x in I] + [('whoosh', max(0, t['start'] - 0.25)) for t in T if all(abs(t['start'] - x['a']) > 0.6 for x in I)] + [('pop', t['script'][1]) for t in T if t.get('script')]
inp = ['-i', src]; f = []; lab = ''
for k, (n, s) in enumerate(ev):
    inp += ['-i', f'work/{n}.wav']; ms = int(s * 1000)
    f.append(f'[{k+1}:a]adelay={ms}|{ms},volume={0.25 if n == "whoosh" else 0.2}[s{k}]'); lab += f'[s{k}]'
f.append(f'[0:a]{lab}amix=inputs={len(ev)+1}:normalize=0:duration=first[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', ';'.join(f), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'pcm_s16le', out], check=True)
print(len(ev), 'звуков →', out)

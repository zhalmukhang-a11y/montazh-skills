# Накладывает вставки (b-roll) поверх нарезки. usage: python3 scripts/inserts.py work/cut_beauty.mp4 work/inserts.json work/bg.mp4
# inserts.json: [{"f": "phone", "a": 3.44, "b": 5.86, "off": 4.0, "x": 0.42}]  f — broll/<f>.mp4, a..b — время в ролике, off — откуда брать в исходнике вставки, x — где кадрировать по горизонтали (0..1)
import json, subprocess, sys
src, cfg, out = sys.argv[1], sys.argv[2], sys.argv[3]
I = json.load(open(cfg))
inp = ['-i', src]; f = []; prev = '0:v'
for k, c in enumerate(I):
    d = c['b'] - c['a']
    inp += ['-ss', str(c['off']), '-t', f'{d + 0.1:.2f}', '-i', f"broll/{c['f']}.mp4"]
    if c.get('card'):  # горизонтальное 720p/1080p: чёткая картинка по ширине поверх размытого фона (не мылим)
        f.append(f"[{k+1}:v]fps=30,split[cb{k}][cf{k}];[cb{k}]scale=-2:1920,crop=1080:1920,boxblur=30:2,eq=brightness=-0.08[cb2{k}];[cf{k}]scale=1080:-2:flags=lanczos[cf2{k}];[cb2{k}][cf2{k}]overlay=0:(H-h)/2,setsar=1,setpts=PTS-STARTPTS+{c['a']}/TB[i{k}]")
    else:
        f.append(f"[{k+1}:v]fps=30,scale=-2:1920:flags=lanczos,crop=1080:1920:'(iw-1080)*{c['x']}':0,setsar=1,setpts=PTS-STARTPTS+{c['a']}/TB[i{k}]")
    f.append(f"[{prev}][i{k}]overlay=enable='between(t,{c['a']},{c['b'] - 0.001:.3f})':eof_action=pass[o{k}]")
    prev = f'o{k}'
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inp + (['-filter_complex', ';'.join(f), '-map', f'[{prev}]'] if I else ['-map', '0:v']) +
               ['-map', '0:a', '-c:v', 'libx264', '-crf', '10', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', out], check=True)
print('Готово:', out)

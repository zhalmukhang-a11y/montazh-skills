# Нарезка по номерам слов (из текста пользователя): слова берутся ЦЕЛИКОМ (без подрезки), паузы > --gap вырезаются,
# планы чередуются: обычный / приближение --zoom (зум на каждой склейке). Качество — как исходник.
# usage: python3 scripts/cut_text.py media/src.mp4 work/words.json --keep 391-396 --keep 397-412 [--zoom 1.13 --pad 0.12 --y 0.38]
# итог: work/cut.mov (crf 12, звук pcm), work/cutwords.json (новое время каждого слова: i, s, e)
import argparse, json, subprocess
p = argparse.ArgumentParser(); p.add_argument("src"); p.add_argument("words")
p.add_argument("--keep", action="append", required=True); p.add_argument("--zoom", type=float, default=1.13)
p.add_argument("--pad", type=float, default=0.16); p.add_argument("--gap", type=float, default=0.4); p.add_argument("--y", type=float, default=0.38)
p.add_argument("--remove", help="json [{s,e}] — вырезать эти интервалы исходника (ээ/ммм внутри слов, из fillers.py)")
a = p.parse_args()
W = {w['i']: w for w in json.load(open(a.words))['words']}
keep = []
for k in a.keep:
    lo, hi = (int(x) for x in k.split('-')) if '-' in k else (int(k), int(k)); keep += list(range(lo, hi + 1))
segs = []
for i in keep:
    w = W[i]
    if segs and i == segs[-1]['last'] + 1 and w['s'] - segs[-1]['le'] <= a.gap:
        s = segs[-1]; s['b'] = w['e'] + a.pad; s['le'] = w['e']; s['last'] = i; s['w'].append(w)
    else:
        segs.append({'a': w['s'] - a.pad, 'b': w['e'] + a.pad, 'le': w['e'], 'last': i, 'w': [w]})
RM = sorted((r['s'], r['e']) for r in json.load(open(a.remove))) if a.remove else []
for r0, r1 in RM:  # режем куски по интервалам «ээ»
    nseg = []
    for s in segs:
        if r1 <= s['a'] or r0 >= s['b']: nseg.append(s); continue
        if r0 - s['a'] > 0.05: nseg.append(dict(s, b=r0))
        if s['b'] - r1 > 0.05: nseg.append(dict(s, a=r1))
    segs = nseg
for p_, n in zip(segs, segs[1:]):
    if p_['b'] > n['a']: m = (p_['le'] + n['w'][0]['s']) / 2; p_['b'] = m; n['a'] = m
inp, f, cat, t, new, seen = [], [], "", 0, [], set()
for k, s in enumerate(segs):
    d = s['b'] - s['a']; z = a.zoom if k % 2 else 1.0
    inp += ["-ss", f"{s['a']:.3f}", "-t", f"{d:.3f}", "-i", a.src]
    vz = f"scale={round(1080*z/2)*2}:{round(1920*z/2)*2}:flags=lanczos,crop=1080:1920:(iw-1080)/2:(ih-1920)*{a.y}" if z > 1 else "scale=1080:1920:flags=lanczos"
    f.append(f"[{k}:v]setpts=PTS-STARTPTS,fps=30,{vz},setsar=1[v{k}]")
    f.append(f"[{k}:a]asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d-0.012:.3f}:d=0.012[a{k}]")
    cat += f"[v{k}][a{k}]"
    s['t'] = t; t += d
def M(x):  # время исходника → время ролика
    for s in segs:
        if x <= s['b']: return round(s['t'] + max(0, x - s['a']), 2)
    return round(t, 2)
for i in keep:
    if i not in seen: seen.add(i); new.append({'i': i, 'w': W[i]['w'], 's': M(W[i]['s']), 'e': M(W[i]['e'])})
f.append(f"{cat}concat=n={len(segs)}:v=1:a=1[v][a]")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + inp + ["-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "work/cut.mov"], check=True)
json.dump({'dur': round(t, 2), 'words': new}, open('work/cutwords.json', 'w'), ensure_ascii=False)
print(f"work/cut.mov: {t:.1f} с, кусков {len(segs)}")

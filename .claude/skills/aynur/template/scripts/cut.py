# usage: python3 scripts/cut.py исходник.mp4 work/words.json --keep "26-44" [--keep "50-61"] [--x 0.5] [--gap 0.25]
# Оставляет только выбранные слова (номера из words.json), сжимает паузы, делает вертикаль 1080×1920.
# Результат: work/cut.mp4 (без субтитров), work/subs.json (субтитры для правки), work/cut.srt
import argparse, json, subprocess, os

p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("words")
p.add_argument("--keep", action="append", required=True, help="диапазон номеров слов, например 26-44")
p.add_argument("--x", type=float, default=0.5, help="где человек по горизонтали: 0 — слева, 0.5 — центр, 1 — справа")
p.add_argument("--gap", type=float, default=0.25, help="паузы длиннее (сек) сжимаются")
p.add_argument("--pad", type=float, default=0.08, help="запас до/после слова (сек)")
p.add_argument("--out", default="work")
p.add_argument("--zoom", default="1", help="крупность по кускам по очереди, например 1.28,1.42")
p.add_argument("--headroom", default="", help="отступ над головой в px для каждой крупности, например 690,600")
p.add_argument("--splits", default="", help="номера слов, с которых начинается новый план (смена крупности)")
p.add_argument("--grade", default="", help="ffmpeg-фильтр цвета")
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)

W = {w["i"]: w for w in json.load(open(a.words, encoding="utf-8"))["words"]}

# реальная тишина в звуке: если распознавание «растянуло» слово на паузу, обрезаем слово по тишине
import re
log = subprocess.run(["ffmpeg", "-i", a.src, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True).stderr
sil = list(zip([float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)], [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]))
for w in W.values():
    for s0, s1 in sil:
        if w["s"] < s0 < w["e"] and s1 > w["e"] - 0.05: w["e"] = round(s0, 2)       # тишина в конце слова
        if w["s"] < s1 < w["e"] and s0 < w["s"] + 0.05: w["s"] = round(s1, 2)       # тишина в начале слова
order = []
for k in a.keep:
    lo, hi = (int(x) for x in k.split("-")) if "-" in k else (int(k), int(k))
    order += [W[i] for i in range(lo, hi + 1) if i in W]

# куски исходника: новый кусок, если пауза между словами больше --gap или слова не подряд
segs = []
for w in order:
    if segs and w["i"] == segs[-1]["last"]["i"] + 1 and w["s"] - segs[-1]["last"]["e"] <= a.gap:
        segs[-1]["words"].append(w); segs[-1]["last"] = w
    else:
        segs.append({"words": [w], "last": w})
sp = {int(x) for x in a.splits.split(",") if x}
segs2 = []
for s in segs:
    cur = []
    for w in s["words"]:
        if cur and w["i"] in sp:
            segs2.append({"words": cur, "last": cur[-1], "cut_after": True}); cur = []
        cur.append(w)
    segs2.append({"words": cur, "last": cur[-1]})
segs = segs2
for k, s in enumerate(segs):
    if k and segs[k - 1].get("cut_after"):  # внутренний стык: делим ровно посередине между словами
        m = (segs[k - 1]["last"]["e"] + s["words"][0]["s"]) / 2
        segs[k - 1]["b"] = m; s["a"] = m; continue
for s in segs:
    if "a" not in s: s["a"] = max(0, s["words"][0]["s"] - a.pad)
    if "b" not in s: s["b"] = s["words"][-1]["e"] + a.pad

# размер кадра исходника -> кроп 9:16
w0, h0 = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                  "-of", "csv=p=0", a.src], capture_output=True, text=True).stdout.strip().split(",")[:2])
rot = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream_side_data=rotation",
                      "-of", "csv=p=0", a.src], capture_output=True, text=True).stdout.strip()
if rot and abs(int(float(rot.splitlines()[0]))) % 180 == 90:  # снято вертикально, в файле кадр «лёжа»
    w0, h0 = h0, w0
if w0 / h0 > 9 / 16:
    cw, ch = round(h0 * 9 / 16 / 2) * 2, h0
else:
    cw, ch = w0, round(w0 * 16 / 9 / 2) * 2
cx = round(max(0, min(w0 - cw, a.x * w0 - cw / 2)))
crop = f"crop={cw}:{ch}:{cx}:{(h0 - ch) // 2},scale=1080:1920,setsar=1"

f, cat, F = [], "", 0.012
for k, s in enumerate(segs):
    d = s["b"] - s["a"]
    zs = [float(z) for z in a.zoom.split(",")]; z = zs[k % len(zs)]
    zc = crop
    if z != 1:
        hr = [float(x) for x in a.headroom.split(",")] if a.headroom else []
        W2, H2 = round(1080 * z / 2) * 2, round(1920 * z / 2) * 2
        yo = int(min(H2 - 1920, max(0, 615 * z - hr[k % len(hr)]))) if hr else (H2 - 1920) // 2
        zc += f",scale={W2}:{H2},crop=1080:1920:{(W2 - 1080) // 2}:{yo}"
    if a.grade: zc += "," + a.grade
    zc += ",setsar=1"
    f.append(f"[0:v]trim={s['a']:.3f}:{s['b']:.3f},setpts=PTS-STARTPTS,{zc}[v{k}]")
    f.append(f"[0:a]atrim={s['a']:.3f}:{s['b']:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={F},afade=t=out:st={d - F:.3f}:d={F}[a{k}]")
    cat += f"[v{k}][a{k}]"
f.append(f"{cat}concat=n={len(segs)}:v=1:a=1[v][a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
                "-r", "30", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                f"{a.out}/cut.mp4"], check=True)

# время слов в новом ролике + субтитры по 1–2 слова
t, new = 0.0, []
for s in segs:
    for w in s["words"]:
        new.append({"w": w["w"], "s": round(t + w["s"] - s["a"], 2), "e": round(t + w["e"] - s["a"], 2)})
    t += s["b"] - s["a"]
subs, cur = [], []
for k, w in enumerate(new):
    cur.append(w)
    nxt = new[k + 1] if k + 1 < len(new) else None
    long = sum(len(x["w"]) for x in cur) >= 12 or len(cur) == 2
    if not nxt or long or nxt["s"] - w["e"] > 0.3:
        subs.append({"words": [[x["w"], x["s"]] for x in cur], "end": round(min(w["e"] + 0.25, nxt["s"] if nxt else t), 2), "key": -1})
        cur = []
json.dump({"duration": round(t, 2), "subs": subs}, open(f"{a.out}/subs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def ts(x): return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}"
with open(f"{a.out}/cut.srt", "w", encoding="utf-8") as o:
    for n, s in enumerate(subs, 1):
        o.write(f"{n}\n{ts(s['words'][0][1])} --> {ts(s['end'])}\n{' '.join(x[0] for x in s['words'])}\n\n")
print(f"Готово: {a.out}/cut.mp4 ({t:.1f} с, кусков: {len(segs)}), {a.out}/subs.json, {a.out}/cut.srt")

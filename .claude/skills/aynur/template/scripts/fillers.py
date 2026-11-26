# Ищет «ээ/ааа/ммм» по звуку: голос звучит непрерывно ≥ --min с на почти ровной высоте (тянущийся звук без согласных).
# usage: python3 -I scripts/fillers.py media/src.mp4 work/words.json 943 1096 > work/fillers.json
# выводит интервалы (время исходника) + ближайшее слово. Дальше: cut_text.py ... --remove work/fillers.json
import sys, json, subprocess, numpy as np, argparse
p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('words'); p.add_argument('a', type=int); p.add_argument('b', type=int)
p.add_argument('--min', type=float, default=0.3); p.add_argument('--dev', type=float, default=0.06)
a = p.parse_args()
W = json.load(open(a.words))['words'][a.a:a.b + 1]
t0 = max(0, W[0]['s'] - 0.5); t1 = W[-1]['e'] + 0.5
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", a.src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                 capture_output=True, check=True).stdout, np.int16).astype(float)
H, N = 160, 640; n = (len(x) - N) // H; f0 = np.zeros(n)
for i in range(n):
    fr = x[i * H:i * H + N]; fr = fr - fr.mean()
    if np.sqrt((fr ** 2).mean()) < 250: continue
    ac = np.correlate(fr, fr, 'full')[N - 1:]; k = 40 + np.argmax(ac[40:228])
    if ac[k] > 0.6 * ac[0]: f0[i] = 16000 / k
out, i, M = [], 0, int(a.min * 100)
while i < n:
    if f0[i] > 0:
        j = i
        while j < n and f0[j] > 0: j += 1
        # внутри озвученного куска ищем самый длинный ровный по высоте отрезок
        s = i
        for q in range(i + 1, j + 1):
            if q == j or abs(f0[q] - np.median(f0[s:q])) > a.dev * np.median(f0[s:q]):
                if q - s >= M:
                    st, en = t0 + s * 0.01, t0 + q * 0.01
                    near = min(W, key=lambda w: 0 if w['s'] <= st <= w['e'] else min(abs(w['s'] - st), abs(w['e'] - st)))
                    out.append({"s": round(st + 0.03, 2), "e": round(en - 0.01, 2), "word": near['i'], "w": near['w']})
                s = q
        i = j
    else: i += 1
json.dump(out, sys.stdout, ensure_ascii=False, indent=0)

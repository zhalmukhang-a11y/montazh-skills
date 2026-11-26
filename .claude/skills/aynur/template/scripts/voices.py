# Кто говорит: высота голоса по каждому слову. Слова с <130 Гц помечены «М» (мужской голос — реплики интервьюера).
# usage: python3 -I scripts/voices.py media/src.mp4 work/words.json 391 501
import sys, json, subprocess, numpy as np
src, wj, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
W = json.load(open(wj))['words'][a:b + 1]
t0 = max(0, W[0]['s'] - 1); t1 = W[-1]['e'] + 1
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                 capture_output=True, check=True).stdout, np.int16).astype(float)
def f0(seg):
    out = []
    for i in range(0, len(seg) - 640, 320):
        fr = seg[i:i + 640] - seg[i:i + 640].mean()
        if np.sqrt((fr ** 2).mean()) < 300: continue
        ac = np.correlate(fr, fr, 'full')[639:]; k = 40 + np.argmax(ac[40:228])
        if ac[k] > 0.4 * ac[0]: out.append(16000 / k)
    return int(np.median(out)) if out else 0
for w in W:
    p = f0(x[int((w['s'] - t0) * 16000):int((w['e'] - t0) * 16000)])
    print(f"{w['i']}:{w['w']}({w['s']:.1f}) {p}{' М' if 0 < p < 130 else ''}")

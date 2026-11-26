# usage: .venv/bin/python scripts/transcribe.py исходник.mp4 > work/words.json
# Речь -> слова с началом и концом (сек). Режем по паузам, поэтому слова не рвутся на стыках.
import sys, json, re, subprocess, numpy as np, sherpa_onnx

src = sys.argv[1]
m = sys.argv[2] if len(sys.argv) > 2 else "models/sherpa-onnx-zipformer-ru-2024-09-18"
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=f"{m}/encoder.int8.onnx", decoder=f"{m}/decoder.onnx", joiner=f"{m}/joiner.int8.onnx",
    tokens=f"{m}/tokens.txt", num_threads=4, decoding_method="greedy_search")
SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
dur = len(audio) / SR

# паузы -> куски речи
log = subprocess.run(["ffmpeg", "-i", src, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
sil = list(zip(st, en + [dur] * (len(st) - len(en))))
segs, cur = [], 0.0
for a, b in sil:
    if a > cur + 0.05: segs.append((cur, a))
    cur = b
if cur < dur - 0.05: segs.append((cur, dur))

# длинные куски без пауз модель не берёт: режем на части ≤15 с в самом тихом месте
def quiet_split(a, b):
    if b - a <= 15: return [(a, b)]
    lo, hi = a + 8, a + 15
    x = audio[int(lo * SR):int(hi * SR)]
    win = int(0.05 * SR); e = [float(np.mean(x[i:i + win] ** 2)) for i in range(0, max(1, len(x) - win), win)]
    t = lo + (int(np.argmin(e)) * win + win / 2) / SR
    return [(a, t)] + quiet_split(t, b)
segs = [p for a, b in segs for p in quiet_split(a, b)]

words = []
for a, b in segs:
    a0, b0 = max(0, a - 0.1), min(dur, b + 0.1)
    s = rec.create_stream(); s.accept_waveform(SR, audio[int(a0 * SR):int(b0 * SR)]); rec.decode_stream(s)
    seg_words, new = [], True
    for tok, t in zip(s.result.tokens, s.result.timestamps):
        if tok.startswith(("▁", " ")): new = True
        tok = tok.lstrip("▁ ")
        if not tok: continue
        if new: seg_words.append([tok.lower(), max(a, a0 + t)]); new = False
        else: seg_words[-1][0] += tok.lower()
    for i, (w, t) in enumerate(seg_words):
        e = seg_words[i + 1][1] if i + 1 < len(seg_words) else b
        words.append({"i": len(words), "w": w, "s": round(t, 2), "e": round(min(e, b), 2)})

print(json.dumps({"duration": round(dur, 2), "words": words}, ensure_ascii=False, indent=0))

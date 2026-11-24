# usage: .venv/bin/python scripts/transcribe_whisper.py исходник.mp4 kk > work/words.json
# Для казахского и других языков (русский лучше через transcribe.py). Формат такой же: номер, слово, начало, конец.
# Модель whisper large-v3-turbo скачивается сама при первом запуске (~1.6 ГБ), дальше работает без интернета.
import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel

src, lang = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "kk")
model = sys.argv[3] if len(sys.argv) > 3 else "large-v3-turbo"
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
m = WhisperModel(model, device="cpu", compute_type="int8")
segs, _ = m.transcribe(x, language=lang, word_timestamps=True)
words = []
for s in segs:
    for w in s.words or []:
        t = w.word.strip()
        if t:
            words.append({"i": len(words), "w": t.lower().strip(".,!?«»…"), "s": round(w.start, 2), "e": round(w.end, 2)})
print(json.dumps({"duration": round(len(x) / 16000, 2), "words": words}, ensure_ascii=False, indent=0))

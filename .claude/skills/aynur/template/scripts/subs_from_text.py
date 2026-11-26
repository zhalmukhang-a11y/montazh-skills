# Субтитры по одному слову из ТЕКСТА ПОЛЬЗОВАТЕЛЯ: work/groups.json = [[первое_слово, последнее_слово, "текст как у пользователя"], ...]
# время каждого куска текста растягивается на время этих слов в нарезке. usage: python3 scripts/subs_from_text.py → work/subs.json
import json
C = json.load(open('work/cutwords.json')); N = {w['i']: w for w in C['words']}
items = []
for a, b, txt in json.load(open('work/groups.json')):
    s, e = N[a]['s'], N[b]['e']; parts = txt.lower().replace(',', '').replace('.', '').replace('—', '').split()
    L = sum(len(x) + 2 for x in parts); t = s
    for x in parts:
        d = (e - s) * (len(x) + 2) / L; items.append([x, t, t + d]); t += d
subs = [{"words": [[p, round(s, 2)]], "end": round(min(e + 0.3, items[k + 1][1] if k + 1 < len(items) else C['dur']), 2), "key": -1}
        for k, (p, s, e) in enumerate(items)]
json.dump({"duration": C['dur'], "subs": subs}, open('work/subs.json', 'w'), ensure_ascii=False)
print(len(subs), 'слов')

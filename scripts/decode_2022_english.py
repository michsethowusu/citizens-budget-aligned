"""Decode 2022 English Tahoma with a crib-seeded key + word refinement, rebuild doc."""
import json, re
from collections import Counter, defaultdict

spans = json.load(open('data/2022/eng_spans.json'))

# Crib: cover-page text "The 2022 Budget Statement and Economic Policy of the
# Government and the Citizens' Budget are available on the internet at:
# www.mofep.gov.gh  For copies of the Statement, please contact the Public
# Relations Office of the Ministry ... P. O. Box MB 40 ..."
key = {
    '=': 'T', '4': 'h', ')': 'e', '!': ' ', '5': '2', '6': '0', '7': 'B', '8': 'u',
    "'": 'd', '(': 'g', '3': 't', '+': 'S', '*': 'a', ',': 'm', '#': 'n', '9': 'E',
    ':': 'c', '2': 'o', '&': 'i', ';': 'P', '.': 'l', '<': 'y', '/': 'f', '>': 'G',
    '?': 'v', '%': 'r', '@': 'C', 'A': 'z', '1': 's', 'B': "'", 'C': ':', 'D': 'w',
    'E': '.', '-': 'p', 'G': ',', 'F': 'F', 'I': 'O', 'J': 'M', 'N': 'x', 'H': 'R',
}

text = ' '.join(t for (_, _, _, f, t) in spans if f == 'Tahoma')
vocab = {w.lower() for w in re.findall(r"[A-Za-z']+",
         open('data/2023/2023-Citizens-Budget_English.raw.txt').read()) if len(w) > 1}
vocab |= {'a', 'i', 'covid', 'gh', 'gdp', 'imf', 'mofep', 'agenda', 'ghanacares',
          'obaatanpa', 'astrazeneca', 'zipline', 'cedi', 'cedis'}
years = {str(y) for y in range(1980, 2031)}

syms = [c for c, n in Counter(text).most_common() if n >= 2]
space_syms = {'!', ' '}
key[' '] = ' '
tokens = Counter(t for t in re.split(r'[!\s]+', text) if t)
sym2toks = defaultdict(set)
for t in tokens:
    for s in set(t): sym2toks[s].add(t)

def tsc(t, k):
    d = ''.join(k.get(c, c) for c in t).strip('.,:;()%-"\'')
    if not d: return 0
    return len(d) * tokens[t] if (d.lower() in vocab or d in years
                                  or re.fullmatch(r'[\d.,/%]+', d)) else 0

pool = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;()%-/'\"$¢&")
for _ in range(6):
    improved = False
    for si in syms:
        if si in space_syms: continue
        old = key.get(si)
        before = sum(tsc(t, key) for t in sym2toks[si])
        bestc, bestg = None, 0
        for c in pool:
            if c == old: continue
            key[si] = c
            g = sum(tsc(t, key) for t in sym2toks[si]) - before
            if g > bestg: bestg, bestc = g, c
        key[si] = bestc if bestc else old
        if old is None and bestc is None: key.pop(si, None)
        if bestc: improved = True
    if not improved: break

nch = sum(len(t) * n for t, n in tokens.items())
fin = sum(tsc(t, key) for t in tokens)
print(f'word coverage: {fin}/{nch} = {fin/nch:.1%}')

# unresolved symbols report
unres = [s for s in syms if s not in key]
print('unresolved syms:', unres[:20])

# ---- rebuild document ----
text_pages = Counter()
for (p, y, x, f, t) in spans: text_pages[t.strip()] += 1
furniture = {t for t, n in text_pages.items() if n >= 5 and len(t) > 5}

out = []
for (p, y, x, f, t) in sorted(spans, key=lambda s: (s[0], s[1], s[2])):
    ts = t.strip()
    if ts in furniture or re.fullmatch(r'\d+ \|.*', ts):
        continue
    if f == 'Tahoma':
        out.append((p, y, ''.join(key.get(c, c) for c in t)))
    elif f in ('ArialMT', 'Arial-BoldMT', 'Arial-ItalicMT', 'Arial-BoldItalicMT'):
        out.append((p, y, t))
    elif f == 'Tahoma-Bold':
        out.append((p, y, '\n§HEADING§\n'))

lines, cur_key, cur = [], None, []
for (p, y, t) in out:
    kk = (p, round(y))
    if kk != cur_key and cur:
        lines.append(' '.join(cur)); cur = []
    cur_key = kk
    cur.append(t.strip())
if cur: lines.append(' '.join(cur))
txt = '\n'.join(lines)
txt = re.sub(r'\n(§HEADING§\n)+', '\n§HEADING§\n', txt)
open('data/2022/2022-Citizens-Budget_English.decoded.txt', 'w').write(txt)
print('chars:', len(txt))
print(txt[3000:4200])
json.dump(key, open('data/2022/eng_tahoma_key.json', 'w'), ensure_ascii=False, indent=1)

"""Crack the per-font substitution 'cipher' in the 2022 Twi Citizens Budget PDF.

The PDF was authored with legacy Ghanaian fonts; the embedded subsets carry a
broken ToUnicode map, so extracted text is a fixed 1:1 symbol substitution of
the real text. We recover the mapping by hill-climbing against character
quadgram statistics built from the clean 2023 Twi Citizens Budget text.
"""
import fitz, json, math, random, re, sys, unicodedata
import numpy as np
from collections import Counter, defaultdict

random.seed(7)

PDF = 'data/2022/2022-Citizens-Budget_Asante_Twi.pdf'
REF = 'data/2023/2023-Citizens-Budget_Asante_Twi.raw.txt'

# ---------- 1. collect ciphertext lines per font ----------
doc = fitz.open(PDF)
font_lines = defaultdict(list)          # font -> list of line strings
spans_all = []                           # (page, y, x, font, text) for later rebuild
for pno, pg in enumerate(doc):
    for blk in pg.get_text('dict')['blocks']:
        for line in blk.get('lines', []):
            for sp in line['spans']:
                t = sp['text']
                if t.strip():
                    f = sp['font'].split('+')[-1]
                    font_lines[f].append(t)
                    spans_all.append((pno, round(sp['bbox'][1], 1), round(sp['bbox'][0], 1), f, t))
json.dump(spans_all, open('data/2022/twi_spans.json', 'w'))

# ---------- 2. reference quadgram model from 2023 Twi ----------
ref = open(REF).read()
ref = ref.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
ref = ref.replace('–', '-').replace('', ' ')
ref = re.sub(r'\s+', ' ', ref)

plain_alpha = [c for c, n in Counter(ref).most_common() if n >= 3]
P = len(plain_alpha)
pidx = {c: i for i, c in enumerate(plain_alpha)}
print(f'plain alphabet ({P}):', ''.join(plain_alpha))

ridx = np.array([pidx.get(c, -1) for c in ref])
quad = np.full((P, P, P, P), -13.0, dtype=np.float32)   # log-prob floor
cnt = Counter()
for i in range(len(ridx) - 3):
    a, b, c, d = ridx[i:i+4]
    if a >= 0 and b >= 0 and c >= 0 and d >= 0:
        cnt[(a, b, c, d)] += 1
tot = sum(cnt.values())
for k, n in cnt.items():
    quad[k] = math.log(n / tot)

def solve(cipher_lines, label, iters=4000, restarts=8):
    text = ' '.join(cipher_lines)
    csyms = [c for c, n in Counter(text).most_common() if n >= 2]
    C = len(csyms)
    cidx = {c: i for i, c in enumerate(csyms)}
    # encode ciphertext as symbol indices; -1 for rare symbols (skipped in scoring)
    enc = np.array([cidx.get(c, -1) for c in text])
    mask = enc >= 0
    print(f'[{label}] {len(text)} chars, {C} cipher symbols')

    def score(key):                       # key: np array, cipher idx -> plain idx
        m = key[enc[mask]]
        # rebuild with -1 breaks where rare symbols were: approximate by scoring contiguous quadgrams
        a, b, c, d = m[:-3], m[1:-2], m[2:-1], m[3:]
        return quad[a, b, c, d].sum()

    best_key, best_sc = None, -np.inf
    # frequency-order initial key
    freq_init = np.zeros(C, dtype=int)
    for i, s in enumerate(csyms):
        freq_init[i] = i if i < P else P - 1
    for r in range(restarts):
        key = freq_init.copy() if r == 0 else np.random.permutation(P)[:C] if C <= P else None
        if key is None:
            key = np.concatenate([np.random.permutation(P), np.random.randint(0, P, C - P)])
        sc = score(key)
        for it in range(iters):
            i, j = random.randrange(C), random.randrange(C)
            if i == j: continue
            key[i], key[j] = key[j], key[i]
            s2 = score(key)
            if s2 > sc:
                sc = s2
            else:
                key[i], key[j] = key[j], key[i]
        if sc > best_sc:
            best_sc, best_key = sc, key.copy()
        print(f'  restart {r}: {sc:.0f} (best {best_sc:.0f})')
    mapping = {csyms[i]: plain_alpha[best_key[i]] for i in range(C)}
    dec = ''.join(mapping.get(c, c) for c in text)
    print(f'[{label}] sample:', dec[:300])
    return mapping

results = {}
for font in ['Tahoma', 'Tahoma-Bold', 'Calibri', 'Cambria-Italic']:
    if font_lines.get(font):
        results[font] = solve(font_lines[font], font)

json.dump(results, open('data/2022/cipher_keys.json', 'w'), ensure_ascii=False, indent=1)
print('saved data/2022/cipher_keys.json')

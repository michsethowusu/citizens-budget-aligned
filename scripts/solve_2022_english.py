"""Crack the ciphered fonts in the 2022 English Citizens Budget PDF
(quadgram hill-climb on 2023 English stats + word-level refinement)."""
import fitz, json, math, random, re
import numpy as np
from collections import Counter, defaultdict

random.seed(7)

doc = fitz.open('data/2022/2022-Citizens-Budget_English.pdf')
spans = []
for pno, pg in enumerate(doc):
    for blk in pg.get_text('dict')['blocks']:
        for line in blk.get('lines', []):
            for sp in line['spans']:
                if sp['text'].strip():
                    spans.append((pno, round(sp['bbox'][1], 1), round(sp['bbox'][0], 1),
                                  sp['font'].split('+')[-1], sp['text']))
json.dump(spans, open('data/2022/eng_spans.json', 'w'))

ref = open('data/2023/2023-Citizens-Budget_English.raw.txt').read()
ref = ref.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
ref = ref.replace('–', '-').replace('', ' ')
ref = re.sub(r'\s+', ' ', ref)

plain_alpha = [c for c, n in Counter(ref).most_common() if n >= 3]
P = len(plain_alpha)
pidx = {c: i for i, c in enumerate(plain_alpha)}
ridx = np.array([pidx.get(c, -1) for c in ref])
quad = np.full((P, P, P, P), -13.0, dtype=np.float32)
cnt = Counter()
for i in range(len(ridx) - 3):
    a, b, c, d = ridx[i:i+4]
    if min(a, b, c, d) >= 0:
        cnt[(a, b, c, d)] += 1
tot = sum(cnt.values())
for kk, n in cnt.items():
    quad[kk] = math.log(n / tot)

vocab = {w.lower() for w in re.findall(r"[A-Za-z']+", ref) if len(w) > 1}
vocab |= {w.lower() for w in re.findall(r"[A-Za-z']+",
          open('data/2022/2022-Citizens-Budget_Asante_Twi.decoded.txt').read())}
vocab |= {'a', 'i', 'covid', 'gh', 'gdp', 'imf', 'mofep', 'www', 'gov'}
years = {str(y) for y in range(1980, 2031)}

def crack(font, iters=4000, restarts=8):
    text = ' '.join(t for (_, _, _, f, t) in spans if f == font)
    syms = [c for c, n in Counter(text).most_common() if n >= 2]
    C = len(syms)
    cidx = {c: i for i, c in enumerate(syms)}
    enc = np.array([cidx[c] for c in text if c in cidx])
    print(f'[{font}] {len(text)} chars, {C} symbols')

    def score(key):
        m = key[enc]
        return quad[m[:-3], m[1:-2], m[2:-1], m[3:]].sum()

    best_key, best_sc = None, -np.inf
    for r in range(restarts):
        if r == 0:
            key = np.array([i if i < P else P - 1 for i in range(C)])
        else:
            key = np.concatenate([np.random.permutation(P),
                                  np.random.randint(0, P, max(0, C - P))])[:C]
        sc = score(key)
        for _ in range(iters):
            i, j = random.randrange(C), random.randrange(C)
            if i == j: continue
            key[i], key[j] = key[j], key[i]
            s2 = score(key)
            if s2 > sc: sc = s2
            else: key[i], key[j] = key[j], key[i]
        if sc > best_sc: best_sc, best_key = sc, key.copy()
    mapping = {syms[i]: plain_alpha[best_key[i]] for i in range(C)}

    # ---- word-level refinement ----
    space_syms = {s for s in syms if mapping[s] == ' '} or {max(syms, key=text.count)}
    tokpat = re.compile('[' + ''.join(re.escape(s) for s in space_syms) + r'\s]+')
    tokens = Counter(t for t in tokpat.split(text) if t)
    sym2toks = defaultdict(set)
    for t in tokens:
        for s in set(t): sym2toks[s].add(t)
    pool = sorted(set(mapping.values()))

    def tsc(t, k):
        d = ''.join(k.get(c, c) for c in t).strip('.,:;()%-"\'')
        if not d: return 0
        return len(d) * tokens[t] if (d.lower() in vocab or d in years) else 0

    cur = sum(tsc(t, mapping) for t in tokens)
    for _ in range(6):
        improved = False
        for si in syms:
            if si in space_syms: continue
            old = mapping[si]
            before = sum(tsc(t, mapping) for t in sym2toks[si])
            bestc, bestg = None, 0
            for c in pool:
                if c == old: continue
                mapping[si] = c
                g = sum(tsc(t, mapping) for t in sym2toks[si]) - before
                if g > bestg: bestg, bestc = g, c
            mapping[si] = bestc if bestc else old
            if bestc: improved = True
        if not improved: break
    nch = sum(len(t) * n for t, n in tokens.items())
    fin = sum(tsc(t, mapping) for t in tokens)
    print(f'[{font}] word coverage {fin}/{nch} = {fin/nch:.1%}')
    dec = ''.join(mapping.get(c, c) for c in text[:300])
    print(f'[{font}]', dec[:280])
    return mapping

out = {}
for font in ['Tahoma', 'Tahoma-Bold', 'Calibri']:
    out[font] = crack(font)
json.dump(out, open('data/2022/eng_cipher_keys.json', 'w'), ensure_ascii=False, indent=1)

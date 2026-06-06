"""Refine the hill-climbed Tahoma key with a word-level objective:
maximize chars covered by tokens found in a Twi/English vocabulary built
from the clean 2023 documents."""
import json, re, random
from collections import Counter, defaultdict

random.seed(11)

keys = json.load(open('data/2022/cipher_keys.json'))
spans = json.load(open('data/2022/twi_spans.json'))

# ---------- vocabulary ----------
vocab = set()
for p in ['data/2023/2023-Citizens-Budget_Asante_Twi.raw.txt',
          'data/2023/2023-Citizens-Budget_English.raw.txt']:
    for w in re.findall(r"[A-Za-zɛɔƐƆ']+", open(p).read()):
        if len(w) > 1:
            vocab.add(w.lower())
vocab |= {'covid', 'gh', 'imf', 'gdp', 'a', 'na', 'no', 'ne', 'mu', 'ho', 'so', 'wɔ', 'yɛ', 'sɛ', 'de', 'ma', 'nti', 'bi', 'firi', 'kɔ', 'ba', 'da'}
years = {str(y) for y in range(1990, 2031)}
print('vocab size', len(vocab))

def refine(font, iters_per_round=6):
    key = dict(keys[font])
    text = ' '.join(t for (_, _, _, f, t) in spans if f == font)
    syms = [s for s, n in Counter(text).most_common() if n >= 2]
    # the space symbol = whatever currently maps to space (trust it, freq is decisive)
    space_syms = {s for s in syms if key.get(s) == ' '}
    # token types as tuples of cipher symbols
    tok_pat = re.compile('[' + ''.join(re.escape(s) for s in space_syms) + r'\s]+')
    tokens = Counter(t for t in tok_pat.split(text) if t)
    sym2toks = defaultdict(set)
    for t in tokens:
        for s in set(t):
            sym2toks[s].add(t)

    plain_pool = sorted({v for v in key.values()})  # alphabet to permute within

    def tok_score(tok, k):
        dec = ''.join(k.get(c, c) for c in tok).strip('.,:;()%-–"\'’“”')
        if not dec:
            return 0
        low = dec.lower()
        if low in vocab or low in years:
            return len(dec) * tokens[tok]
        return 0

    def total_score(k):
        return sum(tok_score(t, k) for t in tokens)

    cur = total_score(key)
    base = cur
    improved = True
    rounds = 0
    while improved and rounds < iters_per_round:
        improved = False
        rounds += 1
        for i in range(len(syms)):
            si = syms[i]
            if si in space_syms: continue
            for j in range(i + 1, len(syms)):
                sj = syms[j]
                if sj in space_syms: continue
                # swap plaintext assignments of si, sj
                affected = sym2toks[si] | sym2toks[sj]
                before = sum(tok_score(t, key) for t in affected)
                key[si], key[sj] = key.get(sj, sj), key.get(si, si)
                after = sum(tok_score(t, key) for t in affected)
                if after > before:
                    cur += after - before
                    improved = True
                else:
                    key[si], key[sj] = key.get(sj, sj), key.get(si, si)
        # also try remapping each symbol to ANY plaintext char (non-bijective fix)
        for si in syms:
            if si in space_syms: continue
            bestc, bestgain = None, 0
            old = key.get(si, si)
            beforev = sum(tok_score(t, key) for t in sym2toks[si])
            for c in plain_pool:
                if c == old: continue
                key[si] = c
                g = sum(tok_score(t, key) for t in sym2toks[si]) - beforev
                if g > bestgain:
                    bestgain, bestc = g, c
            key[si] = bestc if bestc else old
            if bestc:
                cur += bestgain
                improved = True
    n_chars = sum(len(t) * n for t, n in tokens.items())
    matched = total_score(key)
    print(f'[{font}] word-coverage {base}->{matched} of ~{n_chars} token-chars '
          f'({matched / n_chars:.1%})')
    dec = ''.join(key.get(c, c) for c in text[:400])
    print(f'[{font}] sample:', dec[:350].replace(chr(10), ' '))
    return key

refined = {}
for font in ['Tahoma', 'Tahoma-Bold', 'Calibri', 'Cambria-Italic']:
    if font in keys:
        # seed bold variants from the regular variant if it scores better
        if font == 'Tahoma-Bold':
            keys[font] = dict(keys['Tahoma'])  # same legacy layout hypothesis
        refined[font] = refine(font)

json.dump(refined, open('data/2022/cipher_keys_refined.json', 'w'), ensure_ascii=False, indent=1)
print('saved data/2022/cipher_keys_refined.json')

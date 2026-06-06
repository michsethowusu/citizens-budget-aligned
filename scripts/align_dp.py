"""Monotone DP sentence alignment with lexical anchors.

Similarity = shared numeric tokens + shared Latin/English tokens + length ratio.
DP ops: 1-1 match, 1-2 / 2-1 merge, 1-0 / 0-1 skip. Band-constrained.
Outputs data/<year>/dp_pairs.tsv (unfiltered; QE filtering happens separately).
"""
import re, sys

GAP = -0.08          # skip penalty
MERGE_PEN = -0.05    # extra cost for 1-2 / 2-1
BAND = 0.20

EN_STOP = {'the', 'and', 'of', 'to', 'in', 'a', 'for', 'on', 'is', 'are', 'was',
           'will', 'be', 'by', 'with', 'as', 'at', 'from', 'that', 'this', 'an'}

def feats(s):
    nums = set(re.findall(r'\d[\d.,]*%?', s))
    # Latin-ish tokens: in Twi text these are retained English terms/names
    lat = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", s)
           if not re.search(r'[ɛɔƐƆ]', w)} - EN_STOP
    return nums, lat, max(len(s), 1)

def sim(ftw, fen):
    n1, l1, c1 = ftw
    n2, l2, c2 = fen
    parts, weights = [], []
    if n1 or n2:
        parts.append(len(n1 & n2) / max(len(n1 | n2), 1)); weights.append(0.5)
    if l1 or l2:
        parts.append(len(l1 & l2) / max(len(l1 | l2), 1)); weights.append(0.3)
    # Twi runs ~10-25% longer than English for same content
    r = min(c1, c2 * 1.18) / max(c1, c2 * 1.18)
    parts.append(r); weights.append(0.2)
    return sum(p * w for p, w in zip(parts, weights)) / sum(weights)

def merge_feats(f1, f2):
    return (f1[0] | f2[0], f1[1] | f2[1], f1[2] + f2[2])

def align(year):
    tw = [l.strip() for l in open(f'data/{year}/sentences_tw.txt') if l.strip()]
    en = [l.strip() for l in open(f'data/{year}/sentences_en.txt') if l.strip()]
    N, M = len(tw), len(en)
    ftw = [feats(s) for s in tw]
    fen = [feats(s) for s in en]

    NEG = float('-inf')
    D = [[NEG] * (M + 1) for _ in range(N + 1)]
    bp = [[None] * (M + 1) for _ in range(N + 1)]
    D[0][0] = 0.0
    for i in range(N + 1):
        for j in range(M + 1):
            if D[i][j] == NEG: continue
            if i < N and j < M and abs(i / N - j / M) > BAND:
                pass
            cands = []
            if i < N: cands.append((i + 1, j, GAP, 'skip_tw', None))
            if j < M: cands.append((i, j + 1, GAP, 'skip_en', None))
            if i < N and j < M:
                cands.append((i + 1, j + 1, sim(ftw[i], fen[j]), '1-1', (i, j)))
            if i < N and j + 1 < M:
                s = sim(ftw[i], merge_feats(fen[j], fen[j + 1])) + MERGE_PEN
                cands.append((i + 1, j + 2, s, '1-2', (i, (j, j + 1))))
            if i + 1 < N and j < M:
                s = sim(merge_feats(ftw[i], ftw[i + 1]), fen[j]) + MERGE_PEN
                cands.append((i + 2, j + 1, s, '2-1', ((i, i + 1), j)))
            for ni, nj, g, op, pair in cands:
                if ni <= N and nj <= M and abs(ni / N - nj / M) <= BAND:
                    if D[i][j] + g > D[ni][nj]:
                        D[ni][nj] = D[i][j] + g
                        bp[ni][nj] = (i, j, op, pair)

    # backtrace
    out = []
    i, j = N, M
    while (i, j) != (0, 0) and bp[i][j] is not None:
        pi, pj, op, pair = bp[i][j]
        if op == '1-1':
            ti, ej = pair
            out.append((tw[ti], en[ej], sim(ftw[ti], fen[ej])))
        elif op == '1-2':
            ti, (j1, j2) = pair
            out.append((tw[ti], en[j1] + ' ' + en[j2],
                        sim(ftw[ti], merge_feats(fen[j1], fen[j2]))))
        elif op == '2-1':
            (i1, i2), ej = pair
            out.append((tw[i1] + ' ' + tw[i2], en[ej],
                        sim(merge_feats(ftw[i1], ftw[i2]), fen[ej])))
        i, j = pi, pj
    out.reverse()
    with open(f'data/{year}/dp_pairs.tsv', 'w') as f:
        f.write('anchor_sim\ttwi\tenglish\n')
        for t, e, s in out:
            f.write(f'{s:.4f}\t{t}\t{e}\n')
    print(f'[{year}] {N}tw x {M}en -> {len(out)} DP-aligned pairs '
          f'(coverage {len(out)/min(N,M):.0%})')

for year in sys.argv[1:]:
    align(year)

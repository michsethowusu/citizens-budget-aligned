"""Align Twi and English Citizens-Budget sentences with the GhanaNLP QE model.

Strategy: the documents are parallel in structure, so each Twi sentence only
considers English candidates within a relative-position window. All candidate
pairs are scored with ghananlpcommunity/twi-eng-qe-e5 (P(correct translation)),
then mutual-best pairs above a threshold are kept.
"""
import sys, json, torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL = 'ghananlpcommunity/twi-eng-qe-e5'
WINDOW = 0.18          # relative-position window
THRESHOLD = 0.70       # min P(correct)
BATCH = 128

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)
model.eval()
model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
torch.set_num_threads(4)

def score_pairs(pairs):
    """pairs: list of (twi, en) -> np.array of P(correct)"""
    texts = [f'query: {tw} passage: {en}' for tw, en in pairs]
    # length-sorted batching: minimizes padding waste
    order = sorted(range(len(texts)), key=lambda k: len(texts[k]))
    probs = np.zeros(len(texts))
    done = 0
    with torch.no_grad():
        for i in range(0, len(order), BATCH):
            idx = order[i:i+BATCH]
            enc = tok([texts[k] for k in idx], return_tensors='pt',
                      truncation=True, max_length=256, padding=True)
            logits = model(**enc).logits
            probs[idx] = logits.softmax(-1)[:, 1].numpy()
            done += len(idx)
            if (i // BATCH) % 10 == 0:
                print(f'  scored {done}/{len(texts)}', flush=True)
    return probs

def align(year):
    tw = [l.strip() for l in open(f'data/{year}/sentences_tw.txt') if l.strip()]
    en = [l.strip() for l in open(f'data/{year}/sentences_en.txt') if l.strip()]
    N, M = len(tw), len(en)
    print(f'[{year}] {N} twi x {M} en sentences')

    cand = []           # (i, j)
    for i in range(N):
        pi = i / max(N - 1, 1)
        for j in range(M):
            if abs(j / max(M - 1, 1) - pi) <= WINDOW:
                cand.append((i, j))
    print(f'[{year}] {len(cand)} candidate pairs')
    probs = score_pairs([(tw[i], en[j]) for i, j in cand])

    S = np.zeros((N, M))
    for (i, j), p in zip(cand, probs):
        S[i, j] = p
    best_en = S.argmax(1)        # for each twi
    best_tw = S.argmax(0)        # for each en
    out = []
    for i in range(N):
        j = best_en[i]
        if best_tw[j] == i and S[i, j] >= THRESHOLD:
            out.append((i, j, S[i, j]))
    print(f'[{year}] mutual-best pairs >= {THRESHOLD}: {len(out)}')
    with open(f'data/{year}/aligned_tw_en.tsv', 'w') as f:
        f.write('score\ttwi\tenglish\n')
        for i, j, p in out:
            f.write(f'{p:.4f}\t{tw[i]}\t{en[j]}\n')
    return len(out)

total = 0
for year in sys.argv[1:]:
    total += align(year)
print('total aligned pairs:', total)

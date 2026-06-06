"""GPU-accelerated Twi-English alignment on Modal.

Usage: modal run scripts/align_modal.py --years 2022,2023

Sends the local sentence lists to a GPU container, scores all positional-window
candidate pairs with ghananlpcommunity/twi-eng-qe-e5 (fp16), and writes
data/<year>/aligned_tw_en.tsv locally.
"""
import modal

MODEL = 'ghananlpcommunity/twi-eng-qe-e5'
WINDOW = 0.18
THRESHOLD = 0.70
BATCH = 512

app = modal.App('twi-eng-align')
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch', 'transformers', 'numpy', 'hf_transfer')
         .env({'HF_HUB_ENABLE_HF_TRANSFER': '1'}))

hf_cache = modal.Volume.from_name('hf-cache', create_if_missing=True)


@app.function(image=image, gpu='T4', timeout=900,
              volumes={'/root/.cache/huggingface': hf_cache})
def score_pairs(texts: list[str]) -> list[float]:
    import torch
    import numpy as np
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, torch_dtype=torch.float16).cuda().eval()

    order = sorted(range(len(texts)), key=lambda k: len(texts[k]))
    probs = np.zeros(len(texts))
    with torch.no_grad():
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            enc = tok([texts[k] for k in idx], return_tensors='pt',
                      truncation=True, max_length=256, padding=True)
            enc = {k: v.cuda() for k, v in enc.items()}
            logits = model(**enc).logits
            probs[idx] = logits.softmax(-1)[:, 1].float().cpu().numpy()
            print(f'scored {min(i + BATCH, len(order))}/{len(texts)}')
    return probs.tolist()


@app.local_entrypoint()
def main(years: str = '2022,2023'):
    import numpy as np

    for year in years.split(','):
        tw = [l.strip() for l in open(f'data/{year}/sentences_tw.txt') if l.strip()]
        en = [l.strip() for l in open(f'data/{year}/sentences_en.txt') if l.strip()]
        N, M = len(tw), len(en)
        cand = [(i, j) for i in range(N) for j in range(M)
                if abs(j / max(M - 1, 1) - i / max(N - 1, 1)) <= WINDOW]
        print(f'[{year}] {N} twi x {M} en -> {len(cand)} candidate pairs')
        texts = [f'query: {tw[i]} passage: {en[j]}' for i, j in cand]
        probs = score_pairs.remote(texts)

        S = np.zeros((N, M))
        for (i, j), p in zip(cand, probs):
            S[i, j] = p
        best_en, best_tw = S.argmax(1), S.argmax(0)
        out = [(i, best_en[i], S[i, best_en[i]]) for i in range(N)
               if best_tw[best_en[i]] == i and S[i, best_en[i]] >= THRESHOLD]
        print(f'[{year}] mutual-best pairs >= {THRESHOLD}: {len(out)}')
        with open(f'data/{year}/aligned_tw_en.tsv', 'w') as f:
            f.write('score\ttwi\tenglish\n')
            for i, j, p in out:
                f.write(f'{p:.4f}\t{tw[i]}\t{en[j]}\n')

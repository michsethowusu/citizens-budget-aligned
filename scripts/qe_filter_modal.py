"""Score DP-aligned pairs with the GhanaNLP QE model on Modal and write
data/<year>/aligned_qe.tsv with both anchor_sim and qe_score."""
import csv
import modal

MODEL = 'ghananlpcommunity/twi-eng-qe-e5'
BATCH = 512

app = modal.App('twi-eng-qe-filter')
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch', 'transformers', 'numpy', 'hf_transfer')
         .env({'HF_HUB_ENABLE_HF_TRANSFER': '1'}))
hf_cache = modal.Volume.from_name('hf-cache', create_if_missing=True)


@app.function(image=image, gpu='T4', timeout=600,
              volumes={'/root/.cache/huggingface': hf_cache})
def score(texts: list[str]) -> list[float]:
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
            probs[idx] = model(**enc).logits.softmax(-1)[:, 1].float().cpu().numpy()
    return probs.tolist()


@app.local_entrypoint()
def main(years: str = '2021,2022,2023'):
    for year in years.split(','):
        rows = []
        with open(f'data/{year}/dp_pairs.tsv') as f:
            rd = csv.reader(f, delimiter='\t')
            next(rd)
            rows = [r for r in rd if len(r) == 3]
        probs = score.remote([f'query: {tw} passage: {en}' for _, tw, en in rows])
        with open(f'data/{year}/aligned_qe.tsv', 'w') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['anchor_sim', 'qe_score', 'twi', 'english'])
            for (a, tw, en), p in zip(rows, probs):
                w.writerow([a, f'{p:.4f}', tw, en])
        print(f'[{year}] scored {len(rows)} pairs')

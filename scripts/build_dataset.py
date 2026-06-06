"""Merge per-year aligned pairs into the final parallel dataset
(TSV + JSONL with year/score metadata), with near-duplicate removal."""
import csv, json, glob, re, sys

# acceptance: QE approves it, or (for OCR-noisy years) the lexical anchors are strong
def accept(anchor, qe):
    return qe >= 0.70 or anchor >= 0.45

def is_debris(tw, en):
    # table-of-contents / front-matter fragments
    if tw.count('Hyehyɛpono') >= 2 or en.count('Appendix') >= 2:
        return True
    if re.search(r'(www\.|Email|P\.\s*O\.|Box MB)', tw):
        return True
    return False

YEARS = {'2022', '2023'}   # 2021 excluded: OCR-derived Twi is too noisy

rows = []
for tsv in sorted(glob.glob('data/*/aligned_qe.tsv')):
    year = tsv.split('/')[1]
    if year not in YEARS:
        continue
    with open(tsv) as f:
        rd = csv.reader(f, delimiter='\t')
        next(rd)
        for anchor, qe, tw, en in rd:
            if accept(float(anchor), float(qe)) and not is_debris(tw, en):
                rows.append({'year': year, 'anchor': float(anchor),
                             'score': float(qe), 'tw': tw, 'en': en})

def norm(s):
    return re.sub(r'\W+', '', s.lower())

seen, out = set(), []
for r in sorted(rows, key=lambda r: -r['score']):
    k = (norm(r['tw']), norm(r['en']))
    if k in seen:
        continue
    seen.add(k)
    out.append(r)
out.sort(key=lambda r: (r['year'], -r['score']))

with open('dataset/twi_english_citizens_budget.tsv', 'w') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['year', 'qe_score', 'anchor_sim', 'twi', 'english'])
    for r in out:
        w.writerow([r['year'], f"{r['score']:.4f}", f"{r['anchor']:.4f}",
                    r['tw'], r['en']])
with open('dataset/twi_english_citizens_budget.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps({'twi': r['tw'], 'english': r['en'],
                            'year': r['year'], 'qe_score': round(r['score'], 4),
                            'anchor_sim': round(r['anchor'], 4),
                            'domain': 'economy/public-finance',
                            'source': 'MoF Ghana Citizens Budget'}, ensure_ascii=False) + '\n')

by_year = {}
for r in out:
    by_year[r['year']] = by_year.get(r['year'], 0) + 1
print('pairs by year:', by_year, 'total:', len(out))

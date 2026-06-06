"""Assemble + lexicon-correct the OCRed 2021 Twi pages, then segment.

The tesseract Latin model has no ɛ/ɔ training for Twi, so it substitutes
(ə, €, e, o, 9...). We restore diacritics by looking each token up in a
lexicon built from the clean 2022/2023 Twi documents, keyed by the
ascii-folded form (ɛ→e, ɔ→o)."""
import glob, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, 'scripts')
from segment import process

# ---------- lexicon from clean years ----------
def fold(w):
    return (w.replace('ɛ', 'e').replace('ɔ', 'o')
             .replace('Ɛ', 'E').replace('Ɔ', 'O'))

freq = Counter()
for p in ['data/2022/2022-Citizens-Budget_Asante_Twi.decoded.txt',
          'data/2023/2023-Citizens-Budget_Asante_Twi.raw.txt']:
    freq.update(re.findall(r"[A-Za-zɛɔƐƆ']+", open(p).read()))
folded = defaultdict(Counter)
for w, n in freq.items():
    folded[fold(w).lower()][w] += n

def correct_token(tok):
    # char-level normalizations the Latin model produces
    t = (tok.replace('ə', 'ɔ').replace('Ə', 'Ɔ').replace('€', 'Ɛ')
            .replace('з', 'ɛ').replace('ȼ', '¢'))
    # digits glued to letters at word end are usually ɔ/o misreads
    t = re.sub(r'(?<=[a-zɛɔ])9', 'ɔ', t)
    t = re.sub(r'(?<=[a-zɛɔ])0', 'o', t)
    if t in freq or not re.fullmatch(r"[A-Za-zɛɔƐƆ']+", t):
        return t
    cands = folded.get(fold(t).lower())
    if cands:
        best = cands.most_common(1)[0][0]
        # preserve original capitalization style
        if t[0].isupper() and best[0].islower():
            best = (best[0].upper().replace('Ɔ', 'Ɔ').replace('Ɛ', 'Ɛ')) + best[1:]
            if t.isupper(): best = best.upper()
        return best
    return t

pages = sorted(glob.glob('data/2021/ocr/p*.txt'))
out = []
for p in pages:
    out.append(open(p).read())
raw = '\n\n'.join(out)
tokens = re.split(r'(\s+)', raw)
fixed = ''.join(correct_token(t) if not t.isspace() else t for t in tokens)
open('data/2021/2021-Citizens-Budget_Asante_Twi.ocr.txt', 'w').write(fixed)

# quality estimate
toks = [w for w in re.findall(r"[A-Za-zɛɔƐƆ']+", fixed) if len(w) > 1]
vocab = {w.lower() for w in freq}
hit = sum(1 for w in toks if w.lower() in vocab)
print(f'2021 OCR vocab hit-rate after correction: {hit/len(toks):.1%} ({len(toks)} tokens)')

process('data/2021/2021-Citizens-Budget_Asante_Twi.ocr.txt', 'data/2021/sentences_tw.txt')
process('data/2021/2021-Citizens-Budget_English.raw.txt', 'data/2021/sentences_en.txt')

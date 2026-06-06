"""Rebuild the 2022 Twi Citizens Budget plaintext using the cracked per-font keys."""
import json, re
from collections import Counter

keys = json.load(open('data/2022/cipher_keys_refined.json'))
spans = json.load(open('data/2022/twi_spans.json'))

# --- Tahoma: solver key + manual fixes derived from cribs ---
tah = dict(keys['Tahoma'])
tah.update({
    ' ': ' ',          # literal spaces are real spaces
    'b': '7', 'd': '8', 'Y': '4', '>': '9', 'X': '6', 'W': '3', 'T': '5',
    'a': '%', 'f': '$', '\\': '¢', '=': '-', 'o': 'Z', 'i': '“', 'q': '”',
    'p': '–', '_': ',',
})

# --- Arial family: small manual maps (only the legacy special keys differ) ---
ARIAL = {
    'Arial-BoldMT':       {'!': 'Ɔ', '"': 'Ɛ', '#': 'ɛ', '$': 'ɔ'},
    'ArialMT':            {'!': 'Ɔ', '"': 'ɛ', '#': 'ɔ', '$': 'ɔ'},
    'Arial-BoldItalicMT': {'!': 'ɛ', '"': 'Ɔ', '#': 'ɔ', '$': 'ɔ'},
    'Arial-ItalicMT':     {'!': 'ɛ', '"': 'ɛ', '#': 'ɔ', '$': 'ɔ'},
}

def dec_arial(font, t):
    m = ARIAL[font]
    return ''.join(m.get(c, c) for c in t)

def dec_tahoma(t):
    return ''.join(tah.get(c, c) for c in t)

# drop page furniture: spans whose text repeats on many pages (headers/footers)
text_pages = Counter()
for (p, y, x, f, t) in spans:
    text_pages[t.strip()] += 1
furniture = {t for t, n in text_pages.items() if n >= 5 and len(t) > 5}

out, skipped = [], Counter()
for (p, y, x, f, t) in sorted(spans, key=lambda s: (s[0], s[1], s[2])):
    ts = t.strip()
    if ts in furniture or re.fullmatch(r'\d+ \|.*', ts):
        skipped['furniture'] += 1; continue
    if f in ('Tahoma',):
        out.append((p, y, dec_tahoma(t)))
    elif f in ARIAL:
        out.append((p, y, dec_arial(f, t)))
    elif f == 'Tahoma-Bold':
        out.append((p, y, '\n§HEADING§\n'))      # undecoded heading -> section break
        skipped['tahoma-bold'] += 1
    else:
        skipped[f] += 1                           # Calibri/Cambria chart labels etc.

# assemble: join spans on same page/baseline with space, new baseline = newline
lines, cur_key, cur = [], None, []
for (p, y, t) in out:
    k = (p, round(y))
    if k != cur_key and cur:
        lines.append(' '.join(cur)); cur = []
    cur_key = k
    cur.append(t.strip())
if cur: lines.append(' '.join(cur))
txt = '\n'.join(lines)
txt = re.sub(r'\n(§HEADING§\n)+', '\n§HEADING§\n', txt)

open('data/2022/2022-Citizens-Budget_Asante_Twi.decoded.txt', 'w').write(txt)
print('skipped:', dict(skipped))
print('chars:', len(txt))

# quality: fraction of tokens found in 2023 vocab
vocab = set()
for pth in ['data/2023/2023-Citizens-Budget_Asante_Twi.raw.txt',
            'data/2023/2023-Citizens-Budget_English.raw.txt']:
    vocab |= {w.lower() for w in re.findall(r"[A-Za-zɛɔƐƆ']+", open(pth).read())}
toks = [w for w in re.findall(r"[A-Za-zɛɔƐƆ']+", txt) if len(w) > 1]
hit = sum(1 for w in toks if w.lower() in vocab)
print(f'vocab hit-rate: {hit}/{len(toks)} = {hit/len(toks):.1%}')
bad = Counter(w for w in toks if w.lower() not in vocab)
print('top unknown:', bad.most_common(25))

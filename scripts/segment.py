"""Clean extracted Citizens-Budget text and split into sentences.

Outputs data/<year>/sentences_<lang>.txt (one sentence per line)."""
import re, sys
from collections import Counter

ABBREV = r'(?:H\.E|Dr|Mr|Mrs|Prof|Hon|No|P\.O|Rev|St|etc|e\.g|i\.e|Ltd|Co|Inc)\.$'

def clean_lines(txt):
    lines = txt.split('\n')
    counts = Counter(l.strip() for l in lines if l.strip())
    out = []
    for l in lines:
        s = l.strip()
        if not s:
            out.append(''); continue
        if counts[s] >= 3 and len(s) > 10:        # repeated headers/footers/theme
            continue
        if re.search(r'\.{5,}', s):                # TOC dotted lines
            continue
        if re.fullmatch(r'[\d\s|.,;:%()¢$/-]+', s):  # bare numbers / table debris
            continue
        if s == '§HEADING§':
            out.append(''); continue
        s = s.replace('', ' ').replace('', ' ')
        out.append(s)
    return out

def to_paragraphs(lines):
    paras, cur = [], []
    for l in lines:
        if not l.strip():
            if cur: paras.append(' '.join(cur)); cur = []
        else:
            # join hyphenated line-breaks
            if cur and cur[-1].endswith('-') and l and l[0].islower():
                cur[-1] = cur[-1][:-1] + l.split(' ', 1)[0]
                rest = l.split(' ', 1)[1] if ' ' in l else ''
                if rest: cur.append(rest)
            else:
                cur.append(l)
    if cur: paras.append(' '.join(cur))
    return paras

def split_sentences(para):
    para = para.replace('§HEADING§', ' ')
    para = re.sub(r'\s+', ' ', para).strip()
    # strip leading numbered-paragraph markers like "12." / "iv."
    para = re.sub(r'^\(?\d{1,3}[\.\)]\s+(?=[A-ZƐƆ“"])', '', para)
    parts, buf = [], ''
    for chunk in re.split(r'(?<=[.!?])\s+(?=[A-ZƐƆ“"(])', para):
        if buf:
            chunk = buf + ' ' + chunk; buf = ''
        if re.search(ABBREV, chunk) or re.search(r'\d\.$', chunk):
            buf = chunk; continue
        parts.append(chunk)
    if buf: parts.append(buf)
    return parts

def good(s):
    letters = sum(c.isalpha() for c in s)
    if letters < 15 or len(s.split()) < 4: return False
    if letters / len(s) < 0.6: return False
    return True

def process(infile, outfile):
    txt = open(infile).read()
    sents = []
    for p in to_paragraphs(clean_lines(txt)):
        for s in split_sentences(p):
            s = s.strip()
            s = re.sub(r'^[\-–•°*]\s*', '', s)
            s = re.sub(r'\buS\$', 'US$', s)
            if s and s[0].islower():                       # sentence-case fix
                s = s[0].upper() + s[1:]
            if good(s):
                sents.append(s)
    with open(outfile, 'w') as f:
        f.write('\n'.join(sents))
    print(f'{outfile}: {len(sents)} sentences')

if __name__ == '__main__':
    jobs = [
        ('data/2022/2022-Citizens-Budget_Asante_Twi.decoded.txt', 'data/2022/sentences_tw.txt'),
        ('data/2022/2022-Citizens-Budget_English.decoded.txt',    'data/2022/sentences_en.txt'),
        ('data/2023/2023-Citizens-Budget_Asante_Twi.raw.txt',     'data/2023/sentences_tw.txt'),
        ('data/2023/2023-Citizens-Budget_English.raw.txt',        'data/2023/sentences_en.txt'),
    ]
    for i, o in jobs:
        process(i, o)

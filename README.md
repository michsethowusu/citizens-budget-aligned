# Twi–English Citizens' Budget Parallel Corpus

Parallel sentences (Asante Twi ↔ English) in the **economy / public-finance domain**,
extracted from the Government of Ghana *Citizens' Budget* publications
(<https://www.mofep.gov.gh/publications/citizens-budget>).

## Dataset

- `dataset/twi_english_citizens_budget.tsv` / `.jsonl` — **317 sentence pairs**
  - 2022: 146 · 2023: 171
- Columns: `year`, `qe_score` (P(correct) from `ghananlpcommunity/twi-eng-qe-e5`),
  `anchor_sim` (lexical-anchor similarity used by the aligner), `twi`, `english`.
- Filter for higher precision with `qe_score >= 0.9` (~180 pairs).
- 2021 is deliberately **excluded**: its Twi PDF is scanned, and the OCR-derived
  text carries character noise (`stoo` ↔ `ɛtoɔ`). The full 2021 pipeline output is
  still available at `data/2021/aligned_qe.tsv` (284 scored pairs) if silver data
  is ever wanted.

## Source documents

`data/<year>/` holds all 23 PDFs (2021–2025; English, Asante Twi, Dagbani, Dangme,
Ewe, Ga, Gonja, Nzema where published — fetch with `scripts/download.sh`). Twi
exists only for 2021–2023; English-only for 2024/2025.

## Align it for your language!

Only the Twi↔English pair has been aligned so far, but the same documents exist
in **Dagbani, Dangme, Ewe, Ga, Gonja and Nzema** — and the aligner
(`scripts/align_dp.py`) is language-independent: it matches on shared numbers,
retained English terms and length ratio, so it should work for any of these
languages against English with no model needed. The 2022 PDFs for other
languages may need the same cipher-cracking treatment as Twi
(`scripts/solve_2022_cipher.py` — use a clean 2023 same-language document as
the reference). Contributions welcome.

## Pipeline (scripts/, in order)

1. **Extraction** — PyMuPDF. 2023 PDFs have clean Unicode text.
2. **Cipher cracking (2022, both languages)** — the 2022 PDFs were authored with
   legacy Ghanaian fonts whose embedded subsets carry broken ToUnicode maps, so
   extracted text is a per-font 1:1 symbol substitution cipher.
   - `solve_2022_cipher.py` — quadgram hill-climb against clean 2023 Twi stats
   - `refine_2022_cipher.py` — word-level refinement against 2023 vocabulary
   - `decode_2022.py` / `decode_2022_english.py` — manual crib fixes
     (e.g. `1D1F`, `COVID-19`, `US$11.44 billion`, Isaiah 9:10, info@mofep.gov.gh)
     and document rebuild. Body fonts fully decoded (90%+ vocab hit-rate);
     bold-heading font left as section markers (too little text to crack).
   - Digits were cross-validated **between the two language versions** (shared
     figures like `15,656,160` NIA registrations, `3.5%` GDP growth).
3. **OCR (2021 Twi)** — the PDF is scanned images. tesseract `Latin` script model
   (no Twi support) + `fix_2021_ocr.py`: lexicon built from clean 2022/2023 Twi
   restores ɛ/ɔ diacritics by ascii-folded lookup (82% vocab hit-rate).
4. **Segmentation** — `segment.py`: header/footer & TOC removal, paragraph
   reassembly, abbreviation-aware sentence split (no split on `;` — budget list
   style).
5. **Alignment** — `align_dp.py`: monotone dynamic-programming alignment
   (1-1, 1-2, 2-1, skips; ±20% positional band) scored by lexical anchors —
   shared numbers, shared Latin/English terms retained in the Twi text, and
   length ratio. Budget text is anchor-dense, which makes this very reliable.
6. **QE filtering** — `qe_filter_modal.py`: every aligned pair scored with
   `ghananlpcommunity/twi-eng-qe-e5` on a Modal T4 GPU (fp16).
   `build_dataset.py` accepts pairs with `qe_score >= 0.70` **or**
   `anchor_sim >= 0.45` (the QE model under-rates OCR-noisy 2021 text), then
   dedupes and drops front-matter debris.

### Notes / lessons

- The QE model **saturates (~0.99) on topically-related non-translations**, so it
  cannot rank alignment candidates — earlier mutual-best matching with it failed.
  It works well as a *binary filter* on top of a structural aligner.
- `align.py` / `align_modal.py` are the (deprecated) QE-as-ranker attempts kept
  for reference; `align_modal.py` shows the Modal GPU scoring pattern.

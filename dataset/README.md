---
language:
- tw
- en
license: cc-by-4.0
task_categories:
- translation
tags:
- parallel-corpus
- twi
- akan
- ghana
- economy
- public-finance
- government
pretty_name: Twi-English Citizens' Budget Parallel Corpus
size_categories:
- n<1K
---

# Twi–English Citizens' Budget Parallel Corpus

**317 Asante Twi ↔ English parallel sentences** in the economy / public-finance
domain, extracted and aligned from the Government of Ghana
[*Citizens' Budget*](https://www.mofep.gov.gh/publications/citizens-budget)
publications (2022 and 2023 editions, translated by the Bureau of Ghana
Languages).

## Fields

| field | description |
|---|---|
| `twi` | Asante Twi sentence |
| `english` | English sentence |
| `year` | source publication year (2022 / 2023) |
| `qe_score` | P(correct translation) from [`ghananlpcommunity/twi-eng-qe-e5`](https://huggingface.co/ghananlpcommunity/twi-eng-qe-e5) |
| `anchor_sim` | lexical-anchor similarity from the structural aligner (shared numbers, retained English terms, length ratio) |
| `domain`, `source` | constant metadata |

For a high-precision subset, filter `qe_score >= 0.9` (~189 pairs). Pairs with
`qe_score < 0.7` were admitted on strong lexical anchors (`anchor_sim >= 0.45`);
spot-checks show these are mostly correct, number-dense sentences that the QE
model under-rates.

## How it was built

The 2022 PDFs embed legacy Ghanaian fonts with broken ToUnicode maps, so the
extracted text is a per-font substitution cipher — cracked with character
quadgram statistics from the clean 2023 documents plus manual cribs, and digits
cross-validated between the two language versions. Sentences were aligned with
a monotone dynamic-programming aligner driven by lexical anchors, then filtered
with the GhanaNLP Twi-English QE model. Full pipeline:
<https://github.com/michsethowusu/citizens-budget-aligned-twi>

The 2021 edition exists only as a scanned PDF; its OCR-derived pairs are
excluded from this release (available as silver data in the GitHub repo).

## Attribution

Source text © Government of Ghana, Ministry of Finance — Citizens' Budget
publications; Twi translations by the Bureau of Ghana Languages.
Alignment and curation by the GhanaNLP community.

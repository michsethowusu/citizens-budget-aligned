#!/usr/bin/env bash
# Download all Citizens' Budget PDFs from MoFEP into data/<year>/ folders.
# (PDFs are not committed to git; run this to re-fetch them.)
set -euo pipefail
base="https://www.mofep.gov.gh"
urls="
/sites/default/files/basic-page/2023-Citizens-Budget_Asante_Twi.pdf
/sites/default/files/basic-page/2023-Citizens-Budget_Dagbani.pdf
/sites/default/files/basic-page/2023-Citizens-Budget_Dangme.pdf
/sites/default/files/basic-page/2023-Citizens-Budget_Ewe.pdf
/sites/default/files/basic-page/2023-Citizens-Budget_Gonja.pdf
/sites/default/files/basic-page/2023-Citizens-Budget_Nzema.pdf
/sites/default/files/basic-page/2023-Citizens-Budget.pdf
/sites/default/files/basic-page/2024-Citizens-Budget.pdf
/sites/default/files/basic-page/2025-Citizens-Budget.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_Asante_Twi.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_Dagbani.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_English.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_Ewe.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_Ga.pdf
/sites/default/files/citizens-budget/2021-Citizens-Budget_Nzema.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Asante_Twi.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Dagbani.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Dangme.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_English.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Ewe.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Ga.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Gonja.pdf
/sites/default/files/citizens-budget/2022-Citizens-Budget_Nzema.pdf
"
for u in $urls; do
  f=$(basename "$u"); year=$(echo "$f" | grep -oE '^20[0-9]{2}')
  case "$f" in *_*) out="$f";; *) out="${f%.pdf}_English.pdf";; esac
  mkdir -p "data/$year"
  [ -f "data/$year/$out" ] || { curl -sfL "$base$u" -o "data/$year/$out" && echo "OK  $year/$out"; }
done

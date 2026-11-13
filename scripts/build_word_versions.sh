#!/usr/bin/env bash
# Build both Word versions of the manuscript: the clean copy and the tracked-changes copy (revisions in blue).
# Run from anywhere; needs quarto and python3. Writes paper/K-S-Database-Resource-Paper.docx and
# paper/K-S-Database-Resource-Paper_revised.docx.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/mark_revisions.py
quarto render paper/K-S-Database-Resource-Paper.qmd --to elsevier-docx
quarto render paper/K-S-Database-Resource-Paper_revised.qmd --to elsevier-docx
python3 scripts/finalize_docx.py paper/K-S-Database-Resource-Paper.docx
python3 scripts/finalize_docx.py --revised paper/K-S-Database-Resource-Paper_revised.docx

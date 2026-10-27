#!/bin/bash
# Build the tutorial PDF from README.md: pandoc -> HTML -> WeasyPrint.
# Usage: tools/pdf/build_pdf.sh [output.pdf]   (default: iq-9075-tutorial.pdf at the repo root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/iq-9075-tutorial.pdf}"
CSS="$ROOT/tools/pdf/tutorial.css"
cd "$ROOT"
title=$(grep -m1 '^# ' README.md | sed 's/^# //')
html="$ROOT/tools/pdf/tutorial.html"
# no implicit figures: the long alt texts stay as alt text, not as visible captions
pandoc README.md -f markdown-implicit_figures -t html5 --standalone \
  --metadata title="$title" --metadata lang=en -V pagetitle="$title" \
  --css "$CSS" -o "$html"
# pandoc's standalone template repeats the title; drop its header block
python3 - "$html" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p).read()
s = re.sub(r'<header id="title-block-header">.*?</header>', '', s, flags=re.S)
open(p, "w").write(s)
PY
weasyprint --base-url "$ROOT/" "$html" "$OUT"
rm "$html"
echo "$OUT"

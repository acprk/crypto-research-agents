#!/usr/bin/env bash
# Grep the repo against a local deny-list before pushing. Exit 1 on any hit.
# Deny-list: .privacy-denylist (git-ignored), one extended regex per line, '#' comments.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; LIST="${1:-$ROOT/.privacy-denylist}"
[ -f "$LIST" ] || { echo "no deny-list at $LIST (create one; it is git-ignored)"; exit 2; }
PAT=$(grep -vE '^\s*(#|$)' "$LIST" | paste -sd'|')
HITS=$(grep -rniIE "$PAT" "$ROOT" --exclude-dir=.git --exclude=.privacy-denylist || true)
# also scan text inside PDFs we ship
while IFS= read -r f; do
  pdftotext -q "$f" - 2>/dev/null | grep -qiE "$PAT" && HITS+=$'\n'"PDF text hit: $f"
  pdfinfo "$f" 2>/dev/null | grep -qiE "$PAT" && HITS+=$'\n'"PDF metadata hit: $f"
done < <(find "$ROOT" -name '*.pdf' -not -path '*/.git/*')
if [ -n "$HITS" ]; then echo "$HITS"; echo "PRIVACY SCAN FAILED"; exit 1; fi
echo "privacy scan clean"

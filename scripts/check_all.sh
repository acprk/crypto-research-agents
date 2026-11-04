#!/usr/bin/env bash
# Run every automated check in the repo: unit tests, script self-tests, and the
# case-study gates. Used by CI (.github/workflows/ci.yml) and before every push.
#   scripts/check_all.sh            # all checks
#   scripts/check_all.sh --quick    # skip the figure-rendering tests (slowest part)
# Needs: pip install -e "lib/core[test]" -e "lib/cryptomath[test,plot]" -e "lib/bench[test]" pymupdf
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
PY="${PYTHON:-python3}"; QUICK=0; [ "${1:-}" = "--quick" ] && QUICK=1
FAILED=()
run() { local name="$1"; shift; echo "::group::$name"; if "$@"; then echo "ok   $name"; else echo "FAIL $name"; FAILED+=("$name"); fi; echo "::endgroup::"; }

"$PY" -c "import pytest" 2>/dev/null || { echo "pytest missing: pip install -e 'lib/core[test]' -e 'lib/cryptomath[test]' -e 'lib/bench[test]'"; exit 2; }

run "pytest lib/core"         bash -c "cd lib/core && $PY -m pytest -q"
run "pytest lib/cryptomath"   bash -c "cd lib/cryptomath && $PY -m pytest -q"
run "pytest lib/bench"        bash -c "cd lib/bench && $PY -m pytest -q"
run "pytest skills"           "$PY" -m pytest -q skills/anonymize-check/tests
[ $QUICK = 1 ] || run "pytest figures" "$PY" -m pytest -q figures/tests

for s in skills/phase-gate/scripts/gate_check.py skills/bib-verify/scripts/verify_bib.py \
         skills/camera-ready/scripts/pdf_checks.py skills/textbook-index/scripts/extract_toc.py \
         skills/param-estimation/scripts/core_svp_screen.py skills/anonymize-check/scripts/anon_check.py \
         skills/eprint-search/scripts/eprint_search.py skills/lit-matrix/scripts/lit_matrix.py \
         skills/idea-mining-loop/scripts/toy_mining_demo.py \
         figures/harvester/harvest.py figures/harvester/gallery.py; do
  run "selftest $s" "$PY" "$s" --selftest
done

CS=case-study/toy-mvpbs
for ph in P6 P7 P8; do
  run "case-study gate $ph" "$PY" skills/phase-gate/scripts/gate_check.py --project "$CS" --phase "$ph" --paper paper
done
run "case-study audit-tex" "$PY" -m crbench audit-tex "$CS/paper/main.tex" "$CS/EVIDENCE.md"

echo
if [ ${#FAILED[@]} -gt 0 ]; then printf 'FAILED: %s\n' "${FAILED[@]}"; exit 1; fi
echo "all checks passed"

#!/usr/bin/env bash
# Zero-sorry gate: fails if any proof escape hatch appears in project sources.
# Usage: ./scripts_check_no_sorry.sh [dir]   (run from the Lean project root)
set -euo pipefail
dir="${1:-CryptoTemplate}"
if grep -RnE '\b(sorry|admit)\b|^\s*axiom\s|native_decide' --include='*.lean' "$dir" CryptoTemplate.lean 2>/dev/null; then
  echo "FAIL: proof escape hatch found (sorry/admit/axiom/native_decide)" >&2
  exit 1
fi
echo "OK: no sorry/admit/axiom/native_decide in $dir"

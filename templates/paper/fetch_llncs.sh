#!/bin/sh
# fetch_llncs.sh -- obtain Springer's llncs.cls and splncs04.bst without vendoring them.
# 1) If TeX Live/MiKTeX already provides them, do nothing.
# 2) Otherwise download the official package from CTAN into this directory.
set -eu
if kpsewhich llncs.cls >/dev/null 2>&1 && kpsewhich splncs04.bst >/dev/null 2>&1; then
  echo "llncs.cls and splncs04.bst found in the TeX installation: $(kpsewhich llncs.cls)"
  exit 0
fi
URL="https://mirrors.ctan.org/macros/latex/contrib/llncs.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "downloading $URL"
if command -v curl >/dev/null 2>&1; then curl -fsSL "$URL" -o "$TMP/llncs.zip"
elif command -v wget >/dev/null 2>&1; then wget -q "$URL" -O "$TMP/llncs.zip"
else echo "need curl or wget" >&2; exit 1; fi
unzip -q -o "$TMP/llncs.zip" -d "$TMP"
for f in llncs.cls splncs04.bst; do
  src="$(find "$TMP" -name "$f" | head -n 1)"
  [ -n "$src" ] || { echo "missing $f in archive" >&2; exit 1; }
  cp "$src" .
done
echo "fetched llncs.cls and splncs04.bst (do not commit them; see .gitignore)"

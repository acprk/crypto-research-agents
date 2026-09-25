#!/usr/bin/env bash
# fetch.sh -- clone public baseline libraries at a pinned ref into a directory you choose.
#
# Usage:
#   references/baselines/fetch.sh --list
#   references/baselines/fetch.sh DEST_DIR [NAME ...]          # default: nothing; name what you need
#   references/baselines/fetch.sh DEST_DIR --all
#   references/baselines/fetch.sh DEST_DIR --dry-run openfhe lattice-estimator
#   PIN_openfhe=<sha-or-tag> references/baselines/fetch.sh DEST_DIR openfhe   # override a pin
#
# Refs: a tag pins a release. HEAD means "no release tag, so pin at fetch time". In both
# cases the resolved commit SHA is appended to DEST_DIR/PINNED.tsv. Copy that SHA into your
# project's baselines/MANIFEST.md. From then on, re-fetch by SHA only.
#
# No source is vendored into this repository (SPEC rule 3). This script only clones.
set -euo pipefail

# name | url | suggested ref (verify with: git ls-remote --tags URL)
CATALOG='
openfhe|https://github.com/openfheorg/openfhe-development.git|v1.5.0
helib|https://github.com/homenc/HElib.git|v2.3.0
seal|https://github.com/microsoft/SEAL.git|v4.1.2
lattigo|https://github.com/tuneinsight/lattigo.git|v6.1.0
tfhe-rs|https://github.com/zama-ai/tfhe-rs.git|HEAD
tfhe|https://github.com/tfhe/tfhe.git|HEAD
concrete|https://github.com/zama-ai/concrete.git|HEAD
fheanor|https://github.com/FeanorTheElf/fheanor.git|HEAD
lattice-estimator|https://github.com/malb/lattice-estimator.git|HEAD
fplll|https://github.com/fplll/fplll.git|5.4.5
fpylll|https://github.com/fplll/fpylll.git|0.6.1
g6k|https://github.com/fplll/g6k.git|HEAD
cryptosmt|https://github.com/kste/cryptosmt.git|HEAD
cadical|https://github.com/arminbiere/cadical.git|HEAD
kissat|https://github.com/arminbiere/kissat.git|HEAD
cryptominisat|https://github.com/msoos/cryptominisat.git|HEAD
highs|https://github.com/ERGO-Code/HiGHS.git|HEAD
mp-spdz|https://github.com/data61/MP-SPDZ.git|HEAD
emp-tool|https://github.com/emp-toolkit/emp-tool.git|HEAD
emp-ot|https://github.com/emp-toolkit/emp-ot.git|HEAD
emp-sh2pc|https://github.com/emp-toolkit/emp-sh2pc.git|HEAD
apsi|https://github.com/microsoft/APSI.git|HEAD
libote|https://github.com/osu-crypto/libOTe.git|HEAD
volepsi|https://github.com/Visa-Research/volepsi.git|HEAD
arkworks-algebra|https://github.com/arkworks-rs/algebra.git|HEAD
gnark|https://github.com/Consensys/gnark.git|HEAD
circom|https://github.com/iden3/circom.git|HEAD
liboqs|https://github.com/open-quantum-safe/liboqs.git|HEAD
pqclean|https://github.com/PQClean/PQClean.git|HEAD
'

list() {
  printf '%-20s %-12s %s\n' NAME REF URL
  echo "$CATALOG" | while IFS='|' read -r n u r; do
    [ -z "$n" ] && continue
    printf '%-20s %-12s %s\n' "$n" "$r" "$u"
  done
}

lookup() {  # name -> "url|ref"
  echo "$CATALOG" | awk -F'|' -v n="$1" '$1==n {print $2"|"$3}'
}

if [ "${1:-}" = "--list" ] || [ "${1:-}" = "-l" ]; then list; exit 0; fi
if [ $# -lt 1 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,15p' "$0"; exit 0
fi

DEST="$1"; shift
DRY=0; NAMES=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --all) while IFS='|' read -r n _u _r; do [ -n "$n" ] && NAMES+=("$n"); done <<< "$CATALOG" ;;
    *) NAMES+=("$a") ;;
  esac
done
if [ ${#NAMES[@]} -eq 0 ]; then echo "no baselines named; see --list" >&2; exit 2; fi

[ "$DRY" = 1 ] || mkdir -p "$DEST"
PINS="$DEST/PINNED.tsv"
if [ "$DRY" = 0 ] && [ ! -f "$PINS" ]; then printf 'name\turl\trequested_ref\tresolved_commit\tfetched_utc\n' > "$PINS"; fi

rc=0
for n in "${NAMES[@]}"; do
  entry="$(lookup "$n")"
  if [ -z "$entry" ]; then echo "unknown baseline: $n (see --list)" >&2; rc=2; continue; fi
  url="${entry%%|*}"; ref="${entry#*|}"
  var="PIN_$(echo "$n" | tr '-' '_')"
  ref="${!var:-$ref}"
  dir="$DEST/$n"
  if [ "$DRY" = 1 ]; then
    echo "would clone $url -> $dir at $ref"; continue
  fi
  if [ -d "$dir/.git" ]; then
    echo "[$n] exists, fetching"; git -C "$dir" fetch --tags --quiet origin
  else
    echo "[$n] cloning $url"; git clone --quiet --filter=blob:none "$url" "$dir"
  fi
  if [ "$ref" != "HEAD" ]; then
    git -C "$dir" -c advice.detachedHead=false checkout --quiet "$ref"
  fi
  git -C "$dir" submodule update --init --recursive --quiet || echo "[$n] warning: submodule update failed" >&2
  sha="$(git -C "$dir" rev-parse HEAD)"
  printf '%s\t%s\t%s\t%s\t%s\n' "$n" "$url" "$ref" "$sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PINS"
  echo "[$n] pinned at $sha"
done
exit $rc

#!/usr/bin/env bash
# compare over the historical profile on a rehearsal host root, in the bundle-only tree.
# usage: host_compare.sh <bundle_only> <root> <dispositions rel> <audit rel> <traces> <label>
set -u
B=$1; ROOT=$2; R=$(cygpath -w "$2"); D=$3; A=$4; TR=$5; L=$6
BIN=$(dirname "$0")
CAND=$(cd "$ROOT" && ls -d reports/candidates/* | head -1)
cd "$B" || exit 2
py -3.10 "$BIN/trace_run.py" "$TR/$L.json" harness.commands.blind_assessment compare --repo-root "$R" \
  --baseline-dir "$R\\baseline" \
  --esr "$R\\docs\\tier4_orchestration_state\\msca_dn\\esr\\msca-dn-2025-original-esr.json" \
  --dispositions "$R\\$D" --candidate "$R\\$CAND" \
  --register "$R\\private\\msca_dn_original\\fidelity_register_as_submitted.json" \
  --audit "$A" --profile harness/profiles/msca_dn_2025_historical.json \
  --out-dir "$R\\comparisons" > "$TR/$L.out" 2>&1
echo "compare exit=$?"
grep -v "^  " "$TR/$L.out" | grep -i "refus\|could not\|not found\|-> \|error" | head -6 | cut -c1-400

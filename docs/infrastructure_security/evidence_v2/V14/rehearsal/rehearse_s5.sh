#!/usr/bin/env bash
# Rehearse runbook §5 and the historical-profile audit of §6 in TREE over a copy of the private root.
# usage: rehearse_s5.sh <tree> <private root copy> <traces dir> <label>
# No model call: assess runs with --fake-converse (boto3.client replaced).
set -u
TREE=$1; ROOT=$(cygpath -w "$2"); TR=$3; L=$4
BIN=$(dirname "$0")
P=harness/profiles/msca_dn_2025_historical.json
DOC=MSCA-DN-2025_part_b_as_submitted
G="$ROOT\\workspaces\\msca_dn_original"
M="$G\\docs\\tier4_orchestration_state\\dev_graph\\imports\\$DOC.json"
RR=(); [ -n "${USE_REPO_ROOT:-}" ] && RR=(--repo-root "$ROOT")
COMMON=("${RR[@]}" --document "$DOC" --graph-root "$G" --profile $P --transport bedrock-converse --no-claims --grounding-scope content_focused --import-manifest "$M")
cd "$TREE" || exit 2
t() { local name=$1; shift; py -3.10 "$BIN/trace_run.py" "$TR/${L}_$name.json" "$@" > "$TR/${L}_$name.out" 2>&1; local rc=$?; echo "$name exit=$rc"; return $rc; }
t s5_01_preflight harness.commands.blind_assessment preflight "${COMMON[@]}" --out-dir "$ROOT\\reports" || exit 1
PF=$(ls "$2"/reports/preflight_*.json | head -1)
t s5_02_assess --fake-converse harness.commands.blind_assessment assess "${COMMON[@]}" --preflight "$(cygpath -w "$PF")" --intake msca-dn-2025-original --assessor-model eu.anthropic.claude-sonnet-4-6 --assessor-version bedrock-converse-eu-north-1@2026-11-12 --out-dir "$ROOT\\reports" || exit 1
RP=$(ls "$2"/reports/blind_*.json 2>/dev/null | head -1)
CAND=$(ls -d "$2"/reports/candidates/* 2>/dev/null | head -1)
echo "report=${RP#$2/} candidate=${CAND#$2/}"
t s5_03_freeze harness.commands.blind_assessment freeze "${RR[@]}" --report "$(cygpath -w "$RP")" --candidate "$(cygpath -w "$CAND")" --profile $P --baseline-dir "$ROOT\\baseline" || exit 1
t s6_01_audit harness.commands.blind_assessment audit "${RR[@]}" --document "$DOC" --graph-root "$G" --profile $P --candidate-provenance "$M" --baseline-dir "$ROOT\\baseline" --out-dir "$ROOT\\audit" || exit 1

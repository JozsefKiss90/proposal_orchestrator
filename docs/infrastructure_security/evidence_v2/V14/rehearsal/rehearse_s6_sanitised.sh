#!/usr/bin/env bash
# Runbook §6 over the committed sanitised artifacts, in TREE, with --repo-root ROOT.
# usage: rehearse_s6_sanitised.sh <tree> <root> <traces> <label>
# Inputs are the committed files at their repository paths under ROOT; no content is printed.
set -u
TREE=$1; R=$(cygpath -w "$2"); TR=$3; L=$4
BIN=$(dirname "$0")
P=harness/profiles/msca_dn_2026_default.json
T4="$R\\docs\\tier4_orchestration_state\\msca_dn"
G="$R\\workspaces\\msca_dn"
BASE="$T4\\baselines\\resolved_fixes_2026-10-06"
CAND="$T4\\audit\\candidates\\MSCA-DN-2025_sanitised_part_b@b51a103520b58ded"
cd "$TREE" || exit 2
t() { local name=$1; shift; py -3.10 "$BIN/trace_run.py" "$TR/${L}_$name.json" "$@" > "$TR/${L}_$name.out" 2>&1; local rc=$?; echo "$name exit=$rc"; }
t s6s_01_audit harness.commands.blind_assessment audit --repo-root "$R" --document MSCA-DN-2025_sanitised_part_b --graph-root "$G" --profile $P --candidate-provenance "$G\\docs\\tier4_orchestration_state\\dev_graph\\imports\\MSCA-DN-2025_sanitised_part_b.resolved_fixes.json" --baseline-dir "$BASE" --out-dir "$R\\out\\audit"
t s6s_02_compare harness.commands.blind_assessment compare --repo-root "$R" --baseline-dir "$BASE" --esr "$T4\\esr\\msca-dn-2025-esr.json" --dispositions "$T4\\esr\\dispositions_f60ae6e0a2a1_approved.json" --candidate "$CAND" --historical-candidate "$T4\audit\candidates\MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db" --register "$R\\docs\\tier3_project_instantiation\\source_materials\\msca_dn\\fidelity_register_resolved_fixes.json" --audit "$T4\\audit\\integrity_242f1afb02c8_0003.json" --audit "$T4\\audit\\integrity_13ad3ad81d7e_0001.json" --profile $P --out-dir "$R\\out\\comparisons"
CMP=$(ls "$2"/out/comparisons/comparison_*.json 2>/dev/null | head -1)
[ -n "$CMP" ] || { echo "no comparison written"; exit 1; }
t s6s_03_review harness.commands.blind_assessment review --repo-root "$R" --comparison "$T4\comparisons\comparison_f60ae6e0a2a1_0003.json" --notes "$T4\\esr\\review_notes_f60ae6e0a2a1_approved.json" --profile $P --out-dir "$R\\out\\reviews"
t s6s_04_diff harness.commands.blind_assessment diff --repo-root "$R" --before "$T4\\comparisons\\comparison_f60ae6e0a2a1_0003.json" --after "$(cygpath -w "$CMP")" --out-dir "$R\\out\\comparisons"

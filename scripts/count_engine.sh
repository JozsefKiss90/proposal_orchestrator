#!/usr/bin/env bash
# count_engine.sh — recompute engine counts from the authoritative source files.
#
# Run from the repo root:  bash scripts/count_engine.sh
#
# These are the single source of truth for engine counts in documentation.
# Do NOT hand-type nodes/gates/agents/skills/predicate counts into docs —
# regenerate them here so they can't drift.
#
# Ground-truth definitions (count-refresh policy, 2026-07-10):
#   nodes                = '- node_id:'      in manifest.compile.yaml
#   gates                = '- gate_id:'      in gate_rules_library.yaml   (CANONICAL)
#   agents               = '- id:'           in agent_catalog.yaml
#   skills               = '- id:'           in skill_catalog.yaml
#   predicate instances  = '- predicate_id:' in gate_rules_library.yaml   (each unique,
#                          one 'function:' each) — this is the "N predicates across M gates" number
#   predicate functions  = distinct 'function:' values in gate_rules_library.yaml
set -euo pipefail

WF=".claude/workflows/system_orchestration"
GRL="$WF/gate_rules_library.yaml"

nodes=$(grep -cE "^[[:space:]]*-[[:space:]]*node_id:" "$WF/manifest.compile.yaml")
gates=$(grep -cE "^[[:space:]]*-[[:space:]]*gate_id:" "$GRL")
agents=$(grep -cE "^[[:space:]]*-[[:space:]]*id:" "$WF/agent_catalog.yaml")
skills=$(grep -cE "^[[:space:]]*-[[:space:]]*id:" "$WF/skill_catalog.yaml")
pred_instances=$(grep -cE "^[[:space:]]*-[[:space:]]*predicate_id:" "$GRL")
pred_functions=$(grep -oE "^[[:space:]]*function:[[:space:]]*[A-Za-z0-9_]+" "$GRL" \
                   | sed 's/.*:[[:space:]]*//' | sort -u | wc -l | tr -d ' ')

# Cross-check: quality_gates.yaml enumerates gates under a different naming scheme
# (gate_01..gate_08 instead of the six phase_0N_gate ids), so its count differs.
qg_gates=$(grep -cE "^[[:space:]]*-[[:space:]]*id:[[:space:]]*gate_" "$WF/quality_gates.yaml" 2>/dev/null || echo "n/a")

printf 'nodes:               %s\n' "$nodes"
printf 'gates:               %s   (gate_rules_library.yaml — canonical)\n' "$gates"
printf 'agents:              %s\n' "$agents"
printf 'skills:              %s\n' "$skills"
printf 'predicate instances: %s   (across %s gates — the "N predicates across M gates" number)\n' "$pred_instances" "$gates"
printf 'predicate functions: %s   (distinct function: values)\n' "$pred_functions"
printf '\nnote: quality_gates.yaml lists %s gate ids under a different naming scheme;\n' "$qg_gates"
printf '      the canonical engine gate count is gate_rules_library.yaml = %s.\n' "$gates"

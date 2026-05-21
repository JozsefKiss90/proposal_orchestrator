"""
DAG runner for the Horizon Europe Proposal Orchestration System.

This package implements the gate predicate execution layer described in
.claude/workflows/system_orchestration/gate_rules_library_plan.md.

Implementation sequence (per gate_rules_library_plan.md §8):
  Step 3  — File predicates          [IMPLEMENTED]
  Step 4  — Gate-pass predicate      [IMPLEMENTED]
  Step 5  — Schema predicates        [IMPLEMENTED]
  Step 6  — Source reference preds   [IMPLEMENTED]
  Step 7  — Coverage predicates      [IMPLEMENTED]
  Step 8  — Cycle predicate          [IMPLEMENTED]
  Step 9  — Timeline predicates      [IMPLEMENTED]
  Step 10 — Runner evaluate_gate     [IMPLEMENTED]
  Step 11 — Semantic dispatch        [IMPLEMENTED]

Constitutional authority: subordinate to CLAUDE.md and
gate_rules_library_plan.md. This package must not redefine gate logic,
phase meanings, tier meanings, or the authority hierarchy.
"""

---
skill_id: constitutional-compliance-check
purpose_summary: >
  Verify that a phase output or deliverable does not violate any prohibition in
  CLAUDE.md, checking for fabricated project facts, fabricated call constraints,
  budget-dependent content before the budget gate, grant annex schema usage, and
  other constitutional violations.
used_by_agents:
  - compliance_validator
  - call_analyzer
  - concept_refiner
  - proposal_writer
  - revision_integrator
  - budget_gate_validator
reads_from:
  - CLAUDE.md
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier5_deliverables/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Must check against CLAUDE.md Section 13 prohibitions as a minimum"
  - "Constitutional violations must be flagged; they must not be silently resolved"
  - "CLAUDE.md governs this skill; this skill does not govern CLAUDE.md"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->

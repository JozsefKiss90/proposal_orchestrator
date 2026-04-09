---
skill_id: wp-dependency-analysis
purpose_summary: >
  Analyse inter-WP and inter-task dependencies, producing a directed acyclic graph
  representation that identifies the critical path, dependency cycles, and dependencies
  incompatible with project duration.
used_by_agents:
  - dependency_mapper
  - wp_designer
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
constitutional_constraints:
  - "Must flag dependency cycles; must not silently remove them"
  - "Critical path must be traceable to the dependency map"
  - "Must not declare the map complete with undeclared dependencies"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->

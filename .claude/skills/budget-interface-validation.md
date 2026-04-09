---
skill_id: budget-interface-validation
purpose_summary: >
  Validate budget request conformance to the interface contract before submission,
  and validate budget response conformance and structural consistency upon receipt,
  producing validation artifacts.
used_by_agents:
  - budget_interface_coordinator
  - budget_gate_validator
reads_from:
  - docs/integrations/lump_sum_budget_planner/interface_contract.json
  - docs/integrations/lump_sum_budget_planner/request_templates/
  - docs/integrations/lump_sum_budget_planner/received/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/integrations/lump_sum_budget_planner/validation/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
constitutional_constraints:
  - "Must not generate or estimate budget figures"
  - "Must not accept a response that does not conform to the interface contract"
  - "Must not declare the budget gate passed if blocking inconsistencies exist"
  - "Must not treat absent response as a non-failing state"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->

---
id: BUDGET-mobility_allowance
title: Budget line — mobility allowance
node_type: budget
evidence_strength: source_grounded
tier: tier3
aliases:
- BUDGET-mobility_allowance
- mobility_allowance
line_id: mobility_allowance
host_dependent: false
monthly_rate_eur: 710
months: 24
amount_eur: 17040.0
status: Confirmed
formula: confirmed_months x published_rates x host_country_coefficient
host_country: HU
provenance_detail: 'unit_cost deterministic derivation (CLAUDE.md §8.1 / C1), byte-equal replay checked; source: docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json'
---

MSCA-PF unit-cost budget line **mobility_allowance** (host-independent). Derived deterministically as `confirmed_months x published_rates x host_country_coefficient` over the confirmed 24-month European Fellowship at host country HU (coefficient 78.7%). Amount: €17040.0.

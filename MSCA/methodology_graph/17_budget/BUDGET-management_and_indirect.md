---
id: BUDGET-management_and_indirect
title: Budget line — management and indirect
node_type: budget
evidence_strength: source_grounded
tier: tier3
aliases:
- BUDGET-management_and_indirect
- management_and_indirect
line_id: management_and_indirect
host_dependent: false
monthly_rate_eur: 650
months: 24
amount_eur: 15600.0
status: Confirmed
formula: confirmed_months x published_rates x host_country_coefficient
host_country: HU
provenance_detail: 'unit_cost deterministic derivation (CLAUDE.md §8.1 / C1), byte-equal replay checked; source: docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json'
---

MSCA-PF unit-cost budget line **management_and_indirect** (host-independent). Derived deterministically as `confirmed_months x published_rates x host_country_coefficient` over the confirmed 24-month European Fellowship at host country HU (coefficient 78.7%). Amount: €15600.0.

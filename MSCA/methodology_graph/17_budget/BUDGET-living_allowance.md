---
id: BUDGET-living_allowance
title: Budget line — living allowance
node_type: budget
evidence_strength: source_grounded
tier: tier3
aliases:
- BUDGET-living_allowance
- living_allowance
line_id: living_allowance
host_dependent: true
base_monthly_rate_eur: 6350
coefficient_percent: 78.7
monthly_rate_eur: 4997.45
months: 24
amount_eur: 119938.8
status: Confirmed
formula: confirmed_months x published_rates x host_country_coefficient
host_country: HU
provenance_detail: 'unit_cost deterministic derivation (CLAUDE.md §8.1 / C1), byte-equal replay checked; source: docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json'
---

MSCA-PF unit-cost budget line **living_allowance** (host-dependent). Derived deterministically as `confirmed_months x published_rates x host_country_coefficient` over the confirmed 24-month European Fellowship at host country HU (coefficient 78.7%). Amount: €119938.8.

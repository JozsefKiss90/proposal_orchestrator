---
id: RISK-08
title: Overconfidence - collapsing to one parameter set instead of an honest range
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-08
description: Calibrating AquaCrop to a single overconfident parameter set would break the uncertainty chain and produce falsely confident decisions.
category: model_complexity
probability: medium
impact: high
affected_objectives:
- OBJ-2
affected_work_packages:
- WP2
mitigation: Uncertainty-aware AquaCrop calibration that retains parameter uncertainty (the fellow-attributed method, doi:10.1016/j.envsoft.2022.105556).
contingency: Ensemble over plausible parameter sets and propagate their spread into the decision if a full posterior is intractable.
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R8 (METH-RISK-002)
- Model Complexity Risks (METH-RISK-005)
- Uncertainty Aware AquaCrop Calibration (METH-DEC-002)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

Calibrating AquaCrop to a single overconfident parameter set would break the uncertainty chain and produce falsely confident decisions.

## Related

**Grounded in methodology nodes:** Risk Register R8 (METH-RISK-002), [[Model Complexity Risks]], [[Uncertainty Aware AquaCrop Calibration]]

**Related architecture nodes:** [[OBJ-2]], [[WP2]]

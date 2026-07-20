---
id: RISK-06
title: Reported uncertainty is not well calibrated
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-06
description: The framework's headline commitment - honest uncertainty - fails if e.g. 90% prediction intervals do not contain the truth about 90% of the time.
category: validation
probability: medium
impact: high
affected_objectives:
- OBJ-1
- OBJ-2
- OBJ-3
affected_work_packages:
- WP2
- WP3
mitigation: Build uncertainty-calibration metrics into the validation protocol (RQ5); use uncertainty-aware calibration end to end.
contingency: Recalibrate posteriors post-hoc; report calibration honestly and narrow claims to the calibrated regime.
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R6 (METH-RISK-002)
- Validation Risks (METH-RISK-003)
- Uncertainty Chain (METH-CORE-004)
- Uncertainty Aware AquaCrop Calibration (METH-DEC-002)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

The framework's headline commitment - honest uncertainty - fails if e.g. 90% prediction intervals do not contain the truth about 90% of the time.

## Related

**Grounded in methodology nodes:** Risk Register R6 (METH-RISK-002), [[Validation Risks]], [[Uncertainty Chain]], [[Uncertainty Aware AquaCrop Calibration]]

**Related architecture nodes:** [[OBJ-1]], [[OBJ-2]], [[OBJ-3]], [[WP2]], [[WP3]]

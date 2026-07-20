---
id: RISK-09
title: Sensor calibration/integration complexity
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-09
description: Integrating and calibrating heterogeneous sensors (radar, optical, soil, weather) adds complexity that can degrade signal quality.
category: model_complexity
probability: medium
impact: medium
affected_objectives:
- OBJ-1
- OBJ-3
affected_work_packages:
- WP1
- WP3
mitigation: QC pipeline; sensor comparison in the validation layer.
contingency: Reduce the sensor set to the reliably calibrated core; document excluded sensors as extension points.
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R9 (METH-RISK-002)
- Model Complexity Risks (METH-RISK-005)
- Ground Sensing Layer (METH-INFRA-003)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

Integrating and calibrating heterogeneous sensors (radar, optical, soil, weather) adds complexity that can degrade signal quality.

## Related

**Grounded in methodology nodes:** Risk Register R9 (METH-RISK-002), [[Model Complexity Risks]], [[Ground Sensing Layer]]

**Related architecture nodes:** [[OBJ-1]], [[OBJ-3]], [[WP1]], [[WP3]]

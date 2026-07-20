---
id: RISK-03
title: Cloud limits optical; dense vegetation reduces SAR retrieval accuracy
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-03
description: Cloud cover limits Sentinel-2 optical availability, while dense vegetation reduces Sentinel-1 SAR retrieval accuracy - the two sensors' complementary weaknesses.
category: data_access
probability: high
impact: medium
affected_objectives:
- OBJ-1
affected_work_packages:
- WP1
mitigation: Lean on Sentinel-1 SAR through cloud; cloud masking; vegetation-aware retrieval.
contingency: Weight the fusion toward the more reliable sensor per condition; gap-fill optical with radar-informed estimates.
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R3 (METH-RISK-002)
- Data Access Risks (METH-RISK-004)
- Earth Observation Layer (METH-INFRA-002)
- SAR (METH-TERM-026)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

Cloud cover limits Sentinel-2 optical availability, while dense vegetation reduces Sentinel-1 SAR retrieval accuracy - the two sensors' complementary weaknesses.

## Related

**Grounded in methodology nodes:** Risk Register R3 (METH-RISK-002), [[Data Access Risks]], [[Earth Observation Layer]], [[SAR]]

**Related architecture nodes:** [[OBJ-1]], [[WP1]]

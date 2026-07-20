---
id: RISK-01
title: PlanetScope cost/access not secured, weakening high-resolution coverage of small plots
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-01
description: High-resolution PlanetScope imagery, valuable for small horticultural plots, may not be secured due to cost/access constraints, weakening coverage where the sub-pixel problem bites hardest.
category: data_access
probability: medium
impact: high
affected_objectives:
- OBJ-1
affected_work_packages:
- WP1
mitigation: Treat PlanetScope as an optional enhancement; build the core on open Copernicus Sentinel-1 + Sentinel-2 data; resolve access early (RQ8).
contingency: Deliver the diagnosis on Sentinel-1 + Sentinel-2 only, documenting the resolution trade-off for small plots.
risk_owner: HOST
source_vault_nodes:
- Risk Register R1 (METH-RISK-002)
- Data Access Risks (METH-RISK-004)
- PlanetScope Usage Gap (METH-SOTA-003)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

High-resolution PlanetScope imagery, valuable for small horticultural plots, may not be secured due to cost/access constraints, weakening coverage where the sub-pixel problem bites hardest.

## Related

**Grounded in methodology nodes:** Risk Register R1 (METH-RISK-002), [[Data Access Risks]], [[PlanetScope Usage Gap]]

**Related architecture nodes:** [[OBJ-1]], [[WP1]]

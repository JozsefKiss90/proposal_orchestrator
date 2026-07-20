---
id: RISK-02
title: Spatial/temporal resolution harmonisation across heterogeneous sources fails or degrades fusion
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-02
description: Reconciling the differing spatial and temporal resolutions of radar, optical, soil and weather sources may fail or degrade the fusion quality.
category: data_access
probability: high
impact: medium
affected_objectives:
- OBJ-1
affected_work_packages:
- WP1
mitigation: Geospatial/time-series data platform with QC; temporal compositing; explicit resolution handling.
contingency: Restrict fusion to the sources that harmonise reliably; treat problematic sources as covariates at their native resolution.
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R2 (METH-RISK-002)
- Data Access Risks (METH-RISK-004)
- Geospatial and Time Series Data Platform (METH-INFRA-005)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

Reconciling the differing spatial and temporal resolutions of radar, optical, soil and weather sources may fail or degrade the fusion quality.

## Related

**Grounded in methodology nodes:** Risk Register R2 (METH-RISK-002), [[Data Access Risks]], [[Geospatial and Time Series Data Platform]]

**Related architecture nodes:** [[OBJ-1]], [[WP1]]

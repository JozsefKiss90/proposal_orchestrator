---
id: OBJ-1
title: Probabilistic multi-sensor diagnosis of the latent field state
node_type: objective
evidence_strength: source_grounded
tier: tier3
aliases:
- OBJ-1
description: Develop and calibrate a probabilistic diagnostic method that fuses multi-source Earth observation (Sentinel-1 SAR, Sentinel-2 optical, secured PlanetScope), meteorological data (ERA5 reanalysis) and field observations into estimates of the latent field state (root-zone soil moisture and crop water status, RQ3), returning full posteriors rather than point estimates. The project adopts Route B, the homogeneous-patch proxy (RQ2), within a methodological architecture that also defines the rigorous one-step Route A (direct probabilistic fusion) as an alternative.
measurable_target: A calibrated diagnostic model that outputs the target field-state variables (root-zone soil moisture and crop water status) with explicit, honest uncertainty (posterior/prediction intervals). The verifiable target is uncertainty-calibrated field-state estimation, not a fabricated accuracy percentage.
target_month: 12
pillar: Diagnostic branch
responsible_partner: FELLOW
contributing_partners:
- SUPERVISOR
- HOST
source_vault_nodes:
- Diagnostic Branch (METH-CORE-002)
- Route A - Direct Probabilistic Fusion (METH-ROUTE-001)
- Route B - Homogeneous Patch Proxy (METH-ROUTE-002)
- Latent Field State (METH-TERM-010)
- Uncertainty Chain (METH-CORE-004)
resolved_decisions:
- RQ2 = Route B (homogeneous patch proxy)
- RQ3 = root-zone soil moisture + crop water status
- RQ8 = PlanetScope access secured
provenance_detail: source_grounded (methodology) + operator_confirmed (RQ2 route, RQ3 target state, RQ8 PlanetScope)
---

Develop and calibrate a probabilistic diagnostic method that fuses multi-source Earth observation (Sentinel-1 SAR, Sentinel-2 optical, secured PlanetScope), meteorological data (ERA5 reanalysis) and field observations into estimates of the latent field state (root-zone soil moisture and crop water status, RQ3), returning full posteriors rather than point estimates. The project adopts Route B, the homogeneous-patch proxy (RQ2), within a methodological architecture that also defines the rigorous one-step Route A (direct probabilistic fusion) as an alternative.

## Related

**Grounded in methodology nodes:** [[Diagnostic Branch]], [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]], [[Latent Field State]], [[Uncertainty Chain]]

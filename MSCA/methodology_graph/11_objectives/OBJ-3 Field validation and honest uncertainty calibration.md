---
id: OBJ-3
title: Field validation and honest uncertainty calibration
node_type: objective
evidence_strength: source_grounded
tier: tier3
aliases:
- OBJ-3
description: 'Design and execute a validation protocol on Hungarian tomato farms (accessed via AgroVIR) establishing that the diagnosis and the decision recommendations are credible: collect non-destructive physiological ground truth, assess whether the reported uncertainty is well calibrated, and test that Route B''s chosen homogeneous patch genuinely covaries with the target crop.'
measurable_target: 'A validation protocol with defined ground-truth measurements (RQ4: chlorophyll fluorescence, stomatal conductance, canopy/leaf temperature, spectral reflectance), an uncertainty-calibration criterion (RQ5: 90% prediction intervals contain the truth about 90% of the time), a pilot-success criterion (RQ7: the RQ5 calibration target is met on the validation set), and a patch-covariation test (RQ9: a co-located seasonal campaign measuring the target crop and the proxy patch simultaneously, demonstrating statistical covariation). No validation numbers are asserted beyond these operator-confirmed criteria.'
target_month: 20
pillar: Validation
responsible_partner: FELLOW
contributing_partners:
- HOST
- SUPERVISOR
source_vault_nodes:
- Validation and Field Trial Layer (METH-INFRA-009)
- Validation Risks (METH-RISK-003)
- Control Stand Variant (METH-ROUTE-003)
- Ten Research Questions (METH-RQ-001)
resolved_decisions:
- RQ4 = non-destructive physiological ground truth
- RQ5 = 90% prediction-interval coverage
- RQ7 = pilot success = RQ5 target met on the validation set
- RQ9 = co-located seasonal covariation campaign
coherence_note:
  validation_status: Inferred
  reasoning: RQ3 keeps root-zone soil moisture within the target field state, but the RQ4 non-destructive physiological measures (chlorophyll fluorescence, stomatal conductance, canopy/leaf temperature, spectral reflectance) validate the crop-water-status component directly and the root-zone soil-moisture component only indirectly. This is recorded as a coherence caveat, not a gap; no soil-moisture sensor plan is fabricated here.
provenance_detail: source_grounded (methodology) + operator_confirmed (RQ4/RQ5/RQ7/RQ9)
---

Design and execute a validation protocol on Hungarian tomato farms (accessed via AgroVIR) establishing that the diagnosis and the decision recommendations are credible: collect non-destructive physiological ground truth, assess whether the reported uncertainty is well calibrated, and test that Route B's chosen homogeneous patch genuinely covaries with the target crop.

## Related

**Grounded in methodology nodes:** [[Validation and Field Trial Layer]], [[Validation Risks]], [[Control Stand Variant]], [[Ten Research Questions]]

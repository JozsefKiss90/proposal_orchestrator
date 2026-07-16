---
id: METH-RISK-002
title: "Risk Register"
node_type: risk
status: draft
version: 0.1
created: 2026-06-19
updated: 2026-06-19
domain:
  - crop_water_stress
  - irrigation_decision_support
project_scope:
  - methodology
  - proposal_development
source_refs:
  - "[[Source - Literature Review]]"
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "litreview Report A §3.4, Claims & Evidence Table, Fig.6, key limitations"
  - "methodology_idea.txt (Route A burden; covariation; overconfidence)"
  - "prompt.txt §3, §4, §5, §8"
  - "doi:10.1016/j.envsoft.2022.105556"
evidence_strength: synthesis
confidence: medium
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Methodology SWOT Matrix]]"
downstream_nodes:
  - "[[Validation Risks]]"
  - "[[Data Access Risks]]"
  - "[[Model Complexity Risks]]"
  - "[[Operationalisation Risks]]"
related_nodes:
  - "[[Validation Risks]]"
  - "[[Data Access Risks]]"
  - "[[Model Complexity Risks]]"
  - "[[Operationalisation Risks]]"
  - "[[Methodology SWOT Matrix]]"
key_terms:
  - "[[Uncertainty Propagation]]"
  - "[[Data Fusion]]"
risks: []
open_questions:
  - "[[Ten Research Questions]]"
validation_needs:
  - "Re-score likelihood/impact once data access, partner and TRL decisions are made"
aliases:
  - "Risk Table"
tags:
  - methodology-graph
  - risk
---

# Risk Register

A consolidated table of the principal methodological risks, each with category, qualitative likelihood and impact, a mitigation, the nodes it touches, and its evidence basis.

This register is a *(proposal synthesis)*: the underlying hazards are source-grounded, but the likelihood/impact judgements are qualitative analyst estimates (not measured), so they carry `confidence: medium` and should be re-scored as project decisions firm up. It groups into four themes detailed in [[Validation Risks]], [[Data Access Risks]], [[Model Complexity Risks]] and [[Operationalisation Risks]], and rolls up from the [[Methodology SWOT Matrix]].

> [!note] How to read likelihood/impact
> Likelihood and Impact are coarse High/Medium/Low estimates for proposal triage, not quantitative probabilities. They are the synthesis layer; the hazards themselves trace to the cited sources.

## Register

| # | Risk | Category | Likelihood | Impact | Mitigation | Linked nodes | Evidence |
|---|---|---|---|---|---|---|---|
| R1 | PlanetScope cost/access not secured, weakening high-resolution coverage of small plots | Data access | Medium | High | Treat PlanetScope as optional enhancement; build core on S1+S2; resolve access early (RQ8) | [[Data Access Risks]], [[PlanetScope Usage Gap]], [[Earth Observation Layer]] | litreview Report A key limitations; prompt.txt §3 |
| R2 | Spatial/temporal resolution harmonisation across heterogeneous sources fails or degrades fusion | Data access | High | Medium | Geospatial/time-series platform with QC; temporal compositing; explicit resolution handling | [[Data Access Risks]], [[Geospatial and Time Series Data Platform]] | litreview Report A key limitations |
| R3 | Cloud limits optical; dense vegetation reduces SAR retrieval accuracy | Data access | High | Medium | Lean on S1 SAR through cloud; cloud masking; vegetation-aware retrieval | [[Data Access Risks]], [[Earth Observation Layer]] | litreview Report A §3.4 (cloud); Mkhwenkwana 2025 (SAR) |
| R4 | Few large-scale validation efforts with dense ground-truth; validation under-powered | Validation | Medium | High | Plan field trials + dense ground truth (RQ4); cost-effective sensor network | [[Validation Risks]], [[Validation and Field Trial Layer]] | litreview Report A key limitations; Open Research Questions |
| R5 | Route B patch/control-stand covariation not actually proven | Validation | Medium | High | Pre-register covariation test; measure (control stand) rather than assume (RQ9) | [[Validation Risks]], [[Route B - Homogeneous Patch Proxy]], [[Control Stand Variant]] | methodology_idea.txt; prompt.txt §4 |
| R6 | Uncertainty not well calibrated (e.g. 90% PIs do not contain truth ~90%) | Validation | Medium | High | Calibration metrics in validation protocol (RQ5); uncertainty-aware calibration | [[Validation Risks]], [[Uncertainty Chain]] | prompt.txt §1; doi:10.1016/j.envsoft.2022.105556 |
| R7 | Route A too demanding (expertise / validation data / compute) | Model complexity | Medium | High | Keep Route B as credible fallback; staged build; provision compute runtime | [[Model Complexity Risks]], [[Route A - Direct Probabilistic Fusion]] | prompt.txt §3; methodology_idea.txt |
| R8 | Overconfidence — collapsing to one parameter set instead of an honest range | Model complexity | Medium | High | Uncertainty-aware AquaCrop calibration (retain parameter uncertainty) | [[Model Complexity Risks]], [[Uncertainty Aware AquaCrop Calibration]] | methodology_idea.txt; doi:10.1016/j.envsoft.2022.105556 |
| R9 | Sensor calibration/integration complexity | Model complexity | Medium | Medium | QC pipeline; sensor comparison in validation layer | [[Model Complexity Risks]], [[Ground Sensing Layer]] | litreview Report A §3.4 |
| R10 | Lack of operational frameworks unifying all sensors at scale; prototype does not reach pilot | Operationalisation | Medium | Medium | Frame MVP as standalone research demonstrator; partners assist, not own (RQ10) | [[Operationalisation Risks]], [[Operational Decision Support Gap]], [[Web MVP and User Interface Layer]] | litreview Report A (Duan 2025); prompt.txt §8 |

> [!warning] Unconfirmed assumptions behind several rows
> R1 (PlanetScope access), R10 (TRL target), and the partner roles underlying R10 are not firmly established in the sources (see [[Ten Research Questions]] RQ8, RQ10). Do not treat these scores as settled.

## Links and relationships
The register expands the [[Methodology SWOT Matrix]] threats and weaknesses into actionable items. Each theme has a dedicated node: [[Data Access Risks]] (R1-R3), [[Validation Risks]] (R4-R6), [[Model Complexity Risks]] (R7-R9) and [[Operationalisation Risks]] (R10). Open items map to the [[Ten Research Questions]].

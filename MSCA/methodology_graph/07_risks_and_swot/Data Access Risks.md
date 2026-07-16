---
id: METH-RISK-004
title: "Data Access Risks"
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
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "litreview Report A key limitations (sparse PlanetScope due to cost/access)"
  - "litreview Report A §3.4 (cloud limits optical; dense vegetation reduces SAR)"
  - "litreview Report A key limitations (harmonizing spatial/temporal resolutions)"
  - "prompt.txt §3 (S1/S2/PlanetScope inputs); §8 (EO infrastructure)"
evidence_strength: source_grounded
confidence: medium
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Risk Register]]"
downstream_nodes: []
related_nodes:
  - "[[PlanetScope Usage Gap]]"
  - "[[Earth Observation Layer]]"
  - "[[Risk Register]]"
  - "[[Ten Research Questions]]"
key_terms:
  - "[[PlanetScope]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
risks: []
open_questions:
  - "RQ8 — is PlanetScope access secured or only optional?"
  - "[[Ten Research Questions]]"
validation_needs:
  - "Confirm PlanetScope access status; specify resolution-harmonisation and cloud/SAR handling"
aliases: []
tags:
  - methodology-graph
  - risk
---

# Data Access Risks

Risks that the required Earth-observation inputs are unavailable, too costly, or hard to reconcile: PlanetScope cost/access, cloud-limited optical and vegetation-limited SAR, and resolution harmonisation.

These risks are **source-grounded** in the literature review's key limitations and methodological-advances section, and in the input list of the analyst synthesis (prompt.txt §3, §8). They feed the [[Risk Register]] and are the risk view of the [[Earth Observation Layer]].

## The risks

### 1. PlanetScope cost / access
The review repeatedly flags **sparse use of PlanetScope alongside other satellites due to cost/data-access issues** (litreview Report A key limitations). PlanetScope is the high-resolution input most valuable for small plots, yet its access is uncertain. This is the binding question **RQ8** (access secured vs optional) and is elaborated in the [[PlanetScope Usage Gap]]; the [[PlanetScope]] term carries the same caveat.

### 2. Cloud limits optical; dense vegetation reduces SAR
Two physical constraints recur: **cloud cover limits optical data availability**, and **dense vegetation reduces SAR retrieval accuracy** (litreview Report A §3.4; the latter rated Moderate, Mkhwenkwana 2025). Together they can starve the diagnostic of timely signal. Mitigation leans on S1 [[SAR]] for all-weather coverage and on cloud masking in the [[Earth Observation Layer]], but neither fully removes the constraint.

### 3. Harmonising spatial/temporal resolutions
A persistent challenge is **harmonising spatial/temporal resolutions across disparate datasets** ([[Sentinel 1]], [[Sentinel 2]], [[PlanetScope]], meteo, soil). The review's Open Research Questions tie improved fusion algorithms directly to overcoming differing spatial/temporal resolutions (litreview Report A). Poor harmonisation degrades any fusion model.

> [!warning] PlanetScope access is unconfirmed
> Whether PlanetScope access is secured or merely optional is **not established in the sources** (§B.6, RQ8). `confidence: medium`, `maturity: project_decision_needed`. The core pipeline should be buildable on Sentinel-1 + Sentinel-2 so PlanetScope is an enhancement, not a single point of failure. See [[Ten Research Questions]].

## Mitigations (proposal-level)
- Resolve PlanetScope access early; design the core on free Copernicus [[Sentinel 1]] + [[Sentinel 2]] (RQ8).
- Use S1 SAR through cloud, cloud masking and temporal compositing in the [[Earth Observation Layer]].
- Build explicit resolution-harmonisation and QC into the data platform.

## Links and relationships
This node rolls up to the [[Risk Register]] and the [[Methodology SWOT Matrix]] threats (PlanetScope cost/access; data harmonisation; dense-veg SAR; cloud). It connects to the [[PlanetScope Usage Gap]] and the [[Earth Observation Layer]], and its open item maps to RQ8 in the [[Ten Research Questions]].

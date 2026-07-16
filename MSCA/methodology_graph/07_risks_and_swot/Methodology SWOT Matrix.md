---
id: METH-RISK-001
title: "Methodology SWOT Matrix"
node_type: swot
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
  - "methodology_idea.txt (full narrative)"
  - "prompt.txt §1, §3, §4, §5, §6, §8, §9"
  - "litreview Report A §3.4, Claims & Evidence Table, Fig.6"
  - "litreview Report B (probabilistic novelty gap)"
  - "doi:10.1016/j.envsoft.2022.105556"
evidence_strength: synthesis
confidence: medium
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes:
  - "[[Risk Register]]"
related_nodes:
  - "[[Risk Register]]"
  - "[[Validation Risks]]"
  - "[[Data Access Risks]]"
  - "[[Model Complexity Risks]]"
  - "[[Operationalisation Risks]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Operational Decision Support Gap]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Uncertainty Propagation]]"
risks:
  - "[[Validation Risks]]"
  - "[[Data Access Risks]]"
  - "[[Model Complexity Risks]]"
  - "[[Operationalisation Risks]]"
open_questions:
  - "[[Ten Research Questions]]"
validation_needs:
  - "Confirm which threats are binding once partner, data-access and TRL decisions are made"
aliases:
  - "SWOT"
  - "SWOT Analysis"
tags:
  - methodology-graph
  - swot
---

# Methodology SWOT Matrix

A structured Strengths-Weaknesses-Opportunities-Threats reading of the proposed uncertainty-aware, two-route, end-to-end crop-water-stress monitoring and irrigation decision-support methodology.

This node is a *(proposal synthesis)*: it recombines source material into a strategic frame. Each cell is grounded in the [[Source - Methodology Idea]], the [[Source - Methodology Synthesis Prompt]] and the [[Source - Literature Review]]; the SWOT *layout* itself is the synthesis. It sits beneath the [[Methodology Graph - Meta Node]] and feeds the [[Risk Register]] and the four risk-theme nodes.

## SWOT Matrix

| | Helpful | Harmful |
|---|---|---|
| **Internal** | **Strengths** | **Weaknesses** |
| **External** | **Opportunities** | **Threats** |

### Strengths
- **Uncertainty honest end-to-end.** The "red thread" is that every output reports not just a state but how sure we are, and that uncertainty travels into the decision (idea narrative; prompt.txt §1). Captured by the [[Uncertainty Chain]] and [[Uncertainty Propagation]].
- **Defendable novelty.** Report B concludes multimodal fusion is mature but *probabilistic* row-crop drought/irrigation frameworks remain underdeveloped, so the framework can be genuinely novel (litreview Report B; [[Probabilistic Fusion Novelty Claim]]).
- **Profit-based objective.** Optimising expected profit net of water/input costs rather than yield moves from a "monitoring dashboard" to a tool that can pay for itself (prompt.txt §6; [[Profit Based Objective Function]]).
- **Two-route flexibility.** [[Route A - Direct Probabilistic Fusion]] (rigorous) plus [[Route B - Homogeneous Patch Proxy]] (lighter fallback) give ambition with a credible fallback (prompt.txt §10).
- **AquaCrop on its home ground.** AquaCrop is strong precisely where water is limiting and irrigation is the lever (idea narrative; [[AquaCrop Decision Interface]]).

### Weaknesses
- **Route A modelling burden.** The "hardcore" probabilistic-ML route is demanding in expertise, validation data and compute (prompt.txt §3; [[Model Complexity Risks]]).
- **Route B rests on an assumption.** The patch must genuinely covary with the target crop; that covariation must be proven, not assumed (idea narrative; prompt.txt §4; [[Validation Risks]]).
- **Sub-pixel difficulty.** Small horticultural plots are sub-pixel at today's resolutions, the root technical obstacle ([[Sub Pixel Problem]]).
- **Heavy validation-data need.** Honest uncertainty and decision performance need dense ground truth, which is expensive (litreview Report A limitations).

### Opportunities
- **Ecosystem co-benefit.** Route B leans on keeping natural/semi-natural patches, fitting ecosystem continuity and extensive agriculture, and scales there once horticulture leads (idea narrative).
- **Fill the operational gap.** Report A's Fig.6 shows Real-Time Decision Support × PlanetScope as a GAP, and a Moderate-evidence lack of operational frameworks unifying all sensors (Duan 2025); the project targets exactly this ([[Operational Decision Support Gap]]).
- **MSCA fit.** Presenting the MVP as a standalone research demonstrator suits an MSCA-style proposal (prompt.txt §8).
- **Scales to extensive agriculture.** Beyond horticulture, the same patch/proxy approach extends to extensive agriculture and semi-natural landscapes once horticulture has shown the way, broadening potential impact (idea narrative).

### Threats
- **PlanetScope cost/access.** Sparse PlanetScope use is driven by cost/access (litreview Report A; [[Data Access Risks]]).
- **Data harmonisation.** Differing spatial/temporal resolutions are hard to reconcile (litreview Report A limitations).
- **Sensor physics.** Dense vegetation reduces SAR retrieval (Mkhwenkwana 2025) and cloud limits optical (litreview Report A §3.4).
- **Overconfidence.** If uncertainty is mishandled, an overconfident parameter set undermines the whole premise (idea narrative; doi:10.1016/j.envsoft.2022.105556).
- **Operationalisation at scale.** Moving from prototype to scaled operation is unproven ([[Operationalisation Risks]]).

> [!warning] Unconfirmed inputs to this SWOT
> Several strategic items depend on items not firmly in the sources: the first crop (tomato is tentative), PlanetScope access, partner commitments and the TRL target. See [[Ten Research Questions]] and the per-theme risk nodes. Treat threat severity as provisional.

## Links and relationships
This matrix is operationalised in the [[Risk Register]] and elaborated in [[Validation Risks]], [[Data Access Risks]], [[Model Complexity Risks]] and [[Operationalisation Risks]]. Strengths and weaknesses trace to [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]] and the [[Probabilistic Fusion Novelty Claim]]; opportunities to the [[Operational Decision Support Gap]].

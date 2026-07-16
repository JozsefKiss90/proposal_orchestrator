---
id: METH-PART-003
title: "PI Role"
node_type: partner
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
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "methodology_idea.txt (first-person design narrative; 'a method I developed a few years ago (doi: 10.1016/j.envsoft.2022.105556)')"
  - "BUILD_BRIEF §B.5 (PI prior method, doi:10.1016/j.envsoft.2022.105556)"
  - "BUILD_BRIEF §B.6 (PI identity inferred; name unconfirmed)"
evidence_strength: inference
confidence: medium
maturity: project_decision_needed
owner_role: "[[PI Role]]"
stakeholders:
  - "[[Methodology Contributor Role]]"
upstream_nodes:
  - "[[Partner Roles Overview]]"
downstream_nodes: []
related_nodes:
  - "[[Uncertainty Aware AquaCrop Calibration]]"
  - "[[Methodology Contributor Role]]"
  - "[[Source - Methodology Idea]]"
  - "[[Partner Roles Overview]]"
key_terms: []
risks: []
open_questions:
  - "What is the PI's name and host institution?"
  - "Is the PI the same person as the [[Methodology Contributor Role]] ('colleague')?"
validation_needs:
  - "Confirm PI identity and affiliation before proposal submission."
aliases:
  - "Principal Investigator"
  - "PI"
tags:
  - methodology-graph
  - partner
---

# PI Role

The principal investigator who **authored the design narrative** and leads the methodology — identified by role from the sources, but **not named** in any of them.

> [!note] Inference, not a named fact
> The PI is **inferred** from two source signals: (1) [[Source - Methodology Idea]] is written in the first person as a design the author is "putting down for you to build on," and (2) the author claims the uncertainty-aware calibration method as their own — *"a method I developed a few years ago (doi: 10.1016/j.envsoft.2022.105556)"*. The **DOI is source-grounded** (PI-stated); the **person's name and institution are unconfirmed** (BUILD_BRIEF §B.6). Hence `evidence_strength: inference`, `confidence: medium`.

## What the role covers (from the sources)

- **Owns the methodological design.** The whole two-branch architecture — diagnostic state estimation plus prognostic counterfactuals, tied by "one chain that carries its uncertainty from end to end" — is laid out as the PI's design in [[Source - Methodology Idea]].
- **Developer of the calibration method.** The PI authored the uncertainty-aware calibration approach behind [[Uncertainty Aware AquaCrop Calibration]] (doi:10.1016/j.envsoft.2022.105556), described as a way to "keep an honest range rather than one overconfident parameter set." This is the PI's most concrete, verifiable contribution.
- **Sets the scientific framing and ambition.** The PI frames the novelty cautiously — *"nobody has put exactly these pieces together quite like this … if we defend it carefully"* — which positions the PI as the scientific lead responsible for the defendable edge.

## Relationship to the contributor

The narrative refers to "your colleague" (in the analyst's framing, [[Source - Methodology Synthesis Prompt]] §2–§4) as the source of the sub-pixel concern and the two-route idea. **Whether the PI and the [[Methodology Contributor Role]] are the same person, or two collaborators, is open** *(inference / open question)*. The first-person narrative and the third-person "colleague" references could be the same author summarising a discussion, or two distinct people. This is recorded as an open question, not resolved.

## Source grounding

- Authorship and design ownership: [[Source - Methodology Idea]] (first-person narrative).
- Calibration method (DOI): BUILD_BRIEF §B.5; cited in [[Uncertainty Aware AquaCrop Calibration]].
- Unconfirmed identity: BUILD_BRIEF §B.6.

## Links & relationships

This node sits under [[Partner Roles Overview]], anchors [[Uncertainty Aware AquaCrop Calibration]] as `owner_role`, and is paired with [[Methodology Contributor Role]]. The primary evidence is [[Source - Methodology Idea]].

## Open questions

1. PI name and host institution (unconfirmed).
2. PI vs. contributor — same person or two collaborators?

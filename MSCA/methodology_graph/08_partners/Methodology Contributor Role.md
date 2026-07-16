---
id: METH-PART-004
title: "Methodology Contributor Role"
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
  - "prompt.txt §2 ('Your colleague's key concern is the sub-pixel problem')"
  - "prompt.txt §3–§4 (the colleague's two-route framing and model suggestions)"
  - "BUILD_BRIEF §B.6 (contributor identity inferred; relationship to PI open)"
evidence_strength: inference
confidence: low
maturity: project_decision_needed
owner_role: ""
stakeholders:
  - "[[PI Role]]"
upstream_nodes:
  - "[[Partner Roles Overview]]"
downstream_nodes: []
related_nodes:
  - "[[Sub Pixel Problem]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[PI Role]]"
  - "[[Partner Roles Overview]]"
key_terms: []
risks: []
open_questions:
  - "Who is the 'colleague' referenced in the sources?"
  - "Is the contributor the same person as the [[PI Role]], or a separate collaborator?"
validation_needs:
  - "Confirm whether a distinct methodology contributor exists and their identity."
aliases:
  - "Methodology Contributor"
  - "The Colleague"
tags:
  - methodology-graph
  - partner
---

# Methodology Contributor Role

The **"colleague"** credited in the sources with raising the sub-pixel concern and framing the two methodological routes — a role inferred from references, with **no name and an unresolved relationship to the PI**.

> [!note] Inference — identity and even existence-as-a-separate-person are open
> [[Source - Methodology Synthesis Prompt]] repeatedly attributes the core methodological insight to "your colleague": *"Your colleague's key concern is the sub-pixel problem"* (§2), and the two-route framing and model suggestions (§3–§4). The [[Source - Methodology Idea]] narrative, however, presents these same ideas in the first person. **Whether the "colleague" is a distinct collaborator or simply how the analyst referred to the design author is unresolved** (BUILD_BRIEF §B.6). Hence `evidence_strength: inference`, `confidence: low`.

## What the role contributed (from the sources)

- **The sub-pixel concern.** The colleague is named as the source of the central observation behind [[Sub Pixel Problem]]: at today's resolutions a small horticultural plot is sub-pixel, so the satellite "does not see the plot cleanly" (prompt.txt §2).
- **The downscaling critique.** The colleague's argument that one should not "first manufacture a fine pixel and then use that fine pixel as if it were a real measurement" frames the one-step alternative (prompt.txt §2; see [[Downscaling Critique]]).
- **The two-route framing.** The colleague is credited with both [[Route A - Direct Probabilistic Fusion]] (the "hardcore" probabilistic-ML route, with Bayesian hierarchical model / Gaussian process suggestions, prompt.txt §3) and [[Route B - Homogeneous Patch Proxy]] (the lighter biological-proxy route, including the control-stand seed idea, prompt.txt §4).

## Relationship to the PI

This is the key ambiguity. The same intellectual content is voiced in the first person in [[Source - Methodology Idea]] and attributed to "your colleague" in [[Source - Methodology Synthesis Prompt]]. The contributor may be: (a) the same person as the [[PI Role]]; or (b) a separate scientific collaborator. The graph records this as an **open question** rather than resolving it *(inference)*.

## Source grounding

- Sub-pixel and downscaling attribution: [[Source - Methodology Synthesis Prompt]] §2.
- Two-route attribution: [[Source - Methodology Synthesis Prompt]] §3–§4; corroborated by [[Source - Methodology Idea]].
- Unconfirmed identity / PI relationship: BUILD_BRIEF §B.6.

## Links & relationships

This node sits under [[Partner Roles Overview]], is paired with [[PI Role]], and anchors the contributor's intellectual footprint across [[Sub Pixel Problem]], [[Route A - Direct Probabilistic Fusion]] and [[Route B - Homogeneous Patch Proxy]].

## Open questions

1. Who is the "colleague"?
2. Same person as the PI, or a distinct collaborator?

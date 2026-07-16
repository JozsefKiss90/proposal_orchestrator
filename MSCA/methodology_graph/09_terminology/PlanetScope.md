---
id: METH-TERM-027
title: "PlanetScope"
node_type: concept
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
  - "[[Source - Methodology Synthesis Prompt]]"
  - "[[Source - Literature Review]]"
evidence_basis:
  - "prompt.txt §3 (PlanetScope: higher resolution, for small fields if available)"
  - "litreview Report A §3.2 (high-res, fused with S2; sparse use; yield/land-cover), key limitations (cost/access)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes: []
key_terms:
  - "[[PlanetScope Usage Gap]]"
  - "[[Earth Observation Layer]]"
  - "[[Sentinel 2]]"
  - "[[Data Access Risks]]"
risks: []
open_questions:
  - "Is PlanetScope access secured or only optional? (RQ8)"
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# PlanetScope

High-resolution CubeSat optical imagery, valuable for small fields but constrained by cost and access.

## Definition / What it is

PlanetScope is a commercial CubeSat constellation providing high-spatial-resolution optical imagery, useful for small fields if available (prompt.txt §3). The literature review reports that its high resolution is especially valuable when fused with [[Sentinel 2]], but few studies combine PlanetScope with both radar and ground sensors for drought/irrigation in row crops; most applications use it for yield estimation or land-cover classification rather than direct plant-based drought monitoring (litreview Report A §3.2). Sparse use is attributed to cost and data-access issues (litreview Report A, key limitations).

## Role in this methodology

PlanetScope is the high-resolution optical channel of the [[Earth Observation Layer]], attractive for resolving small horticultural plots. Its rarity in fully integrated row-crop frameworks defines the [[PlanetScope Usage Gap]], part of the project's novelty space. Its cost/access constraints make it a [[Data Access Risks]] item.

> [!warning] Unconfirmed
> Whether PlanetScope access is secured or only optional for this project is open (RQ8). Treat availability as not yet confirmed.

## Related

[[PlanetScope Usage Gap]] · [[Earth Observation Layer]] · [[Sentinel 2]] · [[Data Access Risks]]

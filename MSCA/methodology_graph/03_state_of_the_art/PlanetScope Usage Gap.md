---
id: METH-SOTA-003
title: "PlanetScope Usage Gap"
node_type: state_of_the_art
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
evidence_basis:
  - "litreview Report A §3.2, §5 Key limitations (sparse PlanetScope use, cost/access), Fig.5 (full integration incl. PlanetScope = Moderate), Fig.6 (Real-Time DS x PlanetScope = GAP)"
  - "Report A DOIs: Ihuoma 2021 (j.jag.2021.102396), Kpienbaareh 2021 (rs13040700), Farmonov 2023 (10.1080/17538947.2023.2186505)"
evidence_strength: source_grounded
confidence: high
maturity: validated_in_literature
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
downstream_nodes: []
related_nodes:
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Research Gap Matrix]]"
  - "[[Data Access Risks]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
key_terms:
  - "[[PlanetScope]]"
  - "[[Sentinel 2]]"
risks:
  - "[[Data Access Risks]]"
open_questions:
  - "RQ8: Is PlanetScope access secured or only optional? (see [[Ten Research Questions]])"
validation_needs: []
aliases:
  - "PlanetScope Gap"
tags:
  - methodology-graph
  - state-of-the-art
---

# PlanetScope Usage Gap

The literature finding that `[[PlanetScope]]` high-resolution imagery, despite its value for small fields, is **rarely** combined with both radar (`[[Sentinel 1]]`) and ground sensors for drought-stress or irrigation work in row crops — a key gap this project could occupy.

## What the literature establishes

Section 3.2 of `[[Source - Literature Review]]` (Report A) finds that while PlanetScope's high spatial resolution is valuable for field-scale mapping — **especially when fused with `[[Sentinel 2]]`** — **few studies explicitly combine PlanetScope with both radar (Sentinel-1) and ground-based sensors** for drought stress or irrigation optimisation in row crops (Ihuoma et al. 2021; Kpienbaareh et al. 2021; Farmonov et al. 2023). Most applications use PlanetScope **primarily for yield estimation or land-cover classification** rather than direct plant-based drought monitoring.

In Report A's Claims & Evidence table (Figure 5), the claim *"Full integration including PlanetScope is rare in row-crop drought/irrigation research"* is rated **Moderate** — only a handful of studies attempt it; most focus on partial combinations.

## Why it matters: cost and access

Report A's §5 Key Limitations names **sparse use of PlanetScope alongside other satellites due to cost/data-access issues** as a leading limitation of the field. The report frames the gap as an *opportunity* for future work, "especially as CubeSat constellations expand coverage." High resolution is exactly what helps with small horticultural plots, which connects this gap to the project's `[[Route A - Direct Probabilistic Fusion]]`, where PlanetScope is listed as a higher-resolution input for small fields when available.

## The matrix GAP cell

In the `[[Research Gap Matrix]]` (Report A, Figure 6), PlanetScope is the sparsest column throughout (Drought Stress Detection = 3 studies, Irrigation Optimization = 2), and the **Real-Time Decision Support × PlanetScope** cell is the single explicit **GAP** in the figure. The figure caption itself notes that studies including PlanetScope are *"especially rare."*

> [!warning] Unconfirmed — project access
> Whether **PlanetScope access is secured** for this project, or only an optional input, is **not established in any source**. This is open research question **RQ8** (see `[[Data Access Risks]]` and `[[Ten Research Questions]]`). The project must not assume guaranteed PlanetScope access.

## Role in this methodology

This gap is dual-edged: it is both a *novelty opportunity* (incorporating PlanetScope into a fused, probabilistic, decision-oriented framework is under-explored) and a *risk* (cost and access uncertainty — see `[[Data Access Risks]]`). It is a child of `[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]` and feeds the gap argument in `[[Research Gap Matrix]]`.

---
id: METH-GOV-003
title: "Source Traceability Register"
node_type: governance
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
  - "[[Source - LLM Wiki Method]]"
evidence_basis:
  - "litreview Report A (pp.1-8) & Report B (pp.9-12)"
  - "methodology_idea.txt; prompt.txt"
  - "doi:10.1016/j.envsoft.2022.105556"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[Source - Literature Review]]"
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
  - "[[Source - LLM Wiki Method]]"
  - "[[Methodology Graph Schema]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Traceability Register"
  - "Source Register"
tags:
  - methodology-graph
  - governance
---

# Source Traceability Register

Maps each immutable source to the nodes that cite it, and surfaces the graph's evidence health. It enforces the LLM-wiki rule that every claim is source-grounded (see [[Methodology Graph Schema]] and [[Graph Maintenance Rules]]). Up to the [[Methodology Graph - Meta Node]].

## Sources and where they are cited

| Source note | Backing file | Primary citing nodes |
|---|---|---|
| [[Source - Literature Review]] | `sources/literature_review.pdf` (pp.1–8 = Report A; pp.9–12 = Report B) | [[State of the Art - Multi Sensor Crop Water Stress Monitoring]], [[Sentinel 1 and Sentinel 2 Integration]], [[PlanetScope Usage Gap]], [[Meteorological and Soil Sensor Integration]], [[Operational Decision Support Gap]], [[Research Gap Matrix]], [[Probabilistic Fusion Novelty Claim]] |
| [[Source - Methodology Idea]] | `sources/methodology_idea.txt` | [[Core Architecture]], [[Sub Pixel Problem]], [[Downscaling Critique]], [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]], [[Control Stand Variant]], [[AquaCrop Decision Interface]], [[Uncertainty Aware AquaCrop Calibration]], [[PI Role]] |
| [[Source - Methodology Synthesis Prompt]] | `sources/prompt.txt` | [[Core Architecture]], [[Diagnostic Branch]], [[Prognostic Branch]], [[Observation to Decision Pipeline]], [[Infrastructure Architecture]], all decision nodes, [[Ten Research Questions]] |
| [[Source - LLM Wiki Method]] | build request (Karpathy method) | [[Methodology Graph - Meta Node]], [[Methodology Graph Schema]], [[Graph Maintenance Rules]], [[log]] |

## Key DOIs and identifiers

> [!note] PI prior method
> **doi:10.1016/j.envsoft.2022.105556** (Environmental Modelling & Software, 2022) — the PI's own uncertainty-aware calibration method, cited by [[Uncertainty Aware AquaCrop Calibration]]. The DOI is **source-grounded** (PI-stated in `methodology_idea.txt`); its descriptive title ("Conditional interval reduction method") is the **analyst's inference** in `prompt.txt` §5, not a verified title.

Report A reference DOIs (from `literature_review.pdf`, listed for traceability in [[Source - Literature Review]]): Chun-Yang 2022 (rs14051205); Abdelrahim & Jin 2025 (s10661-025-13686-3); Amankulova 2024 (j.asr.2024.01.040); Bousbih 2018 (rs10121953); Chakhar 2024 (rs16030458); Corbari 2022 (10.1080/22797254.2022.2084643); Duan 2025 (jstars.2025.3580652); Elwan 2022 (w14050804); Farmonov 2023 (10.1080/17538947.2023.2186505); Ferrant 2017 (rs9111119); Gao 2018 (rs10091495); Ghazaryan 2020 (10.1080/15481603.2020.1778332); Hamze 2023 (rs15164081); Ibrahim 2023 (s10661-023-11871-w); Ihuoma 2021 (j.jag.2021.102396); Izquierdo-Sanz & Moltó 2026 (agronomy16050541); Jędrejek & Pudełko 2023 (agriculture13091798); Khabbazan 2019 (rs11161887); Kpienbaareh 2021 (rs13040700); Mkhwenkwana 2025 (j.jag.2025.104647); Müller 2025 (j.agrformet.2025.110789); Noory 2025 (j.agwat.2024.109263); Pageot 2020 (rs12183044); Wu 2024 (j.agwat.2024.108718); Zhao 2025 (rs17132130).

Report B precedents (probabilistic novelty gap, in [[Source - Literature Review]] / [[Probabilistic Fusion Novelty Claim]]): Mena 2024; Maimaitijiang 2020; Li 2025; Yewle 2025; Yang 2024; Fei 2022; Xian 2024; Ghazipour & Mahjouri 2021 (Bayesian Maximum Entropy); Guo 2025 (MF-FusionNet); Banibayat 2021 and Wang 2021 (copula); Yantao/Xue 2024 (dynamic Bayesian networks); Zhang M. 2021; Lin 2025; Liu 2025; Zhang J. 2021.

## Nodes by evidence strength (find weak spots)

```dataview
TABLE evidence_strength, confidence, source_refs
FROM #methodology-graph
WHERE node_type != "dashboard"
SORT evidence_strength ASC, id ASC
```

## Unconfirmed nodes needing source confirmation

```dataview
TABLE title, open_questions
FROM #methodology-graph
WHERE evidence_strength = "unconfirmed"
SORT id ASC
```

> [!warning] Unconfirmed evidence
> Items with `evidence_strength: unconfirmed` (e.g. [[ELTE Role]], [[AgroVIR Validation Partner Role]], [[Unconfirmed Partner Placeholders]], and the tomato/PlanetScope/TRL questions in [[Ten Research Questions]]) are **not** firmly established in the sources. They carry `confidence: low` and may only be promoted via the procedure in [[Graph Maintenance Rules]] §4.

## All source references in the graph

```dataview
TABLE source_refs
FROM #methodology-graph
WHERE source_refs
SORT id ASC
```

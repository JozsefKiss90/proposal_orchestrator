---
id: METH-SOTA-007
title: "Research Gap Matrix"
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
  - "litreview Report A Fig.6 (Research gap matrix, study counts) and its caption; §5 Research Gaps"
evidence_strength: source_grounded
confidence: high
maturity: validated_in_literature
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
downstream_nodes: []
related_nodes:
  - "[[PlanetScope Usage Gap]]"
  - "[[Operational Decision Support Gap]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
key_terms:
  - "[[PlanetScope]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Gap Matrix"
  - "Figure 6"
tags:
  - methodology-graph
  - state-of-the-art
---

# Research Gap Matrix

A faithful reproduction of **Figure 6** of `[[Source - Literature Review]]` (Report A) — the research-gap matrix counting how many of the 50 included studies address each combination of monitoring outcome and sensor integration depth.

## The matrix (Report A, Figure 6)

Each cell is a study count (number of the included papers addressing that topic × that integration level); the single explicit **GAP** label is reproduced verbatim from the figure.

| Topic / Outcome | Dual-Sentinel Integration | + Meteorology Data | + Soil Sensors | + PlanetScope |
|---|---|---|---|---|
| **Drought Stress Detection** | 18 | 10 | 7 | 3 |
| **Irrigation Optimization** | 15 | 9 | 6 | 2 |
| **Real-Time Decision Support** | 7 | 4 | 3 | **GAP** |

Figure 6 caption (Report A): *"Research gap matrix: Few studies combine all four attributes; especially rare are those including PlanetScope."*

## How to read it

Two gradients run through the matrix, and both point at the same corner:

- **Left → right (deeper sensor integration):** counts fall sharply as more sensor types are added. Adding `[[PlanetScope]]` collapses every row to single digits — corroborating the `[[PlanetScope Usage Gap]]`.
- **Top → bottom (harder task):** counts fall as the outcome shifts from detection to optimisation to real-time decision support — corroborating the `[[Operational Decision Support Gap]]`.

The two trends meet at the bottom-right cell — **Real-Time Decision Support × PlanetScope** — which is the only cell with no count, labelled **GAP**. This is the most under-served combination in the entire reviewed literature.

> [!note] Interpretation
> The empty corner is precisely where this project aims: high-resolution, fully-integrated, real-time-oriented decision support. The matrix is a quantitative complement to the *qualitative* novelty argument in `[[Probabilistic Fusion Novelty Claim]]` (which adds the further, Report-B point that even the populated cells rarely use *explicit probabilistic* outputs). The matrix counts integration breadth and task difficulty; it does **not** measure whether existing studies are probabilistic.

## Report A's open research questions

Report A §5 frames the future work the matrix implies: full integration of Sentinel-1/-2/PlanetScope/meteo/soil at field scale; optimal ML/data-fusion strategies for heterogeneous multi-source agricultural datasets; and cost-effective ground-truth networks to validate large-scale multi-sensor frameworks.

## Role in this methodology

This page is the evidentiary anchor for the gap argument. It is a child of `[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]` and is cross-referenced by `[[PlanetScope Usage Gap]]`, `[[Operational Decision Support Gap]]` and `[[Probabilistic Fusion Novelty Claim]]`.

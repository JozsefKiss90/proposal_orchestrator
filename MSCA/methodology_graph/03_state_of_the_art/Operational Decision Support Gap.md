---
id: METH-SOTA-005
title: "Operational Decision Support Gap"
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
  - "litreview Report A §3.4, §5 Key limitations (limited operational frameworks), Fig.5 (lack of operational frameworks unifying all sensors = Moderate, Duan 2025), Fig.6 (Real-Time Decision Support row)"
  - "Report A DOI: Duan 2025 (jstars.2025.3580652)"
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
  - "[[Decision Engine Layer]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Web MVP and User Interface Layer]]"
  - "[[Operationalisation Risks]]"
key_terms:
  - "[[Data Fusion]]"
risks:
  - "[[Operationalisation Risks]]"
open_questions:
  - "RQ10: TRL target (research prototype / validated MVP / operational pilot)? (see [[Ten Research Questions]])"
validation_needs: []
aliases:
  - "Operational Frameworks Gap"
  - "Real-Time DSS Gap"
tags:
  - methodology-graph
  - state-of-the-art
---

# Operational Decision Support Gap

The literature finding that there are **limited operational frameworks** fusing all sensor types into real-time, decision-support tools — the gap the project's decision engine is designed to address.

## What the literature establishes

Section 3.4 of `[[Source - Literature Review]]` (Report A) reports that near-real-time pipelines exist (e.g. via Google Earth Engine; Duan et al. 2025), but that **few studies achieve full integration across all desired sensor types at scale**. Section 5's Key Limitations names this directly: **"Limited operational frameworks that fuse all sensor types into real-time decision-support tools."** The same section also flags challenges in harmonizing spatial/temporal resolutions across disparate datasets and few large-scale validation efforts — both of which compound the operational difficulty.

In Report A's Claims & Evidence table (Figure 5), the claim *"There is a lack of operational frameworks unifying all sensor types at scale for real-time decision support in row-crops"* is rated **Moderate**, with the reasoning that **most operational tools use only subsets of available sensors/data streams** (Duan et al. 2025).

## The matrix evidence

In the `[[Research Gap Matrix]]` (Report A, Figure 6), the **Real-Time Decision Support** row is the sparsest across every column (Dual-Sentinel = 7, +Meteorology = 4, +Soil sensors = 3), and its intersection with PlanetScope is the figure's single explicit **GAP** cell. This quantifies the §5 limitation: decision-support work thins out exactly as sensor integration deepens.

> [!note] Distinction
> Report A's operational gap is about *integration breadth and real-time delivery*. The project's deeper, complementary claim — that fused observations are rarely turned into *explicit probabilistic states* and *economically optimised* irrigation decisions — comes from Report B and is argued in `[[Probabilistic Fusion Novelty Claim]]`. The two gaps reinforce each other.

## Role in this methodology

This gap is the target of the project's decision side. The `[[Decision Engine Layer]]` (irrigation recommendation engine, economic objective function, risk thresholds) and the `[[Web MVP and User Interface Layer]]` are designed to deliver exactly the real-time, all-sensor decision support the literature finds missing. Per `[[Source - Methodology Synthesis Prompt]]` §8, the MVP is positioned as a **standalone research demonstrator**, not a commercial operational product — keeping ambition matched to a research scope.

> [!warning] Unconfirmed — TRL target
> How far toward "operational" the project actually goes (research prototype vs validated MVP vs operational pilot) is **open** — research question **RQ10** (see `[[Operationalisation Risks]]` and `[[Ten Research Questions]]`). Do not claim a specific TRL.

This page is a child of `[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]`.

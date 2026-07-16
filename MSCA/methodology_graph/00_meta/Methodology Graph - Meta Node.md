---
id: METH-META-001
title: "Methodology Graph - Meta Node"
node_type: meta
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
  - "methodology_idea.txt (PI design narrative)"
  - "prompt.txt §1, §9, §10"
  - "litreview Report A & Report B"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders:
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
upstream_nodes: []
downstream_nodes:
  - "[[index]]"
  - "[[Methodology Graph Dashboard]]"
  - "[[Methodology Graph Schema]]"
  - "[[Graph Maintenance Rules]]"
  - "[[Source Traceability Register]]"
  - "[[Core Architecture]]"
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[AquaCrop Decision Interface]]"
  - "[[Infrastructure Architecture]]"
  - "[[Methodology SWOT Matrix]]"
  - "[[Partner Roles Overview]]"
  - "[[Ten Research Questions]]"
related_nodes:
  - "[[Source - Literature Review]]"
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
  - "[[Source - LLM Wiki Method]]"
key_terms:
  - "[[Uncertainty Propagation]]"
  - "[[Data Fusion]]"
  - "[[Crop Water Stress]]"
  - "[[Expected Profit]]"
risks:
  - "[[Methodology SWOT Matrix]]"
open_questions:
  - "[[Ten Research Questions]]"
validation_needs:
  - "[[Validation and Field Trial Layer]]"
aliases:
  - "Methodology Graph Home"
  - "Meta Node"
tags:
  - methodology-graph
  - meta
---

# Methodology Graph - Meta Node

Top-level hub for the methodology knowledge graph of an MSCA-style research proposal on **crop water-stress monitoring and irrigation decision support**, built and governed as a Karpathy **LLM-wiki** layer (see [[Source - LLM Wiki Method]]).

## Mission

The proposed project would **diagnose** crop/soil/water status from multiple uncertain data streams, use that diagnosis to **simulate** alternative irrigation decisions, and **recommend** the option with the best expected economic outcome. The problem has **two branches**: a diagnostic one (the actual state of field, plant, soil and water) and a prognostic one with counterfactuals (given that state, what happens under each decision, so the best can be chosen). This framing is taken directly from the PI's design narrative (see [[Source - Methodology Idea]]) and the analyst synthesis (see [[Source - Methodology Synthesis Prompt]] §1).

## The red thread: uncertainty

The two branches are tied together by **one chain that carries its uncertainty from end to end**; the PI calls keeping that uncertainty honest "the heart of the whole thing." Every model output must say not only *what the state is* but *how sure we are*, and that uncertainty must travel all the way into the irrigation decision. This is captured canonically in the [[Uncertainty Chain]] and operationalised as [[Uncertainty Propagation]] across [[Diagnostic Branch]] and [[Prognostic Branch]].

## Two routes, one shared decision engine

A single thread runs under **two routes** to the diagnosed field state (see [[Source - Methodology Idea]]):

- **[[Route A - Direct Probabilistic Fusion]]** — the "hardcore" one-step route: feed the satellite as one more input into a probabilistic ML model (e.g. [[Bayesian Hierarchical Model]] or [[Gaussian Process]]) that takes satellite + sensors + soil + weather together and goes straight to field state with uncertainty, avoiding the two-step [[Downscaling Critique]] of the [[Sub Pixel Problem]].
- **[[Route B - Homogeneous Patch Proxy]]** — the "creative/easier" route that sidesteps the resolution problem by reading a nearby homogeneous covarying patch the coarse pixel can read cleanly; its seed variant is the [[Control Stand Variant]].

**From the diagnosed state onward the path is the same for both routes.** Both feed the [[AquaCrop Decision Interface]], which "stands for the plant" and is the interface through which decisions act, calibrated in an uncertainty-aware way (see [[Source - Methodology Idea]], doi:10.1016/j.envsoft.2022.105556). The shared engine runs counterfactual irrigation scenarios over weather ensembles and steers toward the best [[Expected Profit]].

## Novelty claim *(proposal synthesis)*

From Report B and the analyst synthesis (§9): multimodal [[Data Fusion]] is mature, but **probabilistic, row-crop drought/irrigation decision frameworks remain underdeveloped**, so a Bayesian/data-fusion approach can still be novel. The defendable claim is detailed in [[Probabilistic Fusion Novelty Claim]] — short form: *"From multi-sensor observation to probabilistic diagnosis to economically optimized irrigation decision."*

## MSCA context

For an MSCA-style proposal, the tool is presented as a **standalone research demonstrator** (an MVP / [[Web MVP and User Interface Layer]]), with AgroVIR-like partners assisting with feedback, farmer access, testing and validation rather than owning or operating it (see [[Partner Roles Overview]] and [[Source - Methodology Synthesis Prompt]] §8).

> [!warning] Unconfirmed items
> Several items are **not** firmly established in the sources and are flagged across the graph: the first crop being **tomato** (tentative), partner identities (**ELTE** absent from sources; **AgroVIR** only as "AgroVIR-like"), PlanetScope access, and the TRL target. See [[Ten Research Questions]] and [[Partner Roles Overview]].

## Navigation

- Governance: [[Methodology Graph Schema]] · [[Graph Maintenance Rules]] · [[Source Traceability Register]]
- Map & dashboards: [[index]] · [[Methodology Graph Dashboard]]
- Architecture: [[Core Architecture]] · [[Infrastructure Architecture]]
- Evidence base: [[State of the Art - Multi Sensor Crop Water Stress Monitoring]]
- Routes & decisions: [[Route A - Direct Probabilistic Fusion]] · [[Route B - Homogeneous Patch Proxy]] · [[AquaCrop Decision Interface]]
- Risk & open issues: [[Methodology SWOT Matrix]] · [[Ten Research Questions]]
- Partners: [[Partner Roles Overview]]

## Source grounding

This node is a **synthesis** combining all four sources: the PI narrative ([[Source - Methodology Idea]]), the analyst synthesis ([[Source - Methodology Synthesis Prompt]]), the literature review ([[Source - Literature Review]]), and the governing method ([[Source - LLM Wiki Method]]). The synthesis framing (two routes, one shared decision engine) follows the analyst's instinct in §10.

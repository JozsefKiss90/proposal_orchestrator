---
id: METH-SRC-003
title: "Source - Methodology Synthesis Prompt"
node_type: source
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
evidence_basis:
  - "sources/prompt.txt"
  - "prompt.txt §1-§10"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes:
  - "[[Core Architecture]]"
  - "[[Infrastructure Architecture]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Ten Research Questions]]"
related_nodes:
  - "[[Core Architecture]]"
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[AquaCrop Decision Interface]]"
  - "[[Infrastructure Architecture]]"
  - "[[Methodology SWOT Matrix]]"
  - "[[Partner Roles Overview]]"
  - "[[Ten Research Questions]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Multimodal Fusion]]"
  - "[[Latent Field State]]"
  - "[[Uncertainty Propagation]]"
  - "[[Counterfactual Simulation]]"
  - "[[Expected Profit]]"
  - "[[Crop Water Stress]]"
  - "[[Posterior Distribution]]"
risks: []
open_questions:
  - "[[Ten Research Questions]]"
validation_needs: []
aliases:
  - "prompt.txt"
  - "Analyst Synthesis"
tags:
  - methodology-graph
  - source
---

# Source - Methodology Synthesis Prompt

> [!note] Immutable source note
> This node is a faithful précis of the raw source `sources/prompt.txt` — a **10-section analyst synthesis** that reorganises the PI's design ([[Source - Methodology Idea]]) into proposal-ready structure and cross-checks it against the [[Source - Literature Review]]. The raw file is immutable per [[Source - LLM Wiki Method]].

One-line summary: an analyst's structured synthesis that fixes the **core architecture**, restates the **sub-pixel/downscaling argument**, details **both routes** and **AquaCrop's decision role**, defines the **counterfactual, profit-based decision principle**, lays out **plain-English terminology** and **infrastructure layers**, locates the **defendable novelty**, and ends with **ten clarification questions**.

## Section map (faithful)

1. **Core architecture (§1).** Pipeline: `Satellite + soil sensors + weather + field observations → probabilistic field-state diagnosis → uncertainty-aware AquaCrop calibration → counterfactual irrigation simulations → profit/risk-based recommendation`. Two blocks — **Diagnostic** (water stress, soil moisture, crop condition, phenology) and **Prognostic** (option A/B/C → select best) — formalised in [[Core Architecture]]. The literature supports the framing, but **"fusion → probabilistic drought state → optimized irrigation" is not yet well established**.
2. **Sub-pixel problem & downscaling critique (§2).** A small horticultural pixel may contain target crop **plus** neighbouring vegetation, bare soil, roads, buildings ([[Sub Pixel Problem]]). Prefer `covariates + uncertainty → prediction directly` over `covariates → estimated fine pixel → prediction`, because the latter pretends an estimated pixel is an observed fact ([[Downscaling Critique]]).
3. **Route 1 — hardcore probabilistic fusion (§3).** Inputs: [[Sentinel 1]] radar (through cloud; sensitive to surface structure/moisture), [[Sentinel 2]] optical ([[NDVI]]/[[NDWI]]/[[NDMI]]), [[PlanetScope]] (higher res, for small fields if available), weather (rainfall, temp, ET, radiation, wind), soil sensors (moisture, temp, conductivity), field observations (crop type, growth stage, irrigation logs, yield, biomass, visual stress). Estimates the **hidden state** ([[Latent Field State]]): [[Root Zone Soil Moisture]], plant water stress, canopy development, biomass, expected yield. Models: [[Bayesian Hierarchical Model]], [[Gaussian Process]], [[Probabilistic Machine Learning]] (return distributions/intervals). "Rigorous but demanding." → [[Route A - Direct Probabilistic Fusion]].
4. **Route 2 — patch/biological proxy (§4).** A nearby homogeneous patch the satellite reads cleanly, with similar soil/climate/biological response; experimental version = plant a **control stand of a covarying species** ("a designed proxy sensor"). Easier to pilot; connects to ecosystem continuity / semi-natural patches / extensive agriculture / landscape sustainability. **Needs validation** (must show the patch really covaries with the target crop). → [[Route B - Homogeneous Patch Proxy]], [[Control Stand Variant]].
5. **AquaCrop's role (§5).** FAO crop-growth model simulating **yield response to water**, suited where **water is limiting**; the bridge from monitoring to decision-making and the **decision simulator** ("what if we irrigate today / delay / apply less / water prices high / coming weather dry-wet-hot"). The DOI method is identified by the analyst as a **"Conditional interval reduction method"** for optimizing process-based models while retaining parameter uncertainty. → [[AquaCrop Decision Interface]], [[Uncertainty Aware AquaCrop Calibration]].
6. **Decision principle = counterfactual optimization (§6).** Candidate decisions: no irrigation; irrigate today; irrigate in 2 days; apply 10/20/30 mm; deficit irrigation; later, fertilization strategies. Run each under multiple weather futures, compare expected outcomes. **Objective = profit, not yield:** `expected crop value − water cost − energy cost − input cost − operational cost`. Moves the project from "nice monitoring dashboard" to "decision-support tool that can pay for itself." → [[Counterfactual Irrigation Simulation]], [[Profit Based Objective Function]].
7. **Terminology, plain English (§7).** [[Data Fusion]], [[Multimodal Fusion]], [[Ground Truth]], [[Covariate]], [[Downscaling]], [[Cokriging]], [[Latent Field State]], [[Posterior Distribution]], [[Uncertainty Propagation]], [[Counterfactual Simulation]], [[Weather Ensemble]], [[Expected Profit]]/[[Expected Utility]], [[Decision Regret]]. This section seeds the 09_terminology glossary.
8. **Infrastructure layers (§8).** Earth observation; ground sensing; data platform; modelling; decision; validation; user interface — formalised in [[Infrastructure Architecture]]. For an **MSCA-style proposal**, present the **MVP as a standalone research demonstrator**, with **AgroVIR-like partners** helping with feedback / farmer access / testing / validation **rather than owning or operating the tool**.
9. **Novelty (§9).** NOT "using satellite data for irrigation" (too broad). Defendable claim: *"develops and validates an uncertainty-aware, end-to-end decision framework that directly fuses multi-source satellite, soil, weather and field data into probabilistic crop-water-state estimates, couples these with AquaCrop-based counterfactual simulation, and optimizes irrigation decisions by expected economic return under weather and model uncertainty."* Short form: *"From multi-sensor observation to probabilistic diagnosis to economically optimized irrigation decision."* → [[Probabilistic Fusion Novelty Claim]].
10. **Ten clarification questions (§10).** Captured in [[Ten Research Questions]]. The analyst's instinct: frame as a **two-route methodology with one shared decision engine** — Route A rigorous probabilistic fusion, Route B ecological proxy/control-patch — for ambition + flexibility + a credible fallback.

> [!note] Synthesis vs source
> This is the **analyst's synthesis**, not the PI's primary statement. Where it identifies the calibration DOI as a "Conditional interval reduction method," the descriptive *title* is **analyst inference**; the DOI itself (10.1016/j.envsoft.2022.105556) is PI-given fact — see [[Uncertainty Aware AquaCrop Calibration]]. Partner references ("AgroVIR-like") are illustrative roles, not committed partnerships — see [[Partner Roles Overview]].

## Role in this methodology

This source is the **structural blueprint** for the whole graph: it maps almost one-to-one onto the category hubs ([[Core Architecture]], [[State of the Art - Multi Sensor Crop Water Stress Monitoring]], the two routes, [[AquaCrop Decision Interface]], [[Infrastructure Architecture]], [[Methodology SWOT Matrix]], [[Partner Roles Overview]]) and originates the [[Ten Research Questions]]. It complements [[Source - Methodology Idea]] (the why/intent) and is cross-checked against [[Source - Literature Review]] (the evidence). Navigate up via the [[Methodology Graph - Meta Node]]; the [[Source Traceability Register]] tracks which nodes cite it.

## Links & relationships
- **Feeds:** [[Core Architecture]], [[Infrastructure Architecture]], [[Probabilistic Fusion Novelty Claim]], [[Ten Research Questions]]
- **Related:** [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]], [[AquaCrop Decision Interface]], [[Methodology SWOT Matrix]], [[Partner Roles Overview]], [[Source - Methodology Idea]], [[Source - Literature Review]]
- **Key terms:** [[Data Fusion]], [[Multimodal Fusion]], [[Latent Field State]], [[Uncertainty Propagation]], [[Counterfactual Simulation]], [[Expected Profit]], [[Crop Water Stress]], [[Posterior Distribution]]

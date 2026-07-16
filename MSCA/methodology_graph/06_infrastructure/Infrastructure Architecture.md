---
id: METH-INFRA-001
title: "Infrastructure Architecture"
node_type: architecture
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
  - "[[Source - Methodology Idea]]"
evidence_basis:
  - "prompt.txt §8 (infrastructure layers table)"
  - "prompt.txt §1 (core architecture pipeline)"
  - "methodology_idea.txt (data is the easy part; fusion/modelling/validation is where it lives or dies)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes:
  - "[[Earth Observation Layer]]"
  - "[[Ground Sensing Layer]]"
  - "[[Weather and Climate Data Layer]]"
  - "[[Geospatial and Time Series Data Platform]]"
  - "[[Probabilistic Modelling Runtime]]"
  - "[[AquaCrop Simulation Runtime]]"
  - "[[Decision Engine Layer]]"
  - "[[Validation and Field Trial Layer]]"
  - "[[Web MVP and User Interface Layer]]"
related_nodes:
  - "[[Core Architecture]]"
  - "[[Observation to Decision Pipeline]]"
key_terms:
  - "[[Data Fusion]]"
risks: []
open_questions:
  - "[[Ten Research Questions]]"
validation_needs:
  - "Confirm which layers are built in-project vs. assumed external services"
aliases:
  - "Infrastructure layers"
  - "System architecture"
tags:
  - methodology-graph
  - infrastructure
---

# Infrastructure Architecture

Layered overview of the technical infrastructure implied by the methodology, organising the system from sensing through data management, modelling, decision-making, validation and user interface.

## What it is

This node is the infrastructure hub. It mirrors the pipeline defined in [[Core Architecture]] and [[Observation to Decision Pipeline]], but viewed as the *stack of layers* that would have to exist for the method to run end-to-end. The grouping into layers is taken directly from the analyst synthesis (prompt.txt §8); the framing as a single coherent architecture is *(proposal synthesis)* across the idea and prompt sources.

> [!note] Why infrastructure matters here
> The PI narrative is explicit that **data (ground truth plus signals) is the easy part**; the real work where the project "lives or dies" is **fusion, modelling and validation** (methodology_idea.txt). The infrastructure layers below are therefore not the scientific contribution in themselves — they are the substrate that lets the [[Data Fusion]], probabilistic diagnosis and decision steps happen.

## The layers

The analyst synthesis (prompt.txt §8) lists the infrastructure as the following layers. Each has its own canonical node:

| Layer | Components (per prompt.txt §8) | Node |
|---|---|---|
| Earth observation | Sentinel-1, Sentinel-2, PlanetScope, field boundaries, cloud masking, temporal compositing | [[Earth Observation Layer]] |
| Ground sensing | Soil-moisture sensors, weather station / meteo data, irrigation logs, crop observations | [[Ground Sensing Layer]] |
| Data platform | Geospatial database, time-series database, metadata catalogue, quality-control pipeline | [[Geospatial and Time Series Data Platform]] |
| Modelling | Probabilistic fusion model, uncertainty estimation, AquaCrop calibration, scenario simulation | [[Probabilistic Modelling Runtime]], [[AquaCrop Simulation Runtime]] |
| Decision | Irrigation recommendation engine, economic objective function, risk thresholds | [[Decision Engine Layer]] |
| Validation | Field trials, sensor comparison, model accuracy, uncertainty calibration, decision-performance metrics | [[Validation and Field Trial Layer]] |
| User interface | Web MVP / dashboard for farmers, advisors, validation partners | [[Web MVP and User Interface Layer]] |

> [!note] Weather and climate as a distinct layer
> prompt.txt §8 places weather/meteo data inside the ground-sensing row, but the weather inputs (rainfall, temperature, evapotranspiration, radiation, wind; ERA5-Land; and the future **weather ensembles** used downstream) are substantial enough to warrant their own canonical node, [[Weather and Climate Data Layer]]. This split is *(proposal synthesis)*; the underlying components remain source-grounded.

## Role in this methodology

Reading the stack bottom-up: the **observation layers** ([[Earth Observation Layer]], [[Ground Sensing Layer]], [[Weather and Climate Data Layer]]) feed the **data platform** ([[Geospatial and Time Series Data Platform]]); the platform feeds the **modelling layers** that produce the probabilistic field-state diagnosis and run AquaCrop scenarios; the **decision layer** turns those scenarios into an irrigation recommendation; the **validation layer** checks every stage; and the **user interface** exposes the result. This is the physical realisation of the [[Observation to Decision Pipeline]].

## MVP positioning (MSCA framing)

For an MSCA-style proposal, the analyst synthesis recommends presenting the MVP / user-interface layer as a **standalone research demonstrator**, with **AgroVIR-like partners** helping with feedback, farmer access, testing and validation **rather than owning or operating the tool** (prompt.txt §8). This is a deliberate scoping choice that keeps the project a research demonstrator rather than a commercial product.

> [!warning] Unconfirmed partner role
> "AgroVIR-like partners" is the only partner phrasing in the sources — it is an example role, not a committed partnership. Treat any specific partner as unconfirmed (see [[Web MVP and User Interface Layer]] and the partner nodes). confidence: low on partner specifics.

## Links & relationships

Up to the hub [[Methodology Graph - Meta Node]]; closely tied to [[Core Architecture]] and [[Observation to Decision Pipeline]]. Down to the nine layer nodes listed above. Open scoping questions (which layers are in-project, the TRL target, validation protocol) are tracked in [[Ten Research Questions]].

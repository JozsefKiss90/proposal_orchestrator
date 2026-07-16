---
id: METH-CORE-002
title: "Diagnostic Branch"
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
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "methodology_idea.txt (diagnostic branch: actual state of field/plant/soil/water)"
  - "prompt.txt §1 (Diagnostic block: water stress, soil moisture, crop condition, phenology)"
  - "prompt.txt §3 (hidden state: root-zone soil moisture, plant water stress, canopy, biomass, yield)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Core Architecture]]"
  - "[[Observation to Decision Pipeline]]"
downstream_nodes:
  - "[[AquaCrop Decision Interface]]"
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Sub Pixel Problem]]"
  - "[[Uncertainty Chain]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Crop Water Stress]]"
  - "[[Root Zone Soil Moisture]]"
  - "[[Latent Field State]]"
  - "[[Posterior Distribution]]"
  - "[[Data Fusion]]"
  - "[[Evapotranspiration]]"
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
  - "[[SAR]]"
risks: []
open_questions:
  - "What exactly is the target field state? (RQ3, see [[Ten Research Questions]])"
validation_needs:
  - "Ground-truth collection (RQ4); uncertainty calibration (RQ5)"
aliases:
  - "Diagnostic Block"
tags:
  - methodology-graph
  - core
---

# Diagnostic Branch

The diagnostic branch is the "what is happening now" half of the [[Core Architecture]]: it estimates the current, not-directly-observed condition of the crop/soil/water system — the [[Latent Field State]] — from fused, uncertain observation streams, and reports that estimate with explicit uncertainty.

## What it is

The PI narrative defines this as the first of the two branches: *"what is the actual state of the field, the plant, the soil, the water?"* (methodology_idea.txt). The analyst synthesis names the same thing the **Diagnostic block** and lists its targets: *"estimate water stress, soil moisture, crop condition, phenology"* (prompt.txt §1).

More precisely, the diagnostic step infers a **hidden state** of the field from all available inputs. The source lists this state as *root-zone soil moisture, plant water stress, canopy development, biomass, expected yield* (prompt.txt §3). In the vocabulary of this graph these are facets of the [[Latent Field State]], with [[Crop Water Stress]] and [[Root Zone Soil Moisture]] as the central state variables, and [[Evapotranspiration]] entering as a closely related water-balance quantity.

## Role in this methodology

The branch sits between the observation layers and the decision engine. Upstream it draws on the [[Observation to Decision Pipeline]] and the [[Core Architecture]]; downstream its diagnosed state feeds the [[AquaCrop Decision Interface]], which takes that state forward into prognosis. Its outputs are not point estimates but distributions — the [[Posterior Distribution]] of the field state — so the diagnosis hands an honest uncertainty range to the [[Uncertainty Chain]] rather than a single overconfident value.

The branch is realised through [[Data Fusion]] of multiple modalities: [[SAR]] (Sentinel-1 radar, all-weather, sensitive to surface structure/moisture) and the Sentinel-2 optical indices [[NDVI]], [[NDWI]] and [[NDMI]], together with soil-sensor and weather inputs. This is exactly the input set described for the fusion model (prompt.txt §3).

## The sub-pixel obstacle

A central difficulty for the diagnostic branch is that the satellite *"cannot be used as is"*: at today's resolutions a small horticultural plot is sub-pixel, so the pixel mostly sees the surrounding area, not the plot (methodology_idea.txt) — the [[Sub Pixel Problem]]. The branch addresses this through one of two interchangeable methods that produce the same kind of diagnosed state with uncertainty: the rigorous one-step [[Route A - Direct Probabilistic Fusion]] (feed the satellite as one more covariate straight to the field state), or the lighter [[Route B - Homogeneous Patch Proxy]] (read a clean covarying patch the coarse pixel can resolve). The choice between them is open (RQ2).

## Source grounding

- Branch definition and the sub-pixel concern: `methodology_idea.txt`.
- Diagnostic-block targets (water stress, soil moisture, crop condition, phenology): `prompt.txt §1`.
- Hidden-state list and fusion inputs (S1/S2 indices, soil, weather): `prompt.txt §3`.

## Links and relationships

Up: [[Core Architecture]] · [[Observation to Decision Pipeline]]. Down: [[AquaCrop Decision Interface]]. Related: [[Route A - Direct Probabilistic Fusion]] · [[Route B - Homogeneous Patch Proxy]] · [[Sub Pixel Problem]] · [[Uncertainty Chain]]. Hub: [[Methodology Graph - Meta Node]].

## Open questions

The precise definition of the "field state" — soil moisture, crop water stress, yield risk, irrigation priority, or all of these — is a project decision still to be made (RQ3, [[Ten Research Questions]]), as are the ground-truth measurements (RQ4) and how the diagnostic uncertainty will be evaluated (RQ5).

---
id: METH-INFRA-002
title: "Earth Observation Layer"
node_type: infrastructure_layer
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
  - "prompt.txt §8 (Earth observation layer: Sentinel-1, Sentinel-2, PlanetScope, field boundaries, cloud masking, temporal compositing)"
  - "prompt.txt §3 (S1 radar through cloud; S2 NDVI/NDWI/NDMI; PlanetScope higher resolution for small fields)"
  - "litreview Report A §3.1–3.2 (S1+S2 common; PlanetScope rare alongside S1 and ground sensors in row crops)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes:
  - "[[Geospatial and Time Series Data Platform]]"
related_nodes:
  - "[[Sentinel 1 and Sentinel 2 Integration]]"
  - "[[PlanetScope Usage Gap]]"
  - "[[Diagnostic Branch]]"
key_terms:
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[PlanetScope]]"
  - "[[SAR]]"
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
risks: []
open_questions:
  - "Is PlanetScope access secured or only optional? (RQ8)"
validation_needs:
  - "Cloud-masking and temporal-compositing quality for small horticultural plots"
aliases:
  - "EO layer"
  - "Satellite layer"
tags:
  - methodology-graph
  - infrastructure
---

# Earth Observation Layer

The satellite-imagery infrastructure layer: acquires, masks and composites Sentinel-1, Sentinel-2 and (optionally) PlanetScope data over the field boundaries, supplying the optical and radar covariates that feed the diagnosis.

## What it is

Per the analyst synthesis (prompt.txt §8), the Earth observation layer comprises: **Sentinel-1, Sentinel-2, PlanetScope, field boundaries, cloud masking, and temporal compositing**. It is the first observation layer in the [[Infrastructure Architecture]] and the upstream source of the satellite signals used by the [[Diagnostic Branch]].

## Components and their role

- **[[Sentinel 1]] ([[SAR]])** — Copernicus C-band radar. Valued because it **works through cloud cover** and is **sensitive to surface structure and moisture** (prompt.txt §3). A known limitation is that **dense vegetation reduces SAR retrieval accuracy** (litreview Report A §3.4).
- **[[Sentinel 2]]** — Copernicus optical imagery, the source of the vegetation/water indices **[[NDVI]], [[NDWI]] and [[NDMI]]** (prompt.txt §3). Optical observation is **limited by cloud cover** (litreview Report A §3.4).
- **[[PlanetScope]]** — high-spatial-resolution CubeSat optical imagery, **useful for small fields if available** (prompt.txt §3). The literature review notes it is **rarely combined with both radar (S1) and ground sensors** for drought/irrigation in row crops, and is mostly used for yield estimation or land cover rather than direct plant-based drought monitoring (litreview Report A §3.2). See [[PlanetScope Usage Gap]].
- **Field boundaries** — the geometry defining each plot, needed to extract per-field signals.
- **Cloud masking** — removing cloud-contaminated optical pixels (a direct response to the optical cloud-cover limitation).
- **Temporal compositing** — combining acquisitions over time into cleaner per-period products.

## Role in this methodology

This layer produces the optical and radar **covariates** that the diagnosis consumes. Crucially, in the preferred design these satellite observations are **not** first converted into an estimated fine pixel; they are fed (with their uncertainty) directly into the probabilistic diagnosis. The pairing of all-weather S1 radar with cloud-sensitive S2 optical is the standard, strongly-evidenced practice documented in [[Sentinel 1 and Sentinel 2 Integration]] (dual-sensor > single-sensor = Strong evidence, litreview Report A).

> [!note] Sub-pixel context
> For small horticultural plots the satellite does not "see" the plot cleanly — a single pixel may mix the target crop with neighbouring vegetation, bare soil, roads or buildings. That is the motivation for the methodological routes; this layer simply supplies the raw EO inputs. The problem and its handling live in the methodological-route nodes, not here.

## Source grounding

Layer composition: prompt.txt §8. Sensor characteristics: prompt.txt §3 and litreview Report A §3.1–3.4. PlanetScope rarity: litreview Report A §3.2. SAR/optical limitations: litreview Report A §3.4. Top EO contributors in the literature were N. Baghdadi, M. Zribi and S. Ferrant.

## Open questions

> [!warning] PlanetScope access unconfirmed
> Whether **PlanetScope access is secured or only optional** is open (RQ8); the literature also flags PlanetScope **cost and access** as a limiting factor. confidence on PlanetScope availability: low. See [[PlanetScope Usage Gap]] and the data-access risk nodes.

## Links & relationships

Up to [[Infrastructure Architecture]]; feeds [[Geospatial and Time Series Data Platform]]; supplies the [[Diagnostic Branch]]. State-of-the-art context in [[Sentinel 1 and Sentinel 2 Integration]] and [[PlanetScope Usage Gap]]. Key terms: [[Sentinel 1]], [[Sentinel 2]], [[PlanetScope]], [[SAR]], [[NDVI]], [[NDWI]], [[NDMI]].

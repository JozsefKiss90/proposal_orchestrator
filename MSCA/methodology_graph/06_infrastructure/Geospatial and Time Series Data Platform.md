---
id: METH-INFRA-005
title: "Geospatial and Time Series Data Platform"
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
evidence_basis:
  - "prompt.txt §8 (Data platform: geospatial database, time-series database, metadata catalogue, quality-control pipeline)"
  - "litreview Report A §3.4 / key limitations (harmonising spatial/temporal resolutions; data-fusion across heterogeneous multi-source datasets)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes:
  - "[[Probabilistic Modelling Runtime]]"
related_nodes:
  - "[[Earth Observation Layer]]"
  - "[[Ground Sensing Layer]]"
  - "[[Weather and Climate Data Layer]]"
key_terms:
  - "[[Data Fusion]]"
risks: []
open_questions:
  - "Concrete database technologies and catalogue standard (implementation detail, not in sources)"
validation_needs:
  - "Quality-control rules; spatial/temporal harmonisation across sensors"
aliases:
  - "Data platform"
  - "Data management layer"
tags:
  - methodology-graph
  - infrastructure
---

# Geospatial and Time Series Data Platform

The data-management infrastructure layer: a geospatial database, a time-series database, a metadata catalogue and a quality-control pipeline that hold and harmonise every observation before modelling.

## What it is

Per the analyst synthesis (prompt.txt §8), the data-platform layer comprises: **a geospatial database, a time-series database, a metadata catalogue, and a quality-control (QC) pipeline**. It sits between the observation layers and the modelling layers in the [[Infrastructure Architecture]].

## Components and their role

- **Geospatial database** — stores spatial objects: field boundaries, satellite rasters and derived index maps from the [[Earth Observation Layer]].
- **Time-series database** — stores temporally indexed streams: soil-moisture and weather series from the [[Ground Sensing Layer]] and [[Weather and Climate Data Layer]], plus index time series and irrigation logs.
- **Metadata catalogue** — records provenance, units, acquisition dates, sensor identity and processing history, so each input can be traced and combined correctly.
- **Quality-control pipeline** — flags, filters and harmonises the raw inputs (e.g. cloud-masked vs. clear optical pixels, sensor outliers) before they reach the models.

## Role in this methodology

This layer is the practical enabler of **[[Data Fusion]]**. The three observation layers — [[Earth Observation Layer]], [[Ground Sensing Layer]] and [[Weather and Climate Data Layer]] — feed into it, and it in turn feeds the [[Probabilistic Modelling Runtime]] that produces the probabilistic field-state diagnosis. Combining radar, optical, soil and weather signals "into one model" (the plain definition of [[Data Fusion]]) is only possible once those heterogeneous streams have been co-registered in space, aligned in time, catalogued and quality-controlled — which is exactly this platform's job.

> [!note] Harmonisation is a named challenge
> The literature review repeatedly flags **harmonising spatial and temporal resolutions** and **optimal data-fusion strategies for heterogeneous multi-source agricultural datasets** as persistent challenges (litreview Report A §3.4 and open research questions). The QC pipeline and the dual geospatial/time-series stores are the infrastructure response to that challenge.

## Source grounding

Layer composition: prompt.txt §8. The harmonisation / heterogeneous-fusion challenge it addresses: litreview Report A §3.4 and the Report A open research questions. The specific database technologies and catalogue standards are implementation details **not specified in the sources** and are left open *(inference: implementation choice)*.

## Links & relationships

Up to [[Infrastructure Architecture]]; ingests from [[Earth Observation Layer]], [[Ground Sensing Layer]] and [[Weather and Climate Data Layer]]; serves the [[Probabilistic Modelling Runtime]]. Key term: [[Data Fusion]].

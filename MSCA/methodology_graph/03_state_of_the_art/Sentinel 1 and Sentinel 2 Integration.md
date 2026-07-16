---
id: METH-SOTA-002
title: "Sentinel 1 and Sentinel 2 Integration"
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
  - "litreview Report A §3.1, §3.4, §4 Discussion, Fig.4 (Top Contributors), Fig.5 (Claims & Evidence: dual-sensor = Strong)"
  - "Report A DOIs: Chun-Yang 2022 (rs14051205), Bousbih 2018 (rs10121953), Wu 2024 (j.agwat.2024.108718), Pageot 2020 (rs12183044)"
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
  - "[[Earth Observation Layer]]"
key_terms:
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[SAR]]"
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "S1+S2 Integration"
  - "Dual-Sentinel Integration"
tags:
  - methodology-graph
  - state-of-the-art
---

# Sentinel 1 and Sentinel 2 Integration

The combination of `[[Sentinel 1]]` SAR (radar) with `[[Sentinel 2]]` optical imagery — the most common multi-sensor pairing in the literature and, per Report A, now **standard practice** for drought-stress and irrigation monitoring in row crops.

## What the literature establishes

According to §3.1 of `[[Source - Literature Review]]` (Report A), most published research integrates two or three data types, **commonly Sentinel-1 SAR with Sentinel-2 optical imagery**, to monitor soil-moisture dynamics, crop growth stages, irrigation events and drought impacts. These studies leverage two complementary strengths:

- **`[[SAR]]` (Sentinel-1):** all-weather capability — radar penetrates cloud and is sensitive to surface structure and moisture.
- **Optical indices (Sentinel-2):** spectral sensitivity captured through `[[NDVI]]`, `[[NDWI]]` and `[[NDMI]]`, improving detection accuracy under variable conditions.

Report A §4 (Discussion) states explicitly that **dual-sensor approaches (Sentinel-1 + Sentinel-2) are now standard practice** owing to these complementary strengths — SAR's weather independence and optical's spectral richness. In the report's Claims & Evidence table (Figure 5), the claim *"Dual-sensor integration (Sentinel-1 + Sentinel-2) improves drought/irrigation monitoring over single-sensor approaches"* is rated **Strong** — the only Strong rating in that table — supported by multiple field validations (e.g. Ibrahim et al. 2023; Chun-Yang et al. 2022; Wu et al. 2024; Bousbih et al. 2018; Pageot et al. 2020).

> [!note] Evidence strength
> "Strong" is Report A's own grading: multiple field validations show higher accuracy/reliability under diverse conditions. This is the most firmly established result in the SOTA review.

## Known limitations of the pairing

Report A §3.4 records persistent challenges that bound this pairing's performance: **dense vegetation reduces SAR retrieval accuracy** (Mkhwenkwana et al. 2025), and **cloud cover limits optical data availability**. These two constraints partly motivate the project's interest in higher-resolution and complementary inputs (see `[[PlanetScope Usage Gap]]`) and in honest uncertainty handling rather than overconfident point estimates.

## Top contributors

Report A's Top Contributors figure (Figure 4) identifies **N. Baghdadi** and **M. Zribi** as the most frequently appearing authors in this dual-sensor / SAR literature, with **S. Ferrant** also prominent; *Remote Sensing* is the dominant journal.

## Role in this methodology

Sentinel-1 and Sentinel-2 are the backbone optical+radar inputs of the project's `[[Earth Observation Layer]]`. Establishing that their fusion is mature and well-validated is important context: the project does **not** claim novelty in dual-sensor fusion itself, but builds on it as a settled foundation. This page is a child of `[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]`.

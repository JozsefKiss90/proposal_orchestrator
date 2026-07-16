---
id: METH-PART-006
title: "Unconfirmed Partner Placeholders"
node_type: partner
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
  - "BUILD_BRIEF §B.6 (UNCONFIRMED / OPEN items: ELTE absent; AgroVIR only 'AgroVIR-like'; PI/contributor inferred)"
  - "prompt.txt §8 (EO / meteo / validation infrastructure implies data and field-access providers)"
evidence_strength: unconfirmed
confidence: low
maturity: project_decision_needed
owner_role: ""
stakeholders:
  - "[[PI Role]]"
upstream_nodes:
  - "[[Partner Roles Overview]]"
downstream_nodes: []
related_nodes:
  - "[[Partner Roles Overview]]"
  - "[[ELTE Role]]"
  - "[[AgroVIR Validation Partner Role]]"
key_terms: []
risks: []
open_questions:
  - "Confirm lead institution and named PI."
  - "Confirm whether ELTE is involved and in what role."
  - "Confirm an AgroVIR (or equivalent) validation partnership and scope."
  - "Confirm validation farms / field sites."
  - "Confirm EO data providers (Planet / Copernicus)."
  - "Confirm meteorological data providers."
validation_needs:
  - "Resolve every placeholder below into a named, evidenced partner before submission."
aliases:
  - "Partner Placeholders"
  - "Unconfirmed Partners"
tags:
  - methodology-graph
  - partner
---

# Unconfirmed Partner Placeholders

A single working checklist of **every partner/provider the methodology implies but no source confirms** — kept so the proposal team can resolve each one explicitly.

> [!warning] All entries below are unconfirmed
> None of the partners on this list is named or committed in [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]], or [[Source - Literature Review]]. They are derived either from the build brief's open-items list (BUILD_BRIEF §B.6) or inferred from the infrastructure the methodology requires. Each must be confirmed before any appears in a proposal as a real partner. (`evidence_strength: unconfirmed`, `confidence: low`.)

## Placeholder checklist

| # | Placeholder | Why it is implied | Current status | Linked node |
|---|---|---|---|---|
| 1 | **Lead institution / named PI** | The design narrative has a first-person author and DOI-holder, but no name | Unconfirmed — name to confirm | [[PI Role]] |
| 2 | **ELTE (Eötvös Loránd University)** | Raised in build context only | Unconfirmed — absent from all sources | [[ELTE Role]] |
| 3 | **AgroVIR (or equivalent) validation partner** | "AgroVIR-like partners" example role (prompt.txt §8) | Unconfirmed — role type only, no commitment | [[AgroVIR Validation Partner Role]] |
| 4 | **Validation farms / field sites** | Field trials, testing and farmer access are required | Unconfirmed — no sites named | [[Validation and Field Trial Layer]] |
| 5 | **EO data providers (Planet / Copernicus)** | PlanetScope, Sentinel-1/2 are core inputs | Unconfirmed — Sentinel is open Copernicus data; PlanetScope access is itself open (RQ8) | [[Earth Observation Layer]] |
| 6 | **Meteorological data providers** | Weather/ET inputs and ERA5-Land are required | Unconfirmed — no provider named | [[Weather and Climate Data Layer]] |

*(Entries 1–3 are taken from BUILD_BRIEF §B.6. Entries 4–6 are inference from the infrastructure the methodology requires — labelled as inference, not source-named partners.)*

## How to retire a placeholder

Following the Karpathy LLM-wiki maintenance discipline, when a partner is confirmed: replace the placeholder with the confirmed identity in its dedicated role node, change that node's `evidence_strength` from `unconfirmed` to the appropriate value, update `confidence`, remove the matching open question here, and note the change in the graph's changelog. This page should shrink over time.

## Source grounding

- Open partner items: BUILD_BRIEF §B.6.
- Infrastructure-implied providers: [[Source - Methodology Synthesis Prompt]] §8.

## Links & relationships

This page sits under [[Partner Roles Overview]] and is cross-linked to the two most-flagged role nodes, [[ELTE Role]] and [[AgroVIR Validation Partner Role]]. The data/field providers map onto the infrastructure layers ([[Earth Observation Layer]], [[Weather and Climate Data Layer]], [[Validation and Field Trial Layer]]).

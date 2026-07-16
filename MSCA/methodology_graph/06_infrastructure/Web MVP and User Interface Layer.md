---
id: METH-INFRA-010
title: "Web MVP and User Interface Layer"
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
  - "prompt.txt §8 (User interface: web MVP/dashboard for farmers/advisors/validation partners; MVP as standalone research demonstrator; AgroVIR-like partners assist, not own/operate)"
  - "prompt.txt §10 (RQ10 — TRL target: research prototype, validated MVP, or operational pilot)"
evidence_strength: synthesis
confidence: low
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[AgroVIR Validation Partner Role]]"
  - "[[Operational Decision Support Gap]]"
  - "[[Operationalisation Risks]]"
key_terms:
  - "[[Expected Profit]]"
risks:
  - "[[Operationalisation Risks]]"
open_questions:
  - "RQ10 — what is the TRL target (research prototype, validated MVP, or operational pilot)?"
validation_needs:
  - "Define TRL target and the MVP's role as demonstrator vs product"
aliases:
  - "User Interface Layer"
  - "Web MVP"
tags:
  - methodology-graph
  - infrastructure
---

# Web MVP and User Interface Layer

The presentation layer — a **web MVP / dashboard** through which farmers, advisors and validation partners see the diagnosis, the simulated options, and the recommended irrigation decision.

## What it is

In the layered infrastructure (prompt.txt §8), the **User interface** is described as a *web MVP/dashboard for farmers/advisors/validation partners*. This node is that front end: the human-facing surface that exposes outputs of the [[Decision Engine Layer]] — the recommended action and its [[Expected Profit]] — in a form usable by non-modellers.

## Role in this methodology

The MVP is how the methodology becomes *visible and testable* by its intended users. The source is deliberate about framing for an MSCA-style proposal:

> [!note] Proposal framing (from prompt.txt §8)
> *"For an MSCA-style proposal, you can present the MVP as a standalone research demonstrator, with AgroVIR-like partners helping with feedback, farmer access, testing and validation rather than owning or operating the tool."*

So this layer is positioned as a **research demonstrator**, not a commercial product. It is also where the project most directly confronts the [[Operational Decision Support Gap]] from the literature — the scarcity of operational frameworks that fuse all sensor types into real-time decision support — by giving the end-to-end pipeline a concrete, demonstrable interface. *(Proposal synthesis)* The choice to keep the MVP a demonstrator, and to keep partners in an assisting rather than operating role, is the analyst's framing of how to present the layer, not a hard technical specification.

## Source grounding & unconfirmed items

> [!warning] Unconfirmed (confidence: low)
> - **TRL target is open (RQ10):** whether the deliverable is a research prototype, a validated MVP, or an operational pilot is *not* decided in the sources. No TRL number is asserted here. See [[Operationalisation Risks]] and [[Ten Research Questions]].
> - **AgroVIR partnership is unconfirmed:** the sources mention only *"AgroVIR-like partners"* as an example role (feedback / farmer access / testing / validation, not owning/operating). A committed AgroVIR partnership is not established — see [[AgroVIR Validation Partner Role]]. Do not present it as a secured partner.
> - **No specific UI technology, hosting, or feature set** is named in the sources, so none is asserted.

This node is tagged `evidence_strength: synthesis` because, while the dashboard layer and its demonstrator framing are source-grounded (prompt.txt §8), its scope (TRL, partner roles) rests on open decisions and a proposal-shaping framing rather than fixed facts.

## Links and relationships

- **Up:** [[Infrastructure Architecture]].
- **Surfaces:** outputs of the [[Decision Engine Layer]] (recommendation + [[Expected Profit]]).
- **Partners:** [[AgroVIR Validation Partner Role]] (assisting role, unconfirmed).
- **Addresses:** [[Operational Decision Support Gap]].
- **Risk / open question:** [[Operationalisation Risks]]; RQ10 in [[Ten Research Questions]].

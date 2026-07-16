---
id: METH-RISK-006
title: "Operationalisation Risks"
node_type: risk
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
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "litreview Report A key limitations (limited operational frameworks fusing all sensors into real-time DSS; Duan 2025, Moderate)"
  - "litreview Report A Fig.6 (Real-Time Decision Support x PlanetScope = GAP)"
  - "prompt.txt §8 (MVP as standalone research demonstrator; AgroVIR-like partners assist not own)"
evidence_strength: source_grounded
confidence: medium
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Risk Register]]"
downstream_nodes: []
related_nodes:
  - "[[Operational Decision Support Gap]]"
  - "[[Web MVP and User Interface Layer]]"
  - "[[Decision Engine Layer]]"
  - "[[Risk Register]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Expected Profit]]"
risks: []
open_questions:
  - "RQ10 — what is the TRL target (research prototype, validated MVP, or operational pilot)?"
  - "[[Ten Research Questions]]"
validation_needs:
  - "Fix the TRL target and confirm partner roles for testing/farmer access"
aliases: []
tags:
  - methodology-graph
  - risk
---

# Operationalisation Risks

Risks in turning the research framework into a usable decision-support tool: the unfilled operational-frameworks gap, the prototype-to-pilot leap, and unsettled partner/TRL scope.

These risks are **source-grounded**. The literature review identifies **limited operational frameworks fusing all sensor types into real-time decision support** as a key limitation (Moderate evidence, Duan 2025), and Report A's Fig.6 marks Real-Time Decision Support × PlanetScope as an outright **GAP** (litreview Report A). This is simultaneously the project's opportunity and its risk: the gap is real because operationalisation at scale is hard. This node feeds the [[Risk Register]] and is the risk view of the [[Operational Decision Support Gap]] and the [[Web MVP and User Interface Layer]].

## The risks

### 1. The operational-frameworks gap is hard to close
Few works fuse all sensor types into a real-time decision-support tool (litreview Report A; [[Operational Decision Support Gap]]). The same difficulty that makes this novel makes it risky: integrating [[Data Fusion]], the [[Decision Engine Layer]] and an [[Expected Profit]] objective into something operable is non-trivial.

### 2. Prototype-to-pilot leap
Moving from a research prototype to a deployable pilot is a recognised step the field rarely completes. The analyst synthesis recommends presenting the MVP as a **standalone research demonstrator** for an MSCA-style proposal, with AgroVIR-like partners assisting on feedback, farmer access, testing and validation **rather than owning or operating** the tool (prompt.txt §8). This framing manages, but does not remove, the leap.

### 3. Scope is unsettled
What the project actually commits to deliver is open: the TRL target (research prototype vs validated MVP vs operational pilot) is **RQ10**, surfaced in the [[Web MVP and User Interface Layer]].

> [!warning] TRL and partner roles unconfirmed
> The TRL target is **not established** in the sources (§B.6, RQ10), and partners appear only as "AgroVIR-like" examples, not committed roles. `confidence: medium`, `maturity: project_decision_needed`. Do not promise an operational product. See [[Ten Research Questions]].

## Mitigations (proposal-level)
- Frame the MVP explicitly as a standalone research demonstrator (prompt.txt §8).
- Position partners as assisting (feedback/farmer-access/testing/validation), not owning/operating.
- Decide and state the TRL target early (RQ10).

## Links and relationships
This node rolls up to the [[Risk Register]] and the [[Methodology SWOT Matrix]] (opportunity to fill the operational gap; threat of operationalisation at scale). It connects to the [[Operational Decision Support Gap]], the [[Web MVP and User Interface Layer]] and the [[Decision Engine Layer]]; its open item maps to RQ10 in the [[Ten Research Questions]].

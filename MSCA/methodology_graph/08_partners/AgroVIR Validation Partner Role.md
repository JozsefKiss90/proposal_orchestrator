---
id: METH-PART-005
title: "AgroVIR Validation Partner Role"
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
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "prompt.txt §8 ('AgroVIR-like partners helping with feedback, farmer access, testing and validation rather than owning or operating the tool')"
  - "BUILD_BRIEF §B.6 (AgroVIR appears only as 'AgroVIR-like'; committed partnership unconfirmed)"
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
  - "[[Web MVP and User Interface Layer]]"
  - "[[Validation and Field Trial Layer]]"
  - "[[Partner Roles Overview]]"
key_terms: []
risks: []
open_questions:
  - "Is there an actual, committed AgroVIR partnership, or only an 'AgroVIR-like' role type?"
  - "If committed, what is the exact scope (feedback, farmer access, testing, validation)?"
validation_needs:
  - "Confirm AgroVIR (or equivalent) partnership and scope before proposal submission."
aliases:
  - "AgroVIR"
  - "Validation Partner"
tags:
  - methodology-graph
  - partner
---

# AgroVIR Validation Partner Role

A possible **validation / farmer-access partner**, described in the sources only by type ("AgroVIR-like"), **not as a committed partnership**.

> [!warning] Unconfirmed — only an "AgroVIR-like" role type is sourced
> AgroVIR appears in exactly one place: [[Source - Methodology Synthesis Prompt]] §8, which suggests that for an MSCA-style proposal the MVP be presented as a *standalone research demonstrator*, *"with AgroVIR-like partners helping with feedback, farmer access, testing and validation rather than owning or operating the tool."* This is an **example of a role type**, not a statement that AgroVIR is committed. No specific partnership, contact, or agreement is in the sources (BUILD_BRIEF §B.6). Hence `evidence_strength: unconfirmed`, `confidence: low`.

## The role type (as sourced)

The source defines the role by **what such a partner does and does not do**:

| Does | Does NOT |
|---|---|
| Provide feedback on the tool | Own the tool |
| Enable farmer access | Operate the tool as a product |
| Support testing | Take commercial control |
| Support validation | — |

This boundary is deliberate: it keeps the [[Web MVP and User Interface Layer]] a research demonstrator owned by the host, while an external partner supplies the real-world touchpoints the research needs. This framing is the load-bearing reason the partner is "helping" rather than "operating."

## Where the role plugs into the methodology

- **[[Web MVP and User Interface Layer]]** — the partner gives feedback on, and farmer access to, the dashboard for farmers/advisors/validation partners.
- **[[Validation and Field Trial Layer]]** — the partner supports testing and validation, i.e. real fields and users against which model accuracy, uncertainty calibration and decision performance can be checked.

## What must not be claimed

Per BUILD_BRIEF §B.6 and §F.4: do **not** state that AgroVIR is a confirmed partner, name specific farms or contracts, or attribute datasets/commitments to it. Only the generic "AgroVIR-like" role type is supported.

## Source grounding

- Role type and ownership boundary: [[Source - Methodology Synthesis Prompt]] §8.
- Unconfirmed-partnership status: BUILD_BRIEF §B.6.

## Links & relationships

This node sits under [[Partner Roles Overview]] and connects the partner model to the [[Web MVP and User Interface Layer]] and the [[Validation and Field Trial Layer]].

## Open questions

1. Is there a committed AgroVIR (or equivalent) partnership, or only a role type to fill?
2. If committed, what is the exact agreed scope?
